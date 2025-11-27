# src/utils/prompts.py

import google.generativeai as genai # Necesario para definir las herramientas (TOOLS)

# SYSTEM_PROMPT: La instrucción principal que define la personalidad y el rol de Molly.
# Ahora incluye todas las instrucciones estáticas y de acción.
SYSTEM_PROMPT = """
Eres Molly, tu asistente de ciberseguridad. Tu objetivo principal es ayudar a los usuarios con tareas relacionadas con la seguridad de la red, como escaneos de vulnerabilidades, análisis de servicios y la interpretación de datos de seguridad.
Siempre responde en español.

Si el usuario te pide explícitamente que 'escanees', 'busques', 'analices', 'inicies', 'encuentres' o realices cualquier operación que implique una acción del sistema (no solo una pregunta de conocimiento), debes responder con un objeto JSON.

**Acciones que puedes realizar (y para las cuales debes responder con JSON):**
- **`start_network_scan`**: Para escanear una IP o rango. Requiere `target` (string, ej. '192.168.1.1' o '192.168.1.0/24'). Opcional: `session_name` (string, nombre para la sesión de escaneo).
- **`analyze_service_vulnerability`**: Analiza una vulnerabilidad específica de un servicio basándose en su nombre, versión e IP, y proporciona una descripción y recomendación.
- **`get_scan_results`**: Recupera los detalles completos, hosts, servicios y hallazgos de un escaneo anterior por su ID o nombre de sesión.
- **`generate_detailed_host_report`**: Genera un reporte PDF detallado para un host específico dentro de una sesión de escaneo.

**Capacidades de conocimiento (para las cuales debes responder con texto directo):**
- **Responder Preguntas Generales:** Sobre ciberseguridad, herramientas, conceptos.
- **Proporcionar Detalles de CVEs:** Si se te da un ID de CVE (ej. 'CVE-2007-2768'), puedes explicar de qué trata esa vulnerabilidad.

Si no se detecta una solicitud de acción clara o la acción solicitada no está en la lista de acciones que puedes realizar, o si el usuario hace una pregunta general de ciberseguridad, responde directamente con una respuesta de texto clara y concisa, y NADA MÁS que texto.
"""

