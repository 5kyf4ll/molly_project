from flask import request, jsonify, current_app, send_from_directory, url_for, session, make_response
from flask_cors import CORS 
import json
import logging
import os
import uuid

logger = logging.getLogger(__name__)

# Definir la ruta raíz del proyecto (donde se encuentra app.py)
# Esto es CRÍTICO para servir los reportes de manera segura.
BASE_DIR = os.path.dirname(os.path.abspath(__file__)) 

def register_routes(app):
    """
    Registra todas las rutas (endpoints) de la API de la aplicación Molly.
    """
    
    # CRÍTICO: Habilitar CORS para permitir que el frontend (React) se comunique con la API de Flask
    CORS(app) 

    # --- Rutas de API para el chat con la IA ---
    @app.route('/api/chat', methods=['POST'])
    def chat_api():
        """
        Endpoint de API para interactuar con la IA.
        Recibe un mensaje del usuario y devuelve la respuesta de la IA.
        """
        # Usamos request.get_json() ya que el frontend enviará JSON
        user_message = request.get_json().get('message')
        # En una arquitectura SPA (Single Page App), el chat_session_id se maneja en la sesión de Flask
        chat_session_id = session.get('chat_session_id')

        if not user_message:
            return jsonify({"error": "Mensaje no proporcionado"}), 400

        if not chat_session_id:
            # Inicialización de sesión de chat si es la primera petición
            session['chat_session_id'] = str(uuid.uuid4())
            chat_session_id = session['chat_session_id']
            current_app.orchestrator.reset_gemini_chat_session(chat_session_id)
            current_app.logger.warning(f"Nueva sesión de chat Flask iniciada en /api/chat: {chat_session_id}")

        try:
            # La respuesta del orquestador debe ser un diccionario con 'response' y potencialmente 'artifact'
            final_response_from_orchestrator = current_app.orchestrator.handle_user_query(
                user_message,
                chat_session_id=chat_session_id
            )
            
            # El frontend necesita saber si hay una sesión activa de Molly (e.g., Proyecto X)
            session_status = current_app.session_manager.get_session_status()
            
            # Aseguramos que la respuesta devuelta al frontend sea JSON
            return jsonify({
                "response": final_response_from_orchestrator,
                "session_status": session_status,
                "active_project": current_app.session_manager.active_session_name,
            }), 200

        except Exception as e:
            current_app.logger.error(f"Error en la API de chat: {e}", exc_info=True)
            return jsonify({"error": f"Error interno del servidor al procesar tu solicitud: {e}"}), 500

    # --- RUTA PARA MONITOREAR EL ESTADO DEL ESCANEO ---
    @app.route('/api/check_scan_status/<int:scan_id>', methods=['GET'])
    def check_scan_status(scan_id):
        """
        Endpoint para que el frontend consulte el estado de un escaneo.
        Devuelve el estado, resumen, y la URL de la vista del reporte.
        """
        scan_details = current_app.data_manager.get_scan_details(scan_id)
        
        if not scan_details:
            return jsonify({"status": "not_found", "message": "Escaneo no encontrado."}), 404

        status = scan_details.get('status')
        
        if status in ['completed', 'failed']:
            summary_from_ai = scan_details.get('summary', 'Escaneo completado/fallido.')
            
            # El frontend usará esta URL para mostrar el reporte PDF.
            report_url = url_for('view_report', scan_id=scan_id, _external=True) 
            
            return jsonify({
                "status": status,
                "summary": summary_from_ai, 
                "report_url": report_url
            }), 200
        else:
            return jsonify({"status": "in_progress"}), 200


    # --- RUTA DE API para obtener el estado de la sesión actual ---
    @app.route('/api/session_status', methods=['GET'])
    def get_session_status_api():
        """
        Devuelve el estado de la sesión activa de Molly (proyecto actual).
        """
        session_manager = current_app.session_manager
        return jsonify({
            "status": session_manager.get_session_status(),
            "active_project": session_manager.active_session_name,
            "last_scan_id": session_manager.active_scan_id,
            "chat_session_id": session.get('chat_session_id') # Útil para el debug en frontend
        }), 200

    # --- RUTA DE API para obtener todos los escaneos ---
    @app.route('/api/scans', methods=['GET'])
    def get_all_scans_api():
        """
        Endpoint para obtener la lista de todas las sesiones de escaneo históricas.
        """
        scans = current_app.data_manager.get_all_scan_sessions()
        return jsonify(scans), 200

    # --- RUTA para VER reportes (abre en el navegador) ---
    @app.route('/view_report/<int:scan_id>')
    def view_report(scan_id):
        """
        Sirve el archivo PDF de reporte solicitado.
        """
        scan_details = current_app.data_manager.get_scan_details(scan_id)
        if not scan_details or not scan_details.get('results_path'):
            return "Informe no encontrado o no disponible.", 404

        full_relative_path = scan_details['results_path'] # e.g., 'instance/scans/session_name/report.pdf'

        # CORRECCIÓN DE RUTA: La carpeta de escaneos está en BASE_DIR/instance/scans
        # full_relative_path debe ser manejada correctamente por ReportGenerator.
        # Asumimos que full_relative_path es la ruta completa desde la raíz del proyecto.
        
        # Para ser seguro, asumimos que 'instance' es el contenedor para 'scans'
        # Usaremos el nombre del directorio que contiene el archivo.
        directory = os.path.dirname(full_relative_path)
        filename = os.path.basename(full_relative_path)

        # La ruta absoluta del directorio base para servir archivos.
        # Si la ruta guardada es 'instance/scans/...', debemos empezar en BASE_DIR.
        # Si la ruta guardada ya es absoluta, esto simplifica el problema.
        # Asumiremos que full_relative_path es relativa al directorio 'backend'.
        # La ruta absoluta para send_from_directory debe ser el path base.
        # Dado que los reportes están en instance/scans, usamos BASE_DIR para encontrar 'instance'.
        absolute_directory = os.path.join(BASE_DIR, directory)
        
        # Nota: La ruta guardada en la DB debe ser relativa a BASE_DIR (ej. 'instance/scans/...')
        if not os.path.isabs(absolute_directory):
             absolute_directory = os.path.join(BASE_DIR, directory)
        
        try:
            response = make_response(send_from_directory(
                absolute_directory, filename, as_attachment=False, mimetype='application/pdf'
            ))
            response.headers['Content-Disposition'] = 'inline'
            return response
        except Exception as e:
            current_app.logger.error(f"Error al servir el archivo PDF {full_relative_path}: {e}", exc_info=True)
            return "Error al cargar el informe.", 500