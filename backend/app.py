from flask import Flask
import os
import yaml
from dotenv import load_dotenv
import logging # Importar el módulo logging
from datetime import timedelta # Importar timedelta para la duración de la sesión

# Importar el orquestador y otras clases que la web necesitará
# NOTA: Las rutas de importación son relativas a la ejecución de app.py
from core.main_orchestrator import MainOrchestrator
from core.data_manager import DataManager
from core.session_manager import SessionManager
from utils.command_runner import CommandRunner
from core.context_protocol import ModelContextProtocol
from reports.report_formatter import ReportFormatter
from reports.report_generator import ReportGenerator

# Obtener el directorio base para resolver rutas de forma confiable
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Cargar variables de entorno al iniciar la app
load_dotenv()

# Configuración básica de logging para la aplicación
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def create_app():
    # El nombre de la aplicación es 'app' para que Flask la encuentre
    app = Flask('app') 

    # --- Configuración de Flask Sessions ---
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'una_clave_secreta_muy_segura_y_aleatoria_por_favor_cambiala')
    app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(minutes=30) 

    # --- Cargar configuración general desde YAML ---
    config_path = os.path.join(BASE_DIR, 'instance', 'config', 'general_config.yaml')
    
    # Rutas por defecto seguras, relativas a BASE_DIR
    default_scan_output_dir = os.path.join(BASE_DIR, 'instance', 'scans')

    try:
        # Intentamos cargar el archivo de configuración
        with open(config_path, 'r') as f:
            app.config.update(yaml.safe_load(f))
        logger.info(f"Configuración cargada desde: {config_path}")
    except FileNotFoundError:
        logger.warning(f"Advertencia: No se encontró el archivo de configuración en {config_path}. Usando configuración por defecto.")
        # Configuración por defecto si el archivo no existe
        app.config.setdefault('GEMINI_MODEL', 'gemini-2.5-flash-preview-09-2025')
        app.config.setdefault('NMAP_TIMEOUT_SECONDS', 300)
        app.config.setdefault('SCAN_OUTPUT_DIR', default_scan_output_dir)


    # --- Inicializar componentes de Molly y adjuntarlos a la aplicación ---
    # CORRECCIÓN: DataManager se inicializa sin argumentos para usar su lógica interna
    app.data_manager = DataManager()
    app.session_manager = SessionManager(app.data_manager)

    app.command_runner = CommandRunner(
        timeout=app.config.get('NMAP_TIMEOUT_SECONDS', 300)
    )
    app.report_formatter = ReportFormatter()
    
    # CRÍTICA: Usar 'report_path_root' (corregido en el paso anterior)
    app.report_generator = ReportGenerator(
        report_path_root=app.config.get('SCAN_OUTPUT_DIR', default_scan_output_dir),
        report_formatter=app.report_formatter
    )

    # La API Key de Gemini se obtiene directamente desde .env
    gemini_api_key = os.getenv("GEMINI_API_KEY")
    if not gemini_api_key:
        logger.error("ERROR: GEMINI_API_KEY no encontrada en el archivo .env. La IA no funcionará correctamente.")
        gemini_api_key = "" # Se pasa una cadena vacía

    app.model_context_protocol = ModelContextProtocol(
        api_key=gemini_api_key,
        model_name=app.config.get('GEMINI_MODEL', 'gemini-2.5-flash-preview-09-2025')
    )

    # Inicializar el Orchestrator
    app.orchestrator = MainOrchestrator(
        data_manager=app.data_manager,
        session_manager=app.session_manager,
        model_context_protocol=app.model_context_protocol,
        command_runner=app.command_runner,
        report_formatter=app.report_formatter,
        report_generator=app.report_generator
    )

    # Importar y registrar las rutas de la aplicación
    try:
        # Importación esperada para Flask apps
        from .routes import register_routes 
    except ImportError:
         logger.warning("No se pudo importar 'routes.py' como sub-módulo. Intentando importación local.")
         # Intentaremos una importación local si es un archivo hermano
         import routes 
         register_routes = routes.register_routes


    register_routes(app)

    return app

# Este bloque solo se ejecuta si el script se corre directamente (ej. python app.py)
if __name__ == '__main__':
    app = create_app()
    logger.info("Molly Core inicializado con éxito.")
    logger.info("Iniciando servidor Flask en http://0.0.0.0:5000")
    app.run(host='0.0.0.0', port=5000, debug=False)