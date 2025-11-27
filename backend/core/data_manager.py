# core/data_manager.py
import sqlite3
import os
from datetime import datetime
from typing import List, Dict, Any, Optional
import json

class DataManager:
    """
    Gestiona la base de datos SQLite para almacenar y recuperar datos
    de escaneos, hosts, servicios y hallazgos.
    """
    def __init__(self, db_name: str = 'molly_scans.db'):
        self.db_path = os.path.join('data', db_name)
        
        # Asegurarse de que el directorio 'data' exista antes de intentar crear/conectar la DB
        os.makedirs('data', exist_ok=True)
        
        # Verificar si la base de datos ya existe
        db_exists = os.path.exists(self.db_path)

        # Conectar y crear tablas si la DB no existía o si es una nueva conexión
        self._create_tables() # Este método ya usa CREATE TABLE IF NOT EXISTS, lo cual es robusto

        # Actualizamos el mensaje de inicialización
        if db_exists:
            print(f"[DataManager] Inicializado. Base de datos existente: {self.db_path}")
        else:
            print(f"[DataManager] Inicializado. Nueva base de datos creada: {self.db_path}")

    def _create_tables(self):
        """
        Crea las tablas de la base de datos si no existen.
        La conexión a la DB en este método creará el archivo .db si no existe.
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            # Tabla de sesiones de escaneo
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS scans (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_name TEXT NOT NULL UNIQUE,
                    scan_type TEXT NOT NULL,
                    target TEXT NOT NULL,
                    start_time TEXT NOT NULL,
                    end_time TEXT,
                    status TEXT NOT NULL,    -- ¡ESTA COLUMNA ES CLAVE!
                    summary TEXT,
                    results_path TEXT
                )
            """)
            # Tabla de hosts descubiertos
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS hosts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    scan_id INTEGER NOT NULL,
                    ip_address TEXT NOT NULL,
                    hostname TEXT,
                    os_info TEXT,
                    FOREIGN KEY (scan_id) REFERENCES scans(id)
                )
            """)
            # Tabla de servicios/puertos
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS services (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    host_id INTEGER NOT NULL,
                    port INTEGER NOT NULL,
                    protocol TEXT NOT NULL,
                    service_name TEXT,
                    version TEXT,
                    state TEXT,
                    FOREIGN KEY (host_id) REFERENCES hosts(id)
                )
            """)
            # Tabla de hallazgos de seguridad
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS findings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    scan_id INTEGER NOT NULL,
                    host_id INTEGER NOT NULL,
                    service_id INTEGER,
                    type TEXT NOT NULL,
                    title TEXT NOT NULL,
                    description TEXT NOT NULL,
                    severity TEXT,
                    recommendation TEXT,
                    details TEXT,
                    timestamp TEXT NOT NULL,
                    FOREIGN KEY (scan_id) REFERENCES scans(id),
                    FOREIGN KEY (host_id) REFERENCES hosts(id),
                    FOREIGN KEY (service_id) REFERENCES services(id)
                )
            """)
            conn.commit()

    def get_findings_for_scan_and_host(self, scan_id: int, host_id: int) -> List[Dict[str, Any]]:
        """
        Obtiene todos los hallazgos de seguridad asociados a un ID de escaneo y un ID de host específico.
        Los detalles (details) se cargan como JSON.
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM findings WHERE scan_id = ? AND host_id = ?", (scan_id, host_id))
            findings = []
            for row in cursor.fetchall():
                finding = dict(row)
                if finding['details']:
                    try:
                        finding['details'] = json.loads(finding['details'])
                    except json.JSONDecodeError:
                        finding['details'] = {"error": "Invalid JSON in details field"}
                findings.append(finding)
            return findings

    def create_scan_session(self, session_name: str, scan_type: str, target: str, status: str = 'in_progress') -> Optional[int]:
        """
        Crea una nueva sesión de escaneo en la base de datos.
        Acepta un argumento 'status' con un valor por defecto 'in_progress'.
        Retorna el ID de la sesión creada o None si falla.
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                start_time = datetime.now().isoformat()
                cursor.execute(
                    "INSERT INTO scans (session_name, scan_type, target, start_time, status) VALUES (?, ?, ?, ?, ?)",
                    (session_name, scan_type, target, start_time, status)
                )
                conn.commit()
                return cursor.lastrowid
        except sqlite3.IntegrityError:
            print(f"[DataManager ERROR] La sesión '{session_name}' ya existe. Por favor, usa un nombre único.")
            return None
        except Exception as e:
            print(f"[DataManager ERROR] Error al crear sesión de escaneo: {e}")
            return None

    def update_scan_session(self, scan_id: int, status: str, summary: Optional[str] = None, end_time: Optional[str] = None, results_path: Optional[str] = None):
        """
        Actualiza el estado, resumen, hora de finalización y ruta de resultados de una sesión de escaneo.
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            updates = []
            params = []

            updates.append("status = ?")
            params.append(status)

            # Si end_time no se proporciona y el escaneo ha finalizado (completed/failed), establecerlo
            if end_time is None and status in ['completed', 'failed']:
                end_time = datetime.now().isoformat()
            
            if end_time is not None:
                updates.append("end_time = ?")
                params.append(end_time)

            if summary is not None:
                updates.append("summary = ?")
                params.append(summary)
            
            if results_path is not None:
                updates.append("results_path = ?")
                params.append(results_path)

            params.append(scan_id)

            query = f"UPDATE scans SET {', '.join(updates)} WHERE id = ?"
            cursor.execute(query, tuple(params))
            conn.commit()
            print(f"[DataManager] Sesión {scan_id} actualizada a estado: {status}")


    def add_host(self, scan_id: int, ip_address: str, hostname: Optional[str] = None, os_info: Optional[str] = None) -> Optional[int]:
        """
        Añade un host descubierto a la base de datos.
        Retorna el ID del host creado o None si falla.
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "INSERT INTO hosts (scan_id, ip_address, hostname, os_info) VALUES (?, ?, ?, ?)",
                    (scan_id, ip_address, hostname, os_info)
                )
                conn.commit()
                return cursor.lastrowid
        except Exception as e:
            print(f"[DataManager ERROR] Error al añadir host {ip_address}: {e}")
            return None

    def add_service(self, host_id: int, port: int, protocol: str, service_name: Optional[str] = None, version: Optional[str] = None, state: Optional[str] = None) -> Optional[int]:
        """
        Añade un servicio descubierto para un host.
        Retorna el ID del servicio creado o None si falla.
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "INSERT INTO services (host_id, port, protocol, service_name, version, state) VALUES (?, ?, ?, ?, ?, ?)",
                    (host_id, port, protocol, service_name, version, state)
                )
                conn.commit()
                return cursor.lastrowid
        except Exception as e:
            print(f"[DataManager ERROR] Error al añadir servicio {port}/{protocol} para host {host_id}: {e}")
            return None

    def add_finding(self, scan_id: int, host_id: int, type: str, title: str, description: str, severity: Optional[str] = None, recommendation: Optional[str] = None, details: Optional[Dict[str, Any]] = None, service_id: Optional[int] = None) -> Optional[int]:
        """
        Añade un hallazgo de seguridad.
        Retorna el ID del hallazgo creado o None si falla.
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                timestamp = datetime.now().isoformat()
                details_json = json.dumps(details) if details else None
                cursor.execute(
                    """INSERT INTO findings (scan_id, host_id, service_id, type, title, description, severity, recommendation, details, timestamp)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (scan_id, host_id, service_id, type, title, description, severity, recommendation, details_json, timestamp)
                )
                conn.commit()
                return cursor.lastrowid
        except Exception as e:
            print(f"[DataManager ERROR] Error al añadir hallazgo '{title}' para host {host_id}: {e}")
            return None

    def get_scan_details(self, scan_id: int) -> Optional[Dict[str, Any]]:
        """
        Obtiene los detalles de una sesión de escaneo por su ID.
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM scans WHERE id = ?", (scan_id,))
            scan = cursor.fetchone()
            return dict(scan) if scan else None

    def get_scan_details_by_name(self, session_name: str) -> Optional[Dict[str, Any]]:
        """
        Obtiene los detalles de una sesión de escaneo por su nombre.
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM scans WHERE session_name = ?", (session_name,))
            scan = cursor.fetchone()
            return dict(scan) if scan else None

    def get_hosts_for_scan(self, scan_id: int) -> List[Dict[str, Any]]:
        """
        Obtiene todos los hosts asociados a un ID de escaneo.
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM hosts WHERE scan_id = ?", (scan_id,))
            return [dict(row) for row in cursor.fetchall()]

    def get_services_for_host(self, host_id: int) -> List[Dict[str, Any]]:
        """
        Obtiene todos los servicios asociados a un ID de host.
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM services WHERE host_id = ?", (host_id,))
            return [dict(row) for row in cursor.fetchall()]

    def get_findings_for_scan(self, scan_id: int) -> List[Dict[str, Any]]:
        """
        Obtiene todos los hallazgos de seguridad asociados a un ID de escaneo.
        Los detalles (details) se cargan como JSON.
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM findings WHERE scan_id = ?", (scan_id,))
            findings = []
            for row in cursor.fetchall():
                finding = dict(row)
                if finding['details']:
                    try:
                        finding['details'] = json.loads(finding['details'])
                    except json.JSONDecodeError:
                        finding['details'] = {"error": "Invalid JSON in details field"}
                findings.append(finding)
            return findings

    def get_all_scan_sessions(self) -> List[Dict[str, Any]]:
        """
        Obtiene todas las sesiones de escaneo.
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM scans ORDER BY start_time DESC")
            return [dict(row) for row in cursor.fetchall()]

    def generate_timestamp(self) -> str:
        """Genera una cadena de tiempo formateada para nombres de sesión y archivos."""
        return datetime.now().strftime("%Y%m%d_%H%M%S")

    # Los métodos save_scan_output y get_scan_output_path han sido eliminados,
    # ya que la responsabilidad de la gestión de archivos de reporte recae en ReportGenerator.
    # Si alguna parte del código aún los llama, deberá ser actualizada.

    def get_host_by_ip_and_scan_id(self, ip_address: str, scan_id: int) -> Optional[Dict[str, Any]]:
        """
        Recupera un host por su dirección IP y ID de escaneo.
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM hosts WHERE ip_address = ? AND scan_id = ?", (ip_address, scan_id))
            host_record = cursor.fetchone()
            return dict(host_record) if host_record else None

    def get_host(self, host_id: int) -> Optional[Dict[str, Any]]:
        """
        Recupera un host por su ID de base de datos.
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM hosts WHERE id = ?", (host_id,))
            host_record = cursor.fetchone()
            return dict(host_record) if host_record else None

    def get_service_by_port_and_host_id(self, port: int, host_id: int) -> Optional[Dict[str, Any]]:
        """
        Recupera un servicio por su puerto y ID de host.
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM services WHERE port = ? AND host_id = ?", (port, host_id))
            service_record = cursor.fetchone()
            return dict(service_record) if service_record else None

    def get_service(self, service_id: int) -> Optional[Dict[str, Any]]:
        """
        Recupera un servicio por su ID de base de datos.
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM services WHERE id = ?", (service_id,))
            service_record = cursor.fetchone()
            return dict(service_record) if service_record else None

