import requests
import json
import logging
import re
from typing import Optional, Dict, Any, List

# Configuración básica de logging para este script
logger = logging.getLogger(__name__) # Usar el logger raíz o un logger específico para el módulo

class SimpleNVDAPIClient:
    """
    Cliente simplificado para interactuar con la API del NVD (National Vulnerability Database).
    """
    NVD_API_BASE_URL = "https://services.nvd.nist.gov/rest/json/cves/2.0"
    
    def search_cve(self, cpe_name: str, results_per_page: int = 5) -> Optional[Dict[str, Any]]:
        """
        Busca CVEs en el NVD por nombre CPE.
        :param cpe_name: El nombre CPE a buscar (ej. "cpe:2.3:a:openbsd:openssh:5.3p1:*:*:*:*:*:*:*").
        :param results_per_page: Número máximo de resultados a devolver.
        :return: Un diccionario con la respuesta JSON de la API del NVD, o None si hay un error.
        """
        params = {
            "cpeName": cpe_name,
            "resultsPerPage": results_per_page
        }
        logger.info(f"Realizando solicitud a NVD API con CPE: {cpe_name}")
        try:
            response = requests.get(self.NVD_API_BASE_URL, params=params, timeout=10)
            response.raise_for_status() # Lanza una excepción para códigos de estado HTTP de error (4xx o 5xx)
            return response.json()
        except requests.exceptions.HTTPError as http_err:
            logger.error(f"Error HTTP al buscar CVEs: {http_err} - Respuesta: {response.text}")
        except requests.exceptions.ConnectionError as conn_err:
            logger.error(f"Error de conexión al buscar CVEs: {conn_err}")
        except requests.exceptions.Timeout as timeout_err:
            logger.error(f"Tiempo de espera agotado al buscar CVEs: {timeout_err}")
        except requests.exceptions.RequestException as req_err:
            logger.error(f"Error inesperado al buscar CVEs: {req_err}")
        except json.JSONDecodeError as json_err:
            # Asegurarse de que 'response' esté definido antes de intentar acceder a 'response.text'
            response_text = response.text if 'response' in locals() else "No response text available."
            logger.error(f"Error al decodificar JSON de la respuesta del NVD: {json_err} - Texto: {response_text[:200]}...")
        return None

    def parse_and_summarize_cve_data(self, nvd_response: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Parsea la respuesta cruda de la API del NVD y extrae información clave de los CVEs.
        """
        summarized_cves = []
        if not nvd_response or not nvd_response.get('vulnerabilities'):
            return summarized_cves

        for vuln_entry in nvd_response['vulnerabilities']:
            cve_data = vuln_entry.get('cve')
            if not cve_data:
                continue

            cve_id = cve_data.get('id', 'N/A')
            
            # Obtener descripción en inglés si está disponible
            description = "No description available."
            for desc_entry in cve_data.get('descriptions', []):
                if desc_entry.get('lang') == 'en':
                    description = desc_entry.get('value', description)
                    break
            
            # Obtener métricas CVSS (preferir v3.1, luego v3.0, luego v2)
            cvss_score = 'N/A'
            cvss_severity = 'N/A'
            
            metrics = cve_data.get('metrics', {})
            if metrics.get('cvssMetricV31'):
                metric = metrics['cvssMetricV31'][0].get('cvssData', {})
                cvss_score = metric.get('baseScore', 'N/A')
                cvss_severity = metric.get('baseSeverity', 'N/A')
            elif metrics.get('cvssMetricV30'):
                metric = metrics['cvssMetricV30'][0].get('cvssData', {})
                cvss_score = metric.get('baseScore', 'N/A')
                cvss_severity = metric.get('baseSeverity', 'N/A')
            elif metrics.get('cvssMetricV2'):
                metric = metrics['cvssMetricV2'][0].get('cvssData', {})
                cvss_score = metric.get('baseScore', 'N/A')
                cvss_severity = metric.get('baseSeverity', 'N/A')

            # Obtener referencias (URLs)
            references = [ref.get('url') for ref in cve_data.get('references', []) if ref.get('url')]

            summarized_cves.append({
                'cve_id': cve_id,
                'description': description,
                'cvss_score': cvss_score,
                'cvss_severity': cvss_severity,
                'references': references
            })
        return summarized_cves

def construct_cpe_name_simplified(service_name: str, version: str, generic: bool = False) -> Optional[str]:
    """
    Construye un CPE (Common Platform Enumeration) simplificado a partir del nombre
    del servicio y su versión.
    """
    if not service_name or not version:
        return None

    # Paso 1: Limpiar texto entre paréntesis (ej. "(Ubuntu Linux; protocol 2.0)")
    version_without_parentheses = re.sub(r'\s*\(.*?\)\s*', '', version).strip()
    
    # Paso 2: Intentar extraer la parte de la versión numérica/alfanumérica principal
    # Busca un patrón como "X.Y", "X.Y.Z", "X.YpZ", "X.Y-beta", etc.
    # Esto intentará capturar la versión real después del nombre del servicio.
    # Modificación clave aquí: buscar el patrón de versión en cualquier parte de la cadena
    # y ser más específico con lo que se considera parte de la versión (números, puntos, letras, guiones, p/P)
    version_match = re.search(r'(\d+(\.\d+)*([a-zA-Z]\d+)?(?:[_\-\.]\d+)*)', version_without_parentheses)
    
    normalized_version = ""
    if version_match:
        extracted_version = version_match.group(1)
        # Limpiar aún más si hay sufijos no deseados después de la parte principal de la versión
        # Por ejemplo, de "5.3p1 Debian" queremos "5.3p1" o "5.3"
        # Usamos re.split para dividir por caracteres comunes de separación de versión que no son parte del número
        normalized_version = re.split(r'[\s\-]', extracted_version)[0] # Dividir por espacio o guion
        # Si la versión aún contiene 'p' o 'P' y no es parte de un número (ej. 5.3p1), mantenerlo.
        # Si es '5.3p1', la primera split por espacio o guion la dejará intacta.
        # Si es '5.3-beta', la dejará como '5.3'.
    else:
        # Fallback si no se encuentra un patrón de versión claro
        # Intentar extraer solo la primera secuencia de números y puntos
        num_match = re.search(r'\d+(\.\d+)*', version_without_parentheses)
        if num_match:
            normalized_version = num_match.group(0)
        else:
            normalized_version = "" # No se pudo extraer una versión numérica

    if not normalized_version:
        logger.warning(f"No se pudo normalizar la versión para CPE: '{version}'. Retornando None.")
        return None

    if generic:
        # Para una versión genérica, solo tomamos los dos primeros componentes (ej. 5.3 de 5.3.1p1)
        parts = normalized_version.split('.')
        if len(parts) >= 2:
            normalized_version = ".".join(parts[:2])
        # else: if only one part, use it as is (e.g., "1")
    
    normalized_service = service_name.lower().replace(' ', '_').replace('/', '_').replace('-', '_')
    
    vendor_map = {
        "openssh": "openbsd", 
        "apache httpd": "apache",
        "nginx": "nginx",
        "mysql": "mysql",
        "postgresql": "postgresql",
        "bind": "isc",
        "microsoft terminal services": "microsoft",
        "ms-wbt-server": "microsoft",
        "ssh": "openbsd" # Añadido un mapeo directo para el servicio 'ssh' al vendor 'openbsd'
    }
    vendor = vendor_map.get(normalized_service, normalized_service)
    product = normalized_service

    # Ajustes específicos de producto para CPEs comunes
    if normalized_service == "apache_httpd":
        product = "http_server"
    elif normalized_service == "openssh" or normalized_service == "ssh": # Asegurarse de que "ssh" también mapee a "openssh" como producto
        product = "openssh"
    elif normalized_service == "ms-wbt-server":
        product = "windows_server"

    cpe = f"cpe:2.3:a:{vendor}:{product}:{normalized_version}:*:*:*:*:*:*:*"
    logger.info(f"CPE construido: {cpe} (Servicio: '{service_name}', Versión original: '{version}', Versión limpia final: '{normalized_version}', Genérico: {generic})")
    return cpe
