# src/core/session_manager.py
import os
from datetime import datetime
from typing import Optional, List, Dict, Any
import sqlite3
from .data_manager import DataManager

class SessionManager:
    """
    Gestiona el estado de la sesión de trabajo actual de Molly en memoria.
    Define el contexto operativo (qué escaneo se está realizando, qué host se analiza, etc.).
    """
    def __init__(self, data_manager: DataManager):
        self.data_manager = data_manager # Almacena la instancia de DataManager
        self.active_session_id = None
        self.active_session_data = {}
        print("[SessionManager] Inicializado. Sin sesión activa.")
        self.active_session_id = None
        self.active_session_data = {}
        print("[SessionManager] Inicializado. Sin sesión activa.")
        self.current_scan_id: Optional[int] = None
        self.current_scan_type: Optional[str] = None
        self.current_target: Optional[str] = None
        self.current_session_name: Optional[str] = None
        
        self.current_host_id: Optional[int] = None
        self.current_host_ip: Optional[str] = None

        self.discovered_hosts_in_scan: List[Dict[str, Any]] = [] # Lista de hosts {ip, host_id} para la sesión actual
        self.discovered_services_for_host: Dict[str, List[Dict[str, Any]]] = {} # Servicios {port, name, service_id} por IP

        print("[SessionManager] Inicializado. Sin sesión activa.")

    def start_new_scan_session(self, scan_id: int, session_name: str, scan_type: str, target: str):
        """
        Inicia una nueva sesión de escaneo, configurando el contexto actual.
        """
        self.current_scan_id = scan_id
        self.current_session_name = session_name
        self.current_scan_type = scan_type
        self.current_target = target
        
        # Resetear datos específicos de host/servicio para la nueva sesión
        self.current_host_id = None
        self.current_host_ip = None
        self.discovered_hosts_in_scan = []
        self.discovered_services_for_host = {}
        
        print(f"[SessionManager] Nueva sesión iniciada: ID={scan_id}, Tipo={scan_type}, Objetivo={target}")

    def set_current_host_context(self, host_id: int, ip_address: str):
        """
        Establece el host actual que está siendo analizado en detalle.
        """
        self.current_host_id = host_id
        self.current_host_ip = ip_address
        print(f"[SessionManager] Contexto de host actual establecido: ID={host_id}, IP={ip_address}")

    def add_discovered_host(self, ip_address: str, host_db_id: int):
        """
        Añade un host descubierto a la lista de la sesión actual.
        """
        host_info = {"ip_address": ip_address, "host_db_id": host_db_id}
        if host_info not in self.discovered_hosts_in_scan:
            self.discovered_hosts_in_scan.append(host_info)
            print(f"[SessionManager] Host descubierto y añadido a la sesión: {ip_address} (DB ID: {host_db_id})")

    def add_discovered_service_for_host(self, ip_address: str, port: int, service_name: str, service_db_id: int):
        """
        Añade un servicio descubierto para un host específico.
        """
        if ip_address not in self.discovered_services_for_host:
            self.discovered_services_for_host[ip_address] = []
        
        service_info = {"port": port, "service_name": service_name, "service_db_id": service_db_id}
        if service_info not in self.discovered_services_for_host[ip_address]:
            self.discovered_services_for_host[ip_address].append(service_info)
            print(f"[SessionManager] Servicio {service_name}:{port} añadido para {ip_address} (DB ID: {service_db_id})")

    def clear_session_context(self):
        """
        Limpia el contexto de la sesión actual.
        """
        self.current_scan_id = None
        self.current_scan_type = None
        self.current_target = None
        self.current_session_name = None
        self.current_host_id = None
        self.current_host_ip = None
        self.discovered_hosts_in_scan = []
        self.discovered_services_for_host = {}
        print("[SessionManager] Contexto de sesión limpiado.")

    def get_current_scan_info(self) -> Dict[str, Any]:
        """
        Retorna la información de la sesión de escaneo actual.
        """
        return {
            "scan_id": self.current_scan_id,
            "session_name": self.current_session_name,
            "scan_type": self.current_scan_type,
            "target": self.current_target
        }

    def get_current_host_info(self) -> Dict[str, Any]:
        """
        Retorna la información del host que se está analizando actualmente.
        """
        return {
            "host_id": self.current_host_id,
            "ip_address": self.current_host_ip
        }

    def get_discovered_hosts_in_current_scan(self) -> List[Dict[str, Any]]:
        """
        Retorna la lista de hosts descubiertos en la sesión actual.
        """
        return self.discovered_hosts_in_scan

    def get_discovered_services_for_host(self, ip_address: str) -> List[Dict[str, Any]]:
        """
        Retorna la lista de servicios descubiertos para un host específico.
        """
        return self.discovered_services_for_host.get(ip_address, [])

    def is_session_active(self) -> bool:
        """
        Verifica si hay una sesión de escaneo activa.
        """
        return self.current_scan_id is not None