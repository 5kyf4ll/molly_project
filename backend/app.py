# app.py
from flask import Flask
import os
import yaml
from dotenv import load_dotenv
import logging
from datetime import timedelta

# IMPORTANTE: importar CORS para el frontend
from flask_cors import CORS

# Importar el orquestador y otras clases
from core.main_orchestrator import MainOrchestrator
from core.data_manager import DataManager
from core.session_manager import SessionManager
from utils.command_runner import CommandRunner
from core.context_protocol import ModelContextProtocol
from reports.report_formatter import ReportFormatter
from reports.report_generator import ReportGenerator

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

load_dotenv()

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def create_app():
    app = Flask('app')

    # SECRET KEY y sesiones
    app.config['SECRET_KEY'] = os.environ.get(
        'SECRET_KEY',
        'una_clave_secreta_muy_segura_y_aleatoria_por_favor_cambiala'
    )
    app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(minutes=30)

    # ⭐⭐⭐ CORS AGREGADO AQUI ⭐⭐⭐
    CORS(app,
         supports_credentials=True,
         origins=["http://192.168.1.38:3000"])

    # Cargar config YAML
    config_path = os.path.join(BASE_DIR, 'instance', 'config', 'general_config.yaml')
    default_scan_output_dir = os.path.join(BASE_DIR, 'instance', 'scans')

    try:
        with open(config_path, 'r') as f:
            app.config.update(yaml.safe_load(f))
        logger.info(f"Configuracion cargada desde: {config_path}")
    except FileNotFoundError:
        logger.warning(f"No se encontro {config_path}. Usando config por defecto.")
        app.config.setdefault('GEMINI_MODEL', 'gemini-2.5-flash-preview-09-2025')
        app.config.setdefault('NMAP_TIMEOUT_SECONDS', 300)
        app.config.setdefault('SCAN_OUTPUT_DIR', default_scan_output_dir)

    # Inicializar componentes Molly
    app.data_manager = DataManager()
    app.session_manager = SessionManager(app.data_manager)

    app.command_runner = CommandRunner(
        timeout=app.config.get('NMAP_TIMEOUT_SECONDS', 300)
    )
    app.report_formatter = ReportFormatter()

    app.report_generator = ReportGenerator(
        report_path_root=app.config.get('SCAN_OUTPUT_DIR', default_scan_output_dir),
        report_formatter=app.report_formatter
    )

    gemini_api_key = os.getenv("GEMINI_API_KEY")
    if not gemini_api_key:
        logger.error("ERROR: GEMINI_API_KEY no encontrada en .env")
        gemini_api_key = ""

    app.model_context_protocol = ModelContextProtocol(
        api_key=gemini_api_key,
        model_name=app.config.get('GEMINI_MODEL', 'gemini-2.5-flash-preview-09-2025')
    )

    app.orchestrator = MainOrchestrator(
        data_manager=app.data_manager,
        session_manager=app.session_manager,
        model_context_protocol=app.model_context_protocol,
        command_runner=app.command_runner,
        report_formatter=app.report_formatter,
        report_generator=app.report_generator
    )

    app.config["GEMINI_API_KEY"] = gemini_api_key

    # Cargar rutas
    try:
        from .routes import register_routes
    except ImportError:
        logger.warning("No se pudo importar routes como modulo. Intentando import local...")
        import routes
        register_routes = routes.register_routes

    register_routes(app)

    return app


if __name__ == '__main__':
    app = create_app()
    logger.info("Molly Core inicializado con exito.")
    logger.info("Iniciando Flask en http://0.0.0.0:5000")
    app.run(host='0.0.0.0', port=5000, debug=False)
