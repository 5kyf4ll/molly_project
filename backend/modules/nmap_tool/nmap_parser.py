# src/modules/nmap_tool/nmap_parser.py
import re
from typing import Dict, Any, List

class NmapParser:
    """
    Parsea la salida de texto de Nmap en una estructura de datos Python.
    """
    def __init__(self):
        print("[NmapParser] Inicializado.")

    def parse_nmap_output(self, nmap_output: str) -> Dict[str, Any]:
        """
        Parsea la salida de texto de Nmap para extraer información de hosts, puertos y servicios.
        Este parser es básico y puede necesitar ser expandido para cubrir todos los escenarios
        posibles de salida de Nmap (ej. XML output para mayor robustez).

        Args:
            nmap_output (str): La salida completa de Nmap como una cadena de texto.

        Returns:
            Dict[str, Any]: Un diccionario con la estructura:
                            {
                                "hosts": {
                                    "IP_ADDRESS_1": {
                                        "hostname": "optional_hostname",
                                        "os_info": "optional_os_details",
                                        "ports": [
                                            {"port": int, "protocol": str, "state": str, "service_name": str, "version": str},
                                            ...
                                        ]
                                    },
                                    "IP_ADDRESS_2": {...}
                                }
                            }
        """
        hosts_data: Dict[str, Any] = {"hosts": {}}
        current_ip = None
        current_host_entry = None

        # Patrones de RegEx para diferentes secciones de la salida de Nmap
        host_pattern = re.compile(r"Nmap scan report for ([\d.]+)(?: \(([\w.-]+)\))?")
        port_pattern = re.compile(r"(\d+)/(\w+)\s+([a-zA-Z]+)\s+([\w.-]+)?\s*(.*)?") # Updated to handle optional service/version
        os_details_pattern = re.compile(r"OS details: (.*)")
        # Para el caso de que el hostname sea el mismo que la IP, Nmap a veces no lo repite en ()
        # "Nmap scan report for 192.168.1.1"

        lines = nmap_output.splitlines()
        for line in lines:
            line = line.strip()

            # Busca el inicio de un nuevo host
            host_match = host_pattern.search(line)
            if host_match:
                current_ip = host_match.group(1)
                hostname = host_match.group(2) if host_match.group(2) else current_ip # Si no hay hostname, usa la IP
                hosts_data["hosts"][current_ip] = {
                    "hostname": hostname,
                    "os_info": None,
                    "ports": []
                }
                current_host_entry = hosts_data["hosts"][current_ip]
                continue

            # Si estamos procesando un host, busca sus puertos y OS
            if current_host_entry:
                # Busca información de puertos
                port_match = port_pattern.match(line)
                if port_match:
                    try:
                        port = int(port_match.group(1))
                        protocol = port_match.group(2)
                        state = port_match.group(3)
                        service_name = port_match.group(4) if port_match.group(4) else "unknown"
                        version = port_match.group(5).strip() if port_match.group(5) else "N/A"
                        
                        current_host_entry["ports"].append({
                            "port": port,
                            "protocol": protocol,
                            "state": state,
                            "service_name": service_name,
                            "version": version
                        })
                    except ValueError:
                        # Ignorar líneas que parecen puertos pero no se parsean correctamente (ej. headers)
                        pass
                    continue

                # Busca información de OS
                os_match = os_details_pattern.search(line)
                if os_match:
                    current_host_entry["os_info"] = os_match.group(1).strip()
                    continue
        
        return hosts_data

# Ejemplo de uso (para pruebas)
if __name__ == '__main__':
    parser = NmapParser()

    sample_nmap_output = """
# Nmap 7.80 scan initiated Fri Jul  7 14:00:00 2025 as: nmap -sS -sV -O -p- --max-rate 500 --open 192.168.1.0/24
Nmap scan report for 192.168.1.1
Host is up (0.000040s latency).
Not shown: 997 closed ports
PORT     STATE SERVICE VERSION
22/tcp   open  ssh     OpenSSH 8.9 (Ubuntu)
80/tcp   open  http    Apache httpd 2.4.52 ((Ubuntu))
443/tcp  open  https   Apache httpd 2.4.52 ((Ubuntu))
OS details: Linux 4.15 - 5.10

Nmap scan report for 192.168.1.10 (kali-molly.local)
Host is up (0.000050s latency).
Not shown: 998 closed ports
PORT     STATE SERVICE VERSION
21/tcp   open  ftp     vsftpd 3.0.3
22/tcp   open  ssh     OpenSSH 7.6p1 Ubuntu 4 (Ubuntu Linux; protocol 2.0)
OS details: Linux 4.15 - 5.10

Nmap scan report for 192.168.1.100
Host is up (0.000060s latency).
All 1000 scanned ports on 192.168.1.100 are closed

Nmap done: 3 IP addresses (2 hosts up) scanned in 1.50 seconds
"""

    print("--- Probando NmapParser ---")
    parsed_data = parser.parse_nmap_output(sample_nmap_output)
    import json # Para imprimir el resultado formateado
    print(json.dumps(parsed_data, indent=2))

    # Prueba con un host sin servicios (debería aparecer igual)
    sample_nmap_output_no_services = """
Nmap scan report for 192.168.1.100
Host is up (0.000060s latency).
All 1000 scanned ports on 192.168.1.100 are closed

Nmap done: 1 IP address (1 host up) scanned in 0.50 seconds
"""
    print("\n--- Probando NmapParser (Host sin servicios) ---")
    parsed_data_no_services = parser.parse_nmap_output(sample_nmap_output_no_services)
    print(json.dumps(parsed_data_no_services, indent=2))