# src/core/auth_session_manager.py

import uuid
from datetime import datetime, timedelta

class AuthSessionManager:
    """
    Maneja las sesiones de USUARIO (login/logout) para la API.
    No interfiere con las sesiones internas de escaneo de Molly.
    """
    def __init__(self):
        # token: { user_id, created, active }
        self.sessions = {}
        self.timeout = timedelta(hours=6)  # Duracion de la sesion

    def create_session(self, user_id):
        """
        Crea una nueva sesión y devuelve un token UUID4.
        """
        token = str(uuid.uuid4())

        self.sessions[token] = {
            "user_id": user_id,
            "created": datetime.utcnow(),
            "active": True
        }

        return token

    def validate_session(self, token):
        """
        Valida si una sesión existe, está activa y no ha expirado.
        """
        if not token:
            return False

        data = self.sessions.get(token)
        if not data:
            return False

        # Expiración
        if datetime.utcnow() - data["created"] > self.timeout:
            data["active"] = False
            return False

        return data["active"]

    def end_session(self, token):
        """
        Marca la sesión como terminada.
        """
        if token in self.sessions:
            self.sessions[token]["active"] = False

    def get_user_id(self, token):
        """
        Devuelve el user_id asociado a un token válido.
        """
        if not token:
            return None

        data = self.sessions.get(token)
        if data and data["active"]:
            # Verificar expiración una vez más
            if datetime.utcnow() - data["created"] <= self.timeout:
                return data["user_id"]

        return None

    def cleanup_expired_sessions(self):
        """
        Opcional: elimina de memoria sesiones expiradas o inactivas.
        Puedes llamarlo periódicamente si quieres.
        """
        now = datetime.utcnow()
        expired = []

        for token, data in self.sessions.items():
            if not data["active"] or (now - data["created"] > self.timeout):
                expired.append(token)

        for token in expired:
            del self.sessions[token]