# TOOLS: Definición de las funciones que Gemini puede "llamar" a través de la API.
# Estas definiciones son lo que Gemini ve y usa para decidir qué acción tomar.
TOOLS = [
    genai.protos.Tool(
        function_declarations=[
            genai.protos.FunctionDeclaration(
                name="start_network_scan",
                description="Inicia un escaneo de red en el objetivo especificado para descubrir hosts y servicios. Esto puede tomar varios minutos dependiendo del objetivo y el perfil de escaneo.",
                parameters=genai.protos.Schema(
                    type=genai.protos.Type.OBJECT,
                    properties={
                        "target": genai.protos.Schema(
                            type=genai.protos.Type.STRING,
                            description="La dirección IP o rango CIDR del objetivo (ej. '192.168.1.1' o '192.168.1.0/24')."
                        ),
                        "session_name": genai.protos.Schema(
                            type=genai.protos.Type.STRING,
                            description="Un nombre opcional para la sesión de escaneo. Si no se proporciona, se generará uno automáticamente."
                        )
                    },
                    required=["target"]
                )
            ),
            genai.protos.FunctionDeclaration(
                name="analyze_service_vulnerability",
                description="Analiza una vulnerabilidad específica de un servicio basándose en su nombre, versión e IP, y proporciona una descripción y recomendación. Útil para obtener detalles sobre un servicio específico.",
                parameters=genai.protos.Schema(
                    type=genai.protos.Type.OBJECT,
                    properties={
                        "ip_address": genai.protos.Schema(
                            type=genai.protos.Type.STRING,
                            description="La dirección IP del host donde se encuentra el servicio."
                        ),
                        "service_name": genai.protos.Schema(
                            type=genai.protos.Type.STRING,
                            description="El nombre del servicio a analizar (ej. 'ssh', 'http', 'mysql')."
                        ),
                        "service_version": genai.protos.Schema(
                            type=genai.protos.Type.STRING,
                            description="La versión específica del servicio (ej. 'OpenSSH 8.2p1', 'Apache httpd 2.4.41')."
                        )
                    },
                    required=["ip_address", "service_name", "service_version"]
                )
            ),
            genai.protos.FunctionDeclaration(
                name="get_scan_results",
                # DESCRIPCIÓN ACTUALIZADA para indicar que se requiere uno de los dos.
                description="Recupera los detalles completos, hosts, servicios y hallazgos de un escaneo anterior. Se requiere proporcionar el 'scan_id' o el 'session_name' del escaneo.",
                parameters=genai.protos.Schema(
                    type=genai.protos.Type.OBJECT,
                    properties={
                        "scan_id": genai.protos.Schema(
                            type=genai.protos.Type.INTEGER,
                            description="El ID numérico del escaneo."
                        ),
                        "session_name": genai.protos.Schema(
                            type=genai.protos.Type.STRING,
                            description="El nombre de la sesión del escaneo (ej. 'Escaneo_IA_192_168_1_1_20250711_115855')."
                        )
                    },
                    # ELIMINADO: oneOf=[{"required": ["scan_id"]}, {"required": ["session_name"]}]
                    # Los campos no están en 'required' aquí, la lógica de validación
                    # de "uno de los dos" se maneja en el código Python que llama a la herramienta.
                    required=[] # No se requiere ninguno aquí, la descripción lo aclara.
                )
            ),
            genai.protos.FunctionDeclaration(
                name="generate_detailed_host_report",
                description="Genera un reporte PDF detallado para un host específico dentro de una sesión de escaneo.",
                parameters=genai.protos.Schema(
                    type=genai.protos.Type.OBJECT,
                    properties={
                        "host_ip": genai.protos.Schema(
                            type=genai.protos.Type.STRING,
                            description="La dirección IP del host para el cual generar el reporte."
                        ),
                        "session_name": genai.protos.Schema(
                            type=genai.protos.Type.STRING,
                            description="El nombre de la sesión de escaneo a la que pertenece el host."
                        )
                    },
                    required=["host_ip", "session_name"]
                )
            ),
            genai.protos.FunctionDeclaration(
                name="get_cve_details",
                description="Obtiene detalles sobre un CVE específico (ej. CVE-2007-2768).",
                parameters=genai.protos.Schema(
                    type=genai.protos.Type.OBJECT,
                    properties={
                        "cve_id": genai.protos.Schema(
                            type=genai.protos.Type.STRING,
                            description="El ID del CVE (ej. 'CVE-2007-2768')."
                        )
                    },
                    required=["cve_id"]
                )
            )
        ]
    )
]

# Plantillas de prompts para diferentes tipos de análisis o respuestas
# Estas plantillas se usarán para construir el prompt dinámico en ModelContextProtocol.ask_gemini
NMAP_DETAILED_ANALYSIS_PROMPT_TEMPLATE = """
[OBJETIVO_PRINCIPAL]: Analizar escaneo detallado de Nmap para identificar servicios, versiones y posibles vulnerabilidades.
[TIPO_DE_DATOS_ENTRADA]: Salida de comando Nmap
[DATOS_ENTRADA]:
{nmap_output}

[REQUISITOS_RESPUESTA]: Enumeración estructurada de puertos abiertos, servicios, versiones, y una lista de vulnerabilidades potenciales o hallazgos relevantes. Para cada hallazgo, indicar la criticidad (Baja, Media, Alta, Crítica) y una breve descripción.
"""

FTP_ANONYMOUS_ANALYSIS_PROMPT_TEMPLATE = """
[OBJETIVO_PRINCIPAL]: Analizar resultados de intento de login FTP anónimo y listar archivos encontrados.
[TIPO_DE_DATOS_ENTRADA]: Resultado de login FTP y lista de archivos
[DATOS_ENTRADA]:
FTP Login Exitoso: {success_status}
Archivos Encontrados: {files_list}
Archivos Descargados: {downloaded_files_list}

[REQUISITOS_RESPUESTA]: Confirmación de éxito/fracaso, lista clara de archivos encontrados y descargados. Si se descargó 'nota.txt', solicitar su análisis.
"""

FTP_NOTE_ANALYSIS_PROMPT_TEMPLATE = """
[OBJETIVO_PRINCIPAL]: Analizar el contenido de un archivo (nota.txt) encontrado vía FTP anónimo para extraer información sensible o credenciales.
[TIPO_DE_DATOS_ENTRADA]: Contenido de archivo de texto
[DATOS_ENTRADA]:
{file_content}

[REQUISITOS_RESPUESTA]: Cualquier nombre de usuario, contraseña, clave, URL o información de configuración que pueda ser útil para futuras etapas de seguridad. Si no se encontró nada, indicar "No se encontró información sensible aparente."
"""

