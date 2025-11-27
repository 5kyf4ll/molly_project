import logging
import json
from typing import Dict, Any, Optional, Callable

# Importar módulos necesarios
from core.data_manager import DataManager
from core.context_protocol import ModelContextProtocol
from utils.prompts import GENERAL_VULNERABILITY_ANALYSIS_PROMPT_TEMPLATE

logger = logging.getLogger(__name__)

class AiHandler:
    def __init__(self, get_gemini_chat_session: Callable[[str], ModelContextProtocol]):
        self.get_gemini_chat_session = get_gemini_chat_session
        logger.info("[AiHandler] Inicializado.")

    def process_tool_results_and_get_ai_response(self, tool_output_data: Dict[str, Any], user_follow_up_prompt: str = "", chat_session_id: str = None) -> Optional[str]:
        """
        Inyecta los resultados de una herramienta en el historial de chat de Gemini
        y obtiene una respuesta de seguimiento de la IA.
        """
        if chat_session_id is None:
            logger.error("chat_session_id es requerido para process_tool_results_and_get_ai_response.")
            return "Error interno: ID de sesión no proporcionado."

        model_context = self.get_gemini_chat_session(chat_session_id)
        logger.info(f"[AiHandler] Inyectando resultados de herramienta en el historial de Gemini para sesión {chat_session_id}...")

        response = model_context.inject_tool_results_into_chat(tool_output_data, user_follow_up_prompt)

        if response:
            logger.info(f"[AiHandler] Respuesta de seguimiento de Gemini después de resultados de herramienta para sesión {chat_session_id}: {response}")
        return response

    def parse_ai_vulnerability_response(self, ai_response: str) -> Optional[Dict[str, Any]]:
        """
        Intenta parsear una respuesta de IA que se espera que sea un JSON de hallazgo de vulnerabilidad.
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

    def process_user_query_for_data(self, user_query: str, chat_session_id: str) -> Dict[str, Any]:
        """
        Responde a preguntas del usuario buscando datos en la DB o delegando a la IA.
        Este método necesita acceso al DataManager, por lo que podría ser mejor que DataManager
        sea una dependencia inyectada si se usa directamente aquí, o que el Orchestrator
        medie. Por ahora, asumimos que Orchestrator le pasa los datos relevantes o se ajusta.
        Dado que el Orchestrator ya tiene DataManager, lo ideal es que el Orchestrator
        recupere los datos y se los pase a la IA para el análisis.
        Mantendremos la lógica actual de Orchestrator.process_user_query_for_data aquí para AI,
        pero la parte de la DB la debería manejar el MainOrchestrator o un DataQueryHandler.

        Para esta refactorización, moveremos solo la parte de AI.
        La lógica de búsqueda de la DB se quedará en MainOrchestrator por ahora,
        o se pasará a un QueryHandler.
        """
        model_context = self.get_gemini_chat_session(chat_session_id)
        logger.info(f"[AiHandler] Procesando consulta de datos del usuario (IA only) para sesión {chat_session_id}: '{user_query}'")

        # Para otras preguntas que no sean de listado directo, usa la IA
        response_text = model_context.ask_gemini(
            objective="Responder a una pregunta del usuario basándose en el contexto del último escaneo.",
            input_type="Pregunta del usuario y contexto general",
            input_data=user_query, # El contexto real de la DB se inyectaría desde el MainOrchestrator si fuera necesario para esta consulta
            response_requirements="Respuesta concisa y útil."
        )

        return {"response": response_text}

    def process_general_query(self, user_query: str, chat_session_id: str) -> str:
        """
        Procesa una consulta de usuario general con la IA cuando no se detecta una acción específica.
        """
        model_context = self.get_gemini_chat_session(chat_session_id)
        logger.info(f"[AiHandler] Procesando consulta general de usuario con IA para sesión {chat_session_id}: '{user_query}'")
        ai_response = model_context.ask_gemini(
            objective="Responder a la pregunta general del usuario.",
            input_type="Consulta de usuario",
            input_data=user_query,
            response_requirements="Respuesta detallada y útil."
        )
        return ai_response