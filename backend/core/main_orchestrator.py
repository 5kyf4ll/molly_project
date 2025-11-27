import os
import sys
import json
import logging
from datetime import datetime
from typing import Dict, Any, Optional, List

# El path del proyecto es manejado por el nuevo app.py de Flask. 
# Si la estructura es correcta, las importaciones relativas deberían funcionar.

# Importar módulos necesarios (Asumiendo que las carpetas 'core', 'utils', 'reports' están en el mismo nivel que app.py)
from core.data_manager import DataManager
from core.session_manager import SessionManager
from core.context_protocol import ModelContextProtocol
from utils.command_runner import CommandRunner
from reports.report_formatter import ReportFormatter
from reports.report_generator import ReportGenerator
from utils.prompts import GENERAL_VULNERABILITY_ANALYSIS_PROMPT_TEMPLATE, SYSTEM_PROMPT, TOOLS
import google.generativeai as genai

# Importar los handlers
from core.orchestrator_handlers.scan_handler import ScanHandler
from core.orchestrator_handlers.ai_handler import AiHandler
from core.orchestrator_handlers.report_handler import ReportHandler

logger = logging.getLogger(__name__)

class MainOrchestrator:
    def __init__(self, data_manager: DataManager, session_manager: SessionManager,
                 model_context_protocol: ModelContextProtocol, command_runner: CommandRunner,
                 report_formatter: ReportFormatter, report_generator: ReportGenerator):
        self.data_manager = data_manager
        self.session_manager = session_manager
        self.base_model_context_protocol = model_context_protocol
        self.command_runner = command_runner
        self.report_formatter = report_formatter
        self.report_generator = report_generator

        self.gemini_chat_sessions: Dict[str, ModelContextProtocol] = {}

        # Inicializar los handlers con las dependencias necesarias
        self.scan_handler = ScanHandler(data_manager, session_manager, command_runner, self.get_gemini_chat_session, self._process_ai_analysis_with_tool_results, GENERAL_VULNERABILITY_ANALYSIS_PROMPT_TEMPLATE)
        self.ai_handler = AiHandler(self.get_gemini_chat_session)
        self.report_handler = ReportHandler(data_manager, report_formatter, report_generator)

        logger.info("[MainOrchestrator] Inicializado. Listo para orquestar operaciones.")

    def _log(self, message: str):
        logger.info(f"[MainOrchestrator] {message}")

    def reset_gemini_chat_session(self, chat_session_id: str):
        """Reinicia o crea una nueva sesión de chat de Gemini."""
        self.gemini_chat_sessions[chat_session_id] = ModelContextProtocol(
            api_key=self.base_model_context_protocol.api_key,
            model_name=self.base_model_context_protocol.model_name
        )
        logger.info(f"[MainOrchestrator] Sesión de chat de Gemini reiniciada/creada para ID: {chat_session_id}")

    def get_gemini_chat_session(self, chat_session_id: str) -> ModelContextProtocol:
        """Obtiene una sesión de chat de Gemini existente o crea una nueva si no existe."""
        if chat_session_id not in self.gemini_chat_sessions:
            logger.warning(f"[MainOrchestrator] Sesión de chat de Gemini no encontrada para ID {chat_session_id}. Creando una nueva.")
            self.reset_gemini_chat_session(chat_session_id)
        return self.gemini_chat_sessions[chat_session_id]

    def _process_ai_analysis_with_tool_results(self, tool_output_data: Dict[str, Any], user_follow_up_prompt: str = "", chat_session_id: str = None) -> Optional[str]:
        """
        Procesa los resultados de una herramienta inyectándolos en el historial de chat de Gemini.
        Esta es una función helper que el ScanHandler necesita para comunicarse con la IA.
        """
        if chat_session_id is None:
            logger.error("chat_session_id es requerido para _process_ai_analysis_with_tool_results.")
            return "Error interno: ID de sesión no proporcionado."

        return self.ai_handler.process_tool_results_and_get_ai_response(tool_output_data, user_follow_up_prompt, chat_session_id)

    def start_network_scan(self, target: str, session_name: str, chat_session_id: str, nmap_profile: str = 'default_scan') -> Dict[str, Any]:
        """
        Delega la operación de escaneo de red al ScanHandler.
        """
        # Esta función ya devuelve un Dict[str, Any] del ScanHandler, lo cual es correcto.
        return self.scan_handler.start_network_scan(target, session_name, chat_session_id, nmap_profile)

    def process_user_query_for_data(self, user_query: str, chat_session_id: str) -> Dict[str, Any]:
        """
        Intenta responder a preguntas del usuario buscando datos en la DB o delegando a la IA.
        """
        # ... (La lógica interna es correcta para retornar {"response": response_text}) ...
        
        # La lógica de búsqueda de la DB se quedará en MainOrchestrator por ahora,
        # o se pasará a un DataQueryHandler.
        all_scans = self.data_manager.get_all_scan_sessions()
        last_completed_scan = next((s for s in sorted(all_scans, key=lambda x: x['start_time'], reverse=True) if s['status'] == 'completed'), None)

        response_text = "Lo siento, no pude encontrar información relevante. Por favor, sé más específico o inicia un nuevo escaneo."

        if last_completed_scan:
            scan_id = last_completed_scan['id']
            target = last_completed_scan['target']
            
            if any(phrase in user_query.lower() for phrase in ["puertos abiertos", "servicios", "qué puertos", "versiones", "dame los puertos"]):
                hosts = self.data_manager.get_hosts_for_scan(scan_id)
                if hosts:
                    port_info_lines = []
                    port_info_lines.append(f"Para el último escaneo en {target} (ID: {scan_id}), se encontraron los siguientes servicios:")
                    for host in hosts:
                        services = self.data_manager.get_services_for_host(host['id'])
                        if services:
                            port_info_lines.append(f"\n**Host: {host['ip_address']} ({host['hostname'] or 'N/A'})**")
                            for svc in services:
                                port_info_lines.append(f"- Puerto: {svc['port']}/{svc['protocol']}, Servicio: {svc['service_name'] or 'Desconocido'}, Versión: {svc['version'] or 'N/A'}")
                        else:
                            port_info_lines.append(f"\n**Host: {host['ip_address']} ({host['hostname'] or 'N/A'})**: No se encontraron servicios abiertos.")
                    
                    if len(port_info_lines) > 1:
                        response_text = "\n".join(port_info_lines)
                    else:
                        response_text = f"En el último escaneo de {target}, no se encontraron puertos o servicios abiertos."
                else:
                    response_text = f"No se encontraron hosts en el último escaneo de {target}."
            else:
                # Para otras preguntas que no sean de listado directo, sigue usando la IA
                response_text = self.ai_handler.ask_gemini_about_data_context(user_query, last_completed_scan, chat_session_id)
            
        return {"response": response_text}

    def handle_user_query(self, user_query: str, chat_session_id: str) -> Dict[str, Any]:
        """
        Maneja la consulta general del usuario, determinando si es una acción de sistema
        o una pregunta de conocimiento, delegando a los handlers apropiados.
        """
        model_context = self.get_gemini_chat_session(chat_session_id)

        logger.info(f"[MainOrchestrator] Procesando consulta del usuario para sesión {chat_session_id}: '{user_query}'")

        try:
            ai_response = model_context.ask_gemini(
                objective="Determinar si el usuario solicita una acción del sistema o una respuesta de conocimiento.",
                input_type="Comando de usuario",
                input_data=user_query,
                response_requirements="Devolver JSON para acción o texto directo para pregunta de conocimiento. Mantener un historial conversacional."
            )

            if isinstance(ai_response, dict) and 'action' in ai_response:
                action = ai_response['action']
                params = ai_response.get('parameters', ai_response.get('params', {}))
                # Fallback por si 'target' o 'session_name' están directamente en la raíz
                if 'target' in ai_response and 'target' not in params:
                    params['target'] = ai_response['target']
                if 'session_name' in ai_response and 'session_name' not in params:
                    params['session_name'] = ai_response['session_name']


                logger.info(f"IA solicitó la acción: {action} con parámetros: {params}")

                if action == 'start_network_scan':
                    target = params.get('target')
                    session_name = params.get('session_name')

                    if not target:
                        ai_clarification = model_context.ask_gemini(
                            objective="Solicitar al usuario que especifique el objetivo del escaneo, dada la falta de información en la solicitud original.",
                            input_type="Error de comando: target faltante",
                            input_data=user_query,
                            response_requirements="Respuesta amigable solicitando el IP o rango para el escaneo."
                        )
                        # --- CORRECCIÓN 1: Envolver la respuesta de clarificación en un dict ---
                        return {"response": ai_clarification} 

                    if not session_name:
                        session_name = f"Escaneo_IA_{target.replace('.', '_').replace('/', '_')}_{self.data_manager.generate_timestamp()}"

                    try:
                        # Delega al ScanHandler para ejecutar el escaneo y análisis de IA
                        scan_result = self.scan_handler.start_network_scan(target, session_name, chat_session_id)

                        if scan_result['status'] == 'success':
                            final_ai_summary = scan_result['ai_summary']
                            scan_id = scan_result['scan_id'] # Obtener el scan_id del resultado del scan_handler

                            # --- ¡NUEVA LÓGICA AQUÍ: GENERAR REPORTE PDF! ---
                            logger.info(f"[MainOrchestrator] Generando reporte PDF para escaneo {scan_id}...")
                            pdf_path = self.report_handler.generate_network_summary_report(
                                scan_id, session_name, target, final_ai_summary # Pasa todos los datos necesarios
                            )
                            if pdf_path:
                                logger.info(f"[MainOrchestrator] Reporte PDF generado en: {pdf_path}")
                                # Actualizar la sesión en la DB con la ruta del reporte
                                self.data_manager.update_scan_session(scan_id, status='completed', results_path=pdf_path)
                            else:
                                logger.warning(f"[MainOrchestrator] No se pudo generar el reporte PDF para el escaneo {scan_id}.")
                                # Asegurarse de que el estado sea 'completed' aunque no haya reporte PDF
                                self.data_manager.update_scan_session(scan_id, status='completed')
                            # --- FIN NUEVA LÓGICA ---
                            
                            # --- CORRECCIÓN 2: Devolver el resumen de la IA + scan_id ---
                            return {
                                "response": final_ai_summary,
                                "scan_id": scan_id,
                                "pdf_path": pdf_path if pdf_path else "N/A" # Opcional, para mostrar el link si existe
                            }
                        else:
                            # --- CORRECCIÓN 3: Envolver el mensaje de error del scan_result ---
                            return {"response": scan_result['message']}

                    except Exception as e:
                        logger.error(f"Error al ejecutar la acción 'start_network_scan' desde la IA: {e}")
                        model_context.inject_tool_results_into_chat(
                            {"action": "start_network_scan_error", "target": target, "error": str(e)},
                            f"Lo siento, hubo un problema técnico al intentar escanear {target}. Por favor, ¿podrías intentarlo de nuevo o especificar un objetivo diferente?"
                        )
                        # --- CORRECCIÓN 4: Envolver el mensaje de excepción ---
                        return {"response": f"Hubo un error al iniciar el escaneo de red: {e}"}

                elif action == 'get_scan_results':
                    # Delega al ReportHandler para obtener y formatear los resultados
                    scan_id_param = params.get('scan_id')
                    session_name_param = params.get('session_name')

                    response = self.report_handler.get_scan_results_for_ai(scan_id_param, session_name_param, chat_session_id, model_context)
                    # --- CORRECCIÓN 5: Envolver la respuesta de la IA/Reporte ---
                    return {"response": response}

                elif action == 'generate_detailed_host_report':
                    host_ip = params.get('host_ip')
                    session_name = params.get('session_name')
                    if not host_ip or not session_name:
                        # --- CORRECCIÓN 6: Envolver el mensaje de error de parámetros ---
                        return {"response": "Por favor, especifica tanto la IP del host como el nombre de la sesión para generar el informe detallado."}
                        
                    pdf_path = self.report_handler.generate_detailed_host_report(host_ip, session_name)
                    if pdf_path:
                        # --- CORRECCIÓN 7: Envolver el mensaje de éxito ---
                        return {"response": f"Informe detallado para {host_ip} en la sesión '{session_name}' generado exitosamente: {pdf_path}"}
                    else:
                        # --- CORRECCIÓN 8: Envolver el mensaje de falla ---
                        return {"response": f"No se pudo generar el informe detallado para {host_ip} en la sesión '{session_name}'. Verifica que el host exista en esa sesión."}

                else:
                    # --- CORRECCIÓN 9: Envolver el mensaje de acción desconocida ---
                    return {"response": f"La IA sugirió una acción ('{action}') que aún no puedo ejecutar. Por favor, intenta de nuevo o haz una pregunta diferente."}

            else:
                logger.info("Respuesta de la IA es texto directo (no una acción).")
                # Si la IA no detecta una acción, delega al AiHandler para una respuesta de conocimiento.
                # --- CORRECCIÓN 10: Envolver la respuesta general de la IA ---
                return {"response": self.ai_handler.process_general_query(user_query, chat_session_id)}

        except genai.types.BlockedPromptException as e:
            logger.error(f"Consulta bloqueada por la API de Gemini para sesión {chat_session_id}: {e}")
            # --- CORRECCIÓN 11: Envolver el mensaje de error de bloqueo ---
            return {"response": "Lo siento, tu consulta fue bloqueada por las políticas de seguridad de la IA."}
        except Exception as e:
            logger.error(f"Error al llamar a Gemini API para sesión {chat_session_id}: {e}")
            if "429 You exceeded your current quota" in str(e):
                # --- CORRECCIÓN 12: Envolver el mensaje de error de cuota ---
                return {"response": "He excedido mi cuota de solicitudes. Por favor, intenta de nuevo más tarde."}
            # --- CORRECCIÓN 13: Envolver el mensaje de excepción general ---
            return {"response": f"Hubo un error al comunicarse con la IA: {e}"}

    def generate_detailed_host_report(self, host_ip: str, session_name: str) -> Optional[str]:
        """Delega la generación de informes detallados al ReportHandler."""
        return self.report_handler.generate_detailed_host_report(host_ip, session_name)