# src/core/orchestrator_handlers/scan_handler.py
import logging
from typing import Dict, Any, Optional, Callable, List
import json

# Importar módulos necesarios
from core.data_manager import DataManager
from core.session_manager import SessionManager
from utils.command_runner import CommandRunner
from modules.nmap_tool.nmap_runner import NmapRunner
from modules.nmap_tool.nmap_parser import NmapParser
from core.context_protocol import ModelContextProtocol
# Importar el cliente NVD y la función para construir CPEs
from modules.cve_lookup.nvd_client import SimpleNVDAPIClient, construct_cpe_name_simplified

logger = logging.getLogger(__name__)

class ScanHandler:
    def __init__(self, data_manager: DataManager, session_manager: SessionManager,
                 command_runner: CommandRunner,
                 get_gemini_chat_session: Callable[[str], ModelContextProtocol],
                 process_ai_analysis_with_tool_results: Callable[..., Optional[str]],
                 vulnerability_analysis_prompt_template: str):
        self.data_manager = data_manager
        self.session_manager = session_manager
        self.command_runner = command_runner
        self.get_gemini_chat_session = get_gemini_chat_session
        self._process_ai_analysis_with_tool_results = process_ai_analysis_with_tool_results
        self.vulnerability_analysis_prompt_template = vulnerability_analysis_prompt_template
        logger.info("[ScanHandler] Inicializado.")

        self.nmap_runner = NmapRunner(command_runner=self.command_runner)
        self.nmap_parser = NmapParser()
        # Inicializar el cliente NVD
        self.nvd_client = SimpleNVDAPIClient()
        logger.info("[ScanHandler] Inicializado con NmapRunner, NmapParser y SimpleNVDAPIClient.")

    def _analyze_service_banner(self, scan_id: int, host_id: int, service_id: int, service_data: Dict[str, Any], chat_session_id: str):
        """
        Analiza un banner de servicio usando la IA para detectar posibles vulnerabilidades.
        """
        model_context = self.get_gemini_chat_session(chat_session_id)

        objective = f"Analizar el banner/versión del servicio {service_data.get('service_name')} en puerto {service_data.get('port')} para posibles vulnerabilidades."
        input_data = f"Servicio: {service_data.get('service_name')}\nPuerto: {service_data.get('port')}\nProtocolo: {service_data.get('protocol')}\nVersión: {service_data.get('version')}\nEstado: {service_data.get('state')}"

        ai_response = model_context.ask_gemini(
            objective=objective,
            input_type="Información de servicio/banner",
            input_data=input_data,
            response_requirements=self.vulnerability_analysis_prompt_template
        )

        parsed_finding = self._parse_ai_vulnerability_response(ai_response)
        if parsed_finding:
            host_info = self.data_manager.get_host(host_id)
            service_info = self.data_manager.get_service(service_id)

            self.data_manager.add_finding(
                scan_id=scan_id,
                host_id=host_id,
                service_id=service_id,
                type="vulnerability",
                title=f"Vulnerabilidad Detectada: {parsed_finding.get('vulnerability', 'N/A')}",
                description=parsed_finding.get('vulnerability', 'Sin descripción detallada.'),
                severity=parsed_finding.get('impact', 'Informational'),
                recommendation="\n".join(parsed_finding.get('mitigations', [])),
                details={"ai_raw_response": ai_response, "service_info": service_info, "host_info": host_info}
            )
            logger.info(f"Hallazgo de vulnerabilidad AI registrado para {service_data.get('service_name')} en {host_info['ip_address'] if host_info else 'N/A'}: {parsed_finding.get('vulnerability')}")
        else:
            logger.warning(f"ADVERTENCIA: La IA no pudo generar un hallazgo estructurado para el servicio {service_data.get('service_name')}.")

    def _parse_ai_vulnerability_response(self, ai_response: str) -> Optional[Dict[str, Any]]:
        """
        Método auxiliar para parsear la respuesta JSON de la IA (copiado de Orchestrator).
        Podría moverse a un AiParsingHelper si se usa en muchos lugares.
        """
        try:
            if ai_response.startswith('```json') and ai_response.endswith('```'):
                ai_response = ai_response[len('```json'):-len('```')].strip()
            elif ai_response.startswith('```') and ai_response.endswith('```'):
                ai_response = ai_response[len('```'):-len('```')].strip()

            data = json.loads(ai_response)
            if all(k in data for k in ["vulnerability", "impact", "mitigations"]):
                return data
            else:
                logger.warning(f"Respuesta de IA no tiene el formato esperado para vulnerabilidad: {ai_response[:100]}...")
                return None
        except json.JSONDecodeError as e:
            logger.error(f"ERROR: No se pudo decodificar la respuesta JSON de Gemini: {e}. Respuesta: {ai_response[:200]}...")
            return None
        except Exception as e:
            logger.error(f"ERROR inesperado al procesar respuesta de IA: {e}. Respuesta: {ai_response[:200]}...")
            return None

    def start_network_scan(self, target: str, session_name: str, chat_session_id: str, nmap_profile: str = 'default_scan') -> Dict[str, Any]:
        """
        Ejecuta un escaneo de red utilizando Nmap, procesa los resultados,
        busca CVEs para los servicios descubiertos y delega el análisis de vulnerabilidades a la IA.
        """
        logger.info(f"[ScanHandler] Iniciando nuevo escaneo de red: Objetivo='{target}', Sesión='{session_name}'")

        scan_id = self.data_manager.create_scan_session(session_name, "Network Scan", target, status='in_progress')
        if not scan_id:
            logger.error("ERROR: No se pudo crear la sesión de escaneo en la base de datos.")
            return {"status": "error", "message": "No se pudo crear la sesión de escaneo.", "scan_id": None}

        self.session_manager.start_new_scan_session(scan_id, session_name, "Network Scan", target)

        logger.info(f"[ScanHandler] Ejecutando Nmap con perfil '{nmap_profile}' en {target}...")
        nmap_command = self.nmap_runner.build_command(target, profile=nmap_profile)
        nmap_result = self.command_runner.run_command(nmap_command, timeout=600)

        if not nmap_result.success:
            logger.error(f"ERROR: Nmap falló para {target}. STDERR:\n{nmap_result.stderr}")
            error_summary = f"El escaneo Nmap falló para {target}: {nmap_result.stderr}"
            self.data_manager.update_scan_session(scan_id, status='failed', summary=error_summary)
            self._process_ai_analysis_with_tool_results(
                {"action": "start_network_scan_failed", "target": target, "error": nmap_result.stderr},
                f"El escaneo en {target} falló. ¿Cómo puedo ayudarte con esto? Necesito un nuevo objetivo o un tipo de análisis diferente.",
                chat_session_id
            )
            return {"status": "error", "message": error_summary, "scan_id": scan_id}

        logger.info(f"[ScanHandler] Nmap completado. Procesando resultados...")

        parsed_nmap_data = self.nmap_parser.parse_nmap_output(nmap_result.stdout)

        hosts_found_count = 0
        all_cves_found: Dict[str, List[Dict[str, Any]]] = {} # Para almacenar CVEs por servicio (ej. "OpenSSH 5.3p1")

        if parsed_nmap_data and parsed_nmap_data.get('hosts'):
            for host_ip, host_data in parsed_nmap_data['hosts'].items():
                hostname = host_data.get('hostname')
                os_info = host_data.get('os_info')

                host_db_id = self.data_manager.add_host(scan_id, host_ip, hostname, os_info)
                if host_db_id:
                    self.session_manager.add_discovered_host(host_ip, host_db_id)
                    hosts_found_count += 1

                    for port_info in host_data.get('ports', []):
                        service_db_id = self.data_manager.add_service(
                            host_db_id,
                            port_info['port'],
                            port_info.get('protocol'),
                            port_info.get('service_name'),
                            port_info.get('version'),
                            port_info.get('state')
                        )
                        if service_db_id:
                            self.session_manager.add_discovered_service_for_host(
                                host_ip,
                                port_info['port'],
                                port_info.get('service_name'),
                                service_db_id
                            )

                            # --- NUEVA LÓGICA: BÚSQUEDA DE CVES ---
                            service_name = port_info.get('service_name')
                            service_version = port_info.get('version')

                            if service_name and service_version:
                                logger.info(f"[ScanHandler] Buscando CVEs para {service_name} {service_version}...")
                                cpe_attempts = []
                                # Intentar con la versión exacta primero
                                cpe_exact = construct_cpe_name_simplified(service_name, service_version, generic=False)
                                if cpe_exact:
                                    cpe_attempts.append(cpe_exact)
                                
                                # Si no se encontró nada con la exacta, intentar con una versión genérica
                                cpe_generic = construct_cpe_name_simplified(service_name, service_version, generic=True)
                                if cpe_generic and cpe_generic != cpe_exact: # Evitar duplicados si la versión genérica es igual a la exacta
                                    cpe_attempts.append(cpe_generic)

                                cves_for_current_service = []
                                for cpe_to_search in cpe_attempts:
                                    raw_cve_data = self.nvd_client.search_cve(cpe_to_search)
                                    if raw_cve_data:
                                        summarized_cves = self.nvd_client.parse_and_summarize_cve_data(raw_cve_data)
                                        if summarized_cves:
                                            cves_for_current_service.extend(summarized_cves)
                                            logger.info(f"CVEs encontrados para {service_name} {service_version} (CPE: {cpe_to_search}): {[c['cve_id'] for c in summarized_cves]}")
                                            break # Si encontramos CVEs con un CPE, no necesitamos probar los demás
                                    else:
                                        logger.debug(f"No se obtuvieron resultados del NVD para CPE: {cpe_to_search}")
                                
                                if cves_for_current_service:
                                    service_key = f"{service_name} {service_version}"
                                    all_cves_found[service_key] = cves_for_current_service
                                else:
                                    logger.info(f"No se encontraron CVEs para {service_name} {service_version}.")
                            # --- FIN NUEVA LÓGICA: BÚSQUEDA DE CVES ---

        logger.info(f"[ScanHandler] Se encontraron y registraron {hosts_found_count} hosts activos.")

        if parsed_nmap_data and parsed_nmap_data.get('hosts'):
            logger.info("[ScanHandler] Iniciando análisis de vulnerabilidades para servicios descubiertos (AI)...")
            for host_ip, host_data in parsed_nmap_data['hosts'].items():
                host_record = self.data_manager.get_host_by_ip_and_scan_id(host_ip, scan_id)
                if host_record:
                    host_db_id = host_record['id']
                else:
                    logger.warning(f"ADVERTENCIA: No se pudo encontrar DB ID para host {host_ip}. Saltando análisis de servicios.")
                    continue

                for port_info in host_data.get('ports', []):
                    service_record = self.data_manager.get_service_by_port_and_host_id(port_info['port'], host_db_id)
                    if service_record:
                        service_db_id = service_record['id']
                        logger.info(f"[ScanHandler] Analizando servicio {port_info.get('service_name')}:{port_info['port']} en {host_ip} con IA...")
                        self._analyze_service_banner(scan_id, host_db_id, service_db_id, port_info, chat_session_id)
                    else:
                        logger.warning(f"ADVERTENCIA: No se pudo encontrar DB ID para servicio {port_info.get('service_name')}:{port_info['port']} en {host_ip}. Saltando análisis.")


        tool_output = {
            "action_completed": "start_network_scan",
            "target": target,
            "scan_id": scan_id,
            "hosts_found_count": hosts_found_count,
            "nmap_raw_output": nmap_result.stdout, # Considerar si esto es demasiado verbose
            "parsed_data_summary": {
                "hosts": [
                    {"ip": ip, "ports": [p['port'] for p in host_data.get('ports', [])]}
                    for ip, host_data in parsed_nmap_data.get('hosts', {}).items()
                ],
                "cves_found_by_service": all_cves_found # <-- AÑADIMOS LOS CVES AQUÍ
            }
        }

        all_findings = self.data_manager.get_findings_for_scan(scan_id)

        formatted_findings = []
        if all_findings:
            for finding in all_findings:
                host_ip = finding.get('details', {}).get('host_info', {}).get('ip_address', 'N/A')
                service_name = finding.get('details', {}).get('service_info', {}).get('service_name', 'N/A')
                port = finding.get('details', {}).get('service_info', {}).get('port', 'N/A')

                formatted_findings.append({
                    "vulnerability": finding.get('description'),
                    "impact": finding.get('severity'),
                    "recommendation": finding.get('recommendation'),
                    "target_host": host_ip,
                    "target_service": f"{service_name}:{port}"
                })

        tool_output["vulnerabilities_found"] = formatted_findings

        # Usa la función inyectada para comunicar los resultados a la IA
        # IMPORTANTE: Modificamos el prompt para que la IA sepa que hay CVEs
        ai_summary_for_chat = self._process_ai_analysis_with_tool_results(
            tool_output,
            f"El escaneo de red en {target} ha finalizado. Se han procesado los hallazgos de vulnerabilidades y se han buscado CVEs para los servicios descubiertos. Por favor, genera un resumen conversacional y útil para el usuario, destacando los hosts, servicios, cualquier vulnerabilidad detectada (incluyendo los CVEs si se encontraron) y sus mitigaciones. Si se encontraron CVEs, menciona que el usuario puede preguntar sobre ellos por su ID (ej. '¿Qué es CVE-2007-2768?').",
            chat_session_id
        )
        if not ai_summary_for_chat:
            ai_summary_for_chat = f"El escaneo de {target} ha finalizado y se encontraron {hosts_found_count} hosts, pero no pude generar un resumen detallado con la IA."

        logger.info(f"[ScanHandler] Resumen de IA conversacional del escaneo de red:\n{ai_summary_for_chat}")

        self.data_manager.update_scan_session(scan_id, status='completed', summary=ai_summary_for_chat)

        logger.info(f"[ScanHandler] Escaneo de red de la sesión '{session_name}' completado.")

        return {"status": "success", "scan_id": scan_id, "ai_summary": ai_summary_for_chat, "report_path": None, "report_filename": None}