HYDRA_SSH_ANALYSIS_PROMPT_TEMPLATE = """
[OBJETIVO_PRINCIPAL]: Analizar la salida del comando Hydra para identificar si se encontró una contraseña SSH válida para el usuario especificado.
[TIPO_DE_DATOS_ENTRADA]: Salida de comando Hydra
[DATOS_DATOS]:
{hydra_output}

[REQUISITOS_RESPUESTA]: La contraseña SSH encontrada si el ataque fue exitoso, en el formato "Contraseña SSH: [password]". Si no se encontró la contraseña, indicar "Contraseña SSH no encontrada."
"""

GENERAL_VULNERABILITY_ANALYSIS_PROMPT_TEMPLATE = """
Eres un asistente de ciberseguridad experto llamado Molly. Tu tarea es analizar los resultados de un escaneo de red y los hallazgos de vulnerabilidades, incluyendo los CVEs encontrados, para generar un resumen conversacional y útil para el usuario.

**Información proporcionada:**
- **Resumen del escaneo de Nmap:** Detalles de los hosts y puertos encontrados.
- **Hallazgos de vulnerabilidades (IA):** Vulnerabilidades detectadas por tu análisis previo de banners.
- **CVEs encontrados por servicio:** Una lista de CVEs relevantes para cada servicio detectado, con su ID, descripción, severidad y referencias. Esta información se encuentra en `tool_output['parsed_data_summary']['cves_found_by_service']`.

**Requisitos para tu respuesta:**
1.  **Inicia con un saludo amigable** y confirma que el escaneo ha finalizado.
2.  **Resume los resultados principales del escaneo de Nmap:** Cuántos hosts se encontraron y el objetivo.
3.  **Para cada servicio relevante (con vulnerabilidades o CVEs):**
    * Menciona el servicio, puerto y versión.
    * Si se encontraron CVEs para ese servicio, lista los IDs de CVE (ej. "Lista de CVE IDs para OpenSSH 5.3p1: - CVE-2007-2768, - CVE-2008-3844").
    * Si se detectaron vulnerabilidades por tu análisis (del `vulnerabilities_found`), resúmelas brevemente.
4.  **Proporciona recomendaciones generales** basadas en los hallazgos (actualizaciones, mejores prácticas de seguridad, etc.).
5.  **Invita al usuario a interactuar más:** Anima al usuario a preguntar sobre CVEs específicos (ej. "¿Quieres saber más sobre CVE-2007-2768?") o a realizar otras consultas.

**Ejemplo de formato de respuesta deseado (adapta el contenido):**
"¡Hola! El escaneo de la red en [objetivo] ha finalizado. Se detectaron [X] hosts activos.

Para el host [IP_HOST]:
- Servicio [Nombre_Servicio] (Puerto [Puerto]) versión [Versión]: Se identificaron las siguientes vulnerabilidades: [Resumen de vulnerabilidades IA].
  Lista de CVE IDs para [Nombre_Servicio] [Versión]:
  - [CVE-ID-1]
  - [CVE-ID-2]
  ...
  Se recomienda [recomendaciones específicas para este servicio].

[Repite para otros hosts/servicios relevantes]

En general, te recomiendo [recomendaciones generales, ej. mantener el software actualizado, aplicar parches].

Si quieres saber más detalles sobre un CVE específico, como CVE-2007-2768, ¡solo pregúntame! También puedo ayudarte con otras consultas de ciberseguridad."

Asegúrate de que la respuesta sea conversacional y fácil de leer.
"""

USER_QUESTION_PROMPT_TEMPLATE = """
[OBJETIVO_PRINCIPAL]: Responder a una pregunta específica del usuario sobre el proceso de seguridad, los hallazgos o posibles mejoras.
[TIPO_DE_DATOS_ENTRADA]: Pregunta del usuario y contexto del historial de operaciones
[DATOS_ENTRADA]:
Pregunta del usuario: {user_question}
Contexto del historial de Molly: {molly_history_summary}

[REQUISITOS_RESPUESTA]: Respuesta clara, concisa y útil, haciendo referencia al historial si es relevante, y sugiriendo mejoras o explicaciones detalladas cuando sea apropiado.
"""
