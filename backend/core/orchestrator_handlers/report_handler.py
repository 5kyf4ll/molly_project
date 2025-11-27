import logging
import json
from typing import Dict, Any, Optional, List
from datetime import datetime

# Importar módulos necesarios
from core.data_manager import DataManager
from reports.report_formatter import ReportFormatter
from reports.report_generator import ReportGenerator
from core.context_protocol import ModelContextProtocol # Importar para type hinting

logger = logging.getLogger(__name__)

class ReportHandler:
    def __init__(self, data_manager: DataManager, report_formatter: ReportFormatter, report_generator: ReportGenerator):
        self.data_manager = data_manager
        self.report_formatter = report_formatter
        self.report_generator = report_generator
        logger.info("[ReportHandler] Inicializado.")

    def get_scan_results_for_ai(self, scan_id_param: Optional[int], session_name_param: Optional[str], chat_session_id: str, model_context: ModelContextProtocol) -> str:
        """
        Recupera los detalles de un escaneo y los formatea para ser inyectados en la IA,
        obteniendo luego un resumen conversacional.
        """
        scan_details = None
        if scan_id_param:
            scan_details = self.data_manager.get_scan_details(scan_id_param)
        elif session_name_param:
            scan_details = self.data_manager.get_scan_details_by_name(session_name_param)

        if scan_details:
            hosts = self.data_manager.get_hosts_for_scan(scan_details['id'])
            services_by_host = {}
            for host in hosts:
                services_by_host[host['ip_address']] = self.data_manager.get_services_for_host(host['id'])
            findings = self.data_manager.get_findings_for_scan(scan_details['id'])

            formatted_results = {
                "scan_details": {k: v for k, v in scan_details.items() if k != 'summary'},
                "hosts": [{"ip_address": h['ip_address'], "hostname": h.get('hostname')} for h in hosts],
                "services_by_host": {ip: [{"port": s['port'], "service_name": s.get('service_name'), "version": s.get('version')} for s in svcs] for ip, svcs in services_by_host.items()},
                "findings": [{"title": f.get('title'), "severity": f.get('severity'), "description": f.get('description')} for f in findings]
            }

            tool_output_content = json.dumps(formatted_results, indent=2)

            response_from_tool_injection = model_context.inject_tool_results_into_chat(
                {"action_completed": "get_scan_results", "data": tool_output_content},
                f"He recuperado los detalles del escaneo. Por favor, genera un resumen conversacional de estos resultados para el usuario."
            )
            return response_from_tool_injection if response_from_tool_injection else "Resultados recuperados, pero la IA no generó un resumen de seguimiento."
        else:
            return "No se encontraron resultados para el escaneo solicitado. Por favor, verifica el ID o nombre."

    def generate_network_summary_report(self, scan_id: int, session_name: str, target: str, ai_summary: str) -> Optional[str]:
        """
        Genera un informe PDF de resumen de escaneo de red.
        """
        all_hosts_info = self.data_manager.get_hosts_for_scan(scan_id)
        services_map = {}
        for h_info in all_hosts_info:
            services_map[h_info['ip_address']] = self.data_manager.get_services_for_host(h_info['id'])

        scan_details = self.data_manager.get_scan_details(scan_id)
        network_summary_markdown = self.report_formatter.format_network_scan_summary(scan_details, all_hosts_info, services_map)

        report_filename = f"network_summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        pdf_path = self.report_generator.generate_pdf_report(
            network_summary_markdown,
            report_filename,
            session_name
        )

        if pdf_path:
            logger.info(f"[ReportHandler] Informe de resumen de red generado: {pdf_path}")
            # Actualiza el registro de escaneo con la ruta del informe
            self.data_manager.update_scan_session(scan_id, status='completed', summary=ai_summary, results_path=pdf_path)
            return pdf_path
        else:
            logger.warning(f"[ReportHandler] ADVERTENCIA: No se pudo generar el informe PDF para el escaneo {scan_id}.")
            return None

    def generate_detailed_host_report(self, host_ip: str, session_name: str) -> Optional[str]:
        """
        Genera un informe PDF detallado para un host específico dentro de una sesión.
        """
        scan_details = self.data_manager.get_scan_details_by_name(session_name)
        if not scan_details:
            logger.error(f"ERROR: Sesión '{session_name}' no encontrada para generar informe detallado.")
            return None

        scan_id = scan_details['id']

        hosts_in_scan = self.data_manager.get_hosts_for_scan(scan_id)
        target_host = next((h for h in hosts_in_scan if h['ip_address'] == host_ip), None)

        if not target_host:
            logger.error(f"ERROR: Host {host_ip} no encontrado en la sesión {session_name}.")
            return None

        host_id = target_host['id']
        host_info = target_host
        services = self.data_manager.get_services_for_host(host_id)
        findings = self.data_manager.get_findings_for_scan_and_host(scan_id, host_id)

        detailed_markdown = self.report_formatter.format_detailed_host_report(host_info, services, findings)

        report_filename = f"detailed_report_{host_ip.replace('.', '_')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        pdf_path = self.report_generator.generate_pdf_report(
            detailed_markdown,
            report_filename,
            session_name,
            host_ip
        )
        return pdf_path