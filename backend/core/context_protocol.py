# src/core/context_protocol.py

import json
import logging
import google.generativeai as genai
import os
from typing import Dict, Any

# Importar SYSTEM_PROMPT y TOOLS desde prompts.py
from utils.prompts import SYSTEM_PROMPT, TOOLS

class ModelContextProtocol:
    def __init__(self, api_key: str, model_name: str = 'models/gemini-1.5-flash-latest'):
        if not api_key:
            raise ValueError("La clave de API de Gemini no puede estar vacía.")
        
        self.api_key = api_key 
        
        genai.configure(api_key=self.api_key)
        
        self.model = genai.GenerativeModel(
            model_name=model_name,
            system_instruction=SYSTEM_PROMPT, 
            tools=TOOLS 
        )
        self.model_name = model_name
        
        self.chat = self.model.start_chat(history=[])
        self.logger = logging.getLogger(__name__)
        self.logger.info(f"[MCP] Inicializado con modelo: {self.model_name}. Historial de chat iniciado con SYSTEM_PROMPT y TOOLS.")

    def ask_gemini(self, objective: str, input_type: str, input_data: str, response_requirements: str) -> str | Dict[str, Any]:
        """
        Envía una consulta a Gemini. Las instrucciones estáticas (rol, herramientas)
        ya están configuradas en el modelo. Este método solo construye el prompt
        con el contexto dinámico de la interacción actual.
        """
        prompt_content = (
            f"**Objetivo actual de esta interacción:** {objective}\n"
            f"**Tipo de entrada:** {input_type}\n"
            f"**Petición del usuario:** {input_data}\n"
            f"**Requisitos de respuesta específicos:** {response_requirements}\n"
        )

        try:
            self.logger.info(f"Enviando a Gemini (vía chat.send_message):\n---PROMPT INICIO---\n{prompt_content}\n---PROMPT FIN---")
            
            response = self.chat.send_message(prompt_content)

            text_response = response.text.strip()
            self.logger.info(f"Respuesta cruda de Gemini:\n{text_response}")

            if '```json' in text_response and '```' in text_response:
                try:
                    json_start = text_response.find('```json') + len('```json')
                    json_end = text_response.find('```', json_start)
                    json_str = text_response[json_start:json_end].strip()

                    parsed_json = json.loads(json_str)

                    if isinstance(parsed_json, dict) and 'action' in parsed_json:
                        self.logger.info(f"Gemini sugirió una acción parseable: {parsed_json}")
                        return parsed_json
                except (json.JSONDecodeError, ValueError) as e:
                    self.logger.warning(f"Gemini intentó devolver JSON pero el formato es inválido o hubo error al parsear: {e}. Tratando como texto normal.")
                except Exception as e:
                    self.logger.error(f"Error inesperado al intentar parsear JSON de Gemini: {e}")

            self.logger.info(f"Gemini respondió con texto (o JSON no parseable/accionable): {text_response}")
            return text_response

        except Exception as e:
            self.logger.error(f"Error al llamar a Gemini API: {e}")
            return "Lo siento, no pude comunicarme con la IA en este momento. Por favor, inténtalo de nuevo más tarde."

    def inject_tool_results_into_chat(self, tool_output: Dict[str, Any], user_follow_up_prompt: str = ""):
        """
        Inyecta los resultados de una herramienta ejecutada en el historial de chat de Gemini
        como un mensaje de usuario (representando la salida de la herramienta).
        Esto permite a Gemini "saber" qué ocurrió después de que sugirió una acción.
        El user_follow_up_prompt permite añadir una pregunta o instrucción adicional
        justo después de los resultados de la herramienta.
        """
        # Aseguramos que el tool_output sea un diccionario serializable a JSON.
        # Si tool_output no es un dict, lo convertimos para evitar errores de serialización.
        if not isinstance(tool_output, dict):
            tool_output = {"result": str(tool_output)} 

        # Formateamos la salida de la herramienta como un bloque de código JSON
        formatted_tool_output_message = f"Aquí están los resultados de la acción solicitada:\n```json\n{json.dumps(tool_output, indent=2)}\n```\n"

        self.logger.info(f"[MCP] Inyectando resultados de herramienta como mensaje de usuario en el chat.")
        try:
            # Enviamos los resultados de la herramienta como un mensaje de usuario normal.
            # Esto evita el error "function response parts" porque no estamos respondiendo
            # directamente a una function_call en este punto de la conversación.
            self.chat.send_message(formatted_tool_output_message)

            # Si hay un prompt de seguimiento, lo enviamos después de la inyección de resultados.
            if user_follow_up_prompt:
                self.logger.info(f"[MCP] Enviando seguimiento de usuario después de resultados de herramienta.")
                response = self.chat.send_message(user_follow_up_prompt)
                return response.text
            
            # Si la inyección de la herramienta genera una respuesta de texto inmediata de Gemini, la devolvemos.
            # Esto es un caso borde, pero es posible que Gemini responda directamente.
            if self.chat.history and self.chat.history[-1].role == 'model' and self.chat.history[-1].parts:
                # Verificamos si el último mensaje del modelo tiene contenido de texto después de la salida de la herramienta.
                # Esta es una heurística; una solución más robusta podría implicar otra llamada al modelo
                # para resumir la salida de la herramienta si no se genera una respuesta de texto directa.
                return self.chat.history[-1].parts[0].text
            
            return None # No hay respuesta de texto de seguimiento.
        except Exception as e:
            self.logger.error(f"[MCP ERROR] Error al inyectar resultados de herramienta en el chat: {e}")
            return f"Error al procesar resultados de herramienta: {e}"

    def reset_chat_history(self):
        """Resetea el historial de chat de la sesión actual."""
        # Al resetear el historial, se mantiene el modelo con su SYSTEM_PROMPT y TOOLS configurados.
        self.chat = self.model.start_chat(history=[])
        self.logger.info("[MCP] Historial de chat reseteado.")

