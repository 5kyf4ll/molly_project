from flask import request, jsonify, current_app, send_from_directory, url_for, make_response
from flask_cors import CORS
import logging
import os

from core.auth_session_manager import AuthSessionManager

logger = logging.getLogger(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Crear el manejador global de sesiones de usuario
auth_sessions = AuthSessionManager()


def register_routes(app):
    """
    Registra todas las rutas (endpoints) de la API de Molly.
    """

    CORS(app)

    # -----------------------------------------------------
    # 1. HEALTH CHECK
    # -----------------------------------------------------
    @app.route('/', methods=['GET'])
    def health_check():
        return jsonify({"status": "Backend OK", "service": "Molly API"}), 200

    # -----------------------------------------------------
    # 2. LOGIN REAL (con token via cookie)
    # -----------------------------------------------------
    @app.route('/api/login', methods=['POST'])
    def login_api():
        data = request.get_json()
        username = data.get("username")
        password = data.get("password")

        if username == "admin" and password == "admin":
            token = auth_sessions.create_session(user_id=1)

            resp = jsonify({"message": "Login OK"})
            resp.set_cookie("session", token, httponly=True)
            return resp, 200

        return jsonify({"error": "Credenciales invalidas"}), 401

    # -----------------------------------------------------
    # VALIDACIÓN
    # -----------------------------------------------------
    def require_auth():
        token = request.cookies.get("session")
        return auth_sessions.validate_session(token)

    def get_user_token():
        return request.cookies.get("session")

    # -----------------------------------------------------
    # 3. CHAT CON MOLLY
    # -----------------------------------------------------
    @app.route('/api/chat', methods=['POST'])
    def chat_api():
        if not require_auth():
            return jsonify({"error": "Sesion no valida"}), 401

        data = request.get_json()
        user_message = data.get("message")

        if not user_message:
            return jsonify({"error": "Mensaje vacio"}), 400

        # ID de chat unico por usuario (basado en su token)
        token = get_user_token()
        chat_session_id = f"chat-{token}"

        try:
            response = current_app.orchestrator.handle_user_query(
                user_message,
                chat_session_id=chat_session_id
            )

            # Sesion de trabajo de Molly (escaneos)
            scan_info = current_app.session_manager.get_current_scan_info()

            return jsonify({
                "response": response,
                "session_status": scan_info,
                "active_project": scan_info.get("session_name")
            }), 200

        except Exception as e:
            current_app.logger.error(f"Error en /api/chat: {e}", exc_info=True)
            return jsonify({"error": "Error interno"}), 500

    # -----------------------------------------------------
    # 4. CHECK SCAN STATUS
    # -----------------------------------------------------
    @app.route('/api/check_scan_status/<int:scan_id>', methods=['GET'])
    def check_scan_status(scan_id):
        if not require_auth():
            return jsonify({"error": "Sesion no valida"}), 401

        scan_details = current_app.data_manager.get_scan_details(scan_id)

        if not scan_details:
            return jsonify({"status": "not_found"}), 404

        status = scan_details.get("status")

        if status in ["completed", "failed"]:
            report_url = url_for("view_report", scan_id=scan_id, _external=True)
            return jsonify({
                "status": status,
                "summary": scan_details.get("summary", ""),
                "report_url": report_url
            }), 200

        return jsonify({"status": "in_progress"}), 200

    # -----------------------------------------------------
    # 5. SESSION STATUS
    # -----------------------------------------------------
    @app.route('/api/session_status', methods=['GET'])
    def get_session_status_api():
        if not require_auth():
            return jsonify({"error": "Sesion no valida"}), 401

        scan_info = current_app.session_manager.get_current_scan_info()

        return jsonify({
            "status": scan_info,
            "active_project": scan_info.get("session_name"),
        }), 200

    # -----------------------------------------------------
    # 6. LISTA DE ESCANEOS
    # -----------------------------------------------------
    @app.route('/api/scans', methods=['GET'])
    def get_all_scans_api():
        if not require_auth():
            return jsonify({"error": "Sesion no valida"}), 401

        scans = current_app.data_manager.get_all_scan_sessions()
        return jsonify(scans), 200

    # -----------------------------------------------------
    # 7. VER PDF DEL REPORTE
    # -----------------------------------------------------
    @app.route('/view_report/<int:scan_id>')
    def view_report(scan_id):
        if not require_auth():
            return "Acceso denegado", 403

        scan_details = current_app.data_manager.get_scan_details(scan_id)
        if not scan_details:
            return "No encontrado", 404

        path = scan_details.get("results_path")
        directory = os.path.dirname(path)
        filename = os.path.basename(path)

        abs_dir = os.path.join(BASE_DIR, directory)

        try:
            response = make_response(send_from_directory(
                abs_dir, filename, as_attachment=False, mimetype="application/pdf"
            ))
            response.headers["Content-Disposition"] = "inline"
            return response
        except Exception as e:
            current_app.logger.error(f"Error PDF: {e}")
            return "Error al abrir PDF", 500
