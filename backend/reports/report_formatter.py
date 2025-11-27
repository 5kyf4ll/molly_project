# src/reports/report_formatter.py
from datetime import datetime
from typing import List, Dict, Any, Optional
import json # ¡Esta es la línea que faltaba!

class ReportFormatter:
    """
    Formatea los datos crudos de escaneos y hallazgos en un formato legible
    (ej. Markdown) para la generación de informes.
    """
    def __init__(self):
        print("[ReportFormatter] Inicializado.")

    def format_network_scan_summary(self, scan_info: Dict[str, Any], hosts: List[Dict[str, Any]], services_by_host: Dict[str, List[Dict[str, Any]]]) -> str:
        """
        Formatea un resumen general de un escaneo de red.
        Muestra los hosts descubiertos y sus servicios abiertos.
        """
        report_content = f"# Resumen de Escaneo de Red - Sesión: {scan_info.get('session_name', 'N/A')}\n\n"
        report_content += f"**Tipo de Escaneo:** {scan_info.get('scan_type', 'N/A')}\n"
        report_content += f"**Objetivo:** {scan_info.get('target', 'N/A')}\n"
        report_content += f"**Fecha de Inicio:** {scan_info.get('start_time', 'N/A')}\n"
        report_content += f"**Estado:** {scan_info.get('status', 'N/A')}\n"
        if scan_info.get('end_time'):
            report_content += f"**Fecha de Finalización:** {scan_info.get('end_time', 'N/A')}\n"
        if scan_info.get('summary'):
            report_content += f"**Resumen:** {scan_info.get('summary', 'N/A')}\n"
        report_content += "\n---\n\n"

        if not hosts:
            report_content += "No se encontraron hosts activos en este escaneo.\n"
            return report_content

        report_content += "## Hosts Descubiertos y Servicios Abiertos\n\n"
        for host in hosts:
            ip = host.get('ip_address', 'N/A')
            hostname = host.get('hostname', 'N/A')
            os_info = host.get('os_info', 'N/A')
            
            report_content += f"### Host: {ip}"
            if hostname != 'N/A':
                report_content += f" ({hostname})"
            report_content += "\n"
            
            if os_info != 'N/A':
                report_content += f"**SO:** {os_info}\n"
            
            services = services_by_host.get(ip, [])
            if services:
                report_content += "**Servicios Abiertos:**\n"
                for service in services:
                    report_content += (
                        f"- Puerto: {service.get('port')}/{service.get('protocol')} "
                        f"({service.get('service_name')} v{service.get('version', 'N/A')}) "
                        f"Estado: {service.get('state')}\n"
                    )
            else:
                report_content += "  No se encontraron servicios abiertos en este host.\n"
            report_content += "\n"
        
        return report_content

    def format_detailed_host_report(self, host_info: Dict[str, Any], services: List[Dict[str, Any]], findings: List[Dict[str, Any]]) -> str:
        """
        Formatea un informe detallado para un host específico, incluyendo servicios y hallazgos.
        """
        ip = host_info.get('ip_address', 'N/A')
        hostname = host_info.get('hostname', 'N/A')
        os_info = host_info.get('os_info', 'N/A')

        report_content = f"# Informe Detallado del Host: {ip}"
        if hostname != 'N/A':
            report_content += f" ({hostname})"
        report_content += "\n\n"
        
        report_content += f"**Fecha del Informe:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        report_content += f"**Dirección IP:** {ip}\n"
        if hostname != 'N/A':
            report_content += f"**Nombre de Host:** {hostname}\n"
        if os_info != 'N/A':
            report_content += f"**Sistema Operativo:** {os_info}\n"
        report_content += "\n---\n\n"

        # Sección de Servicios
        report_content += "## Servicios y Puertos Abiertos\n\n"
        if services:
            for service in services:
                report_content += (
                    f"### Puerto: {service.get('port')}/{service.get('protocol')}\n"
                    f"- **Servicio:** {service.get('service_name', 'N/A')} (Versión: {service.get('version', 'N/A')})\n"
                    f"- **Estado:** {service.get('state', 'N/A')}\n"
                )
                report_content += "\n"
        else:
            report_content += "No se encontraron servicios abiertos para este host en el escaneo detallado.\n\n"
        
        report_content += "---\n\n"

        # Sección de Hallazgos
        report_content += "## Hallazgos de Seguridad\n\n"
        if findings:
            severity_order = {'Critical': 1, 'High': 2, 'Medium': 3, 'Low': 4, 'Informational': 5}
            sorted_findings = sorted(findings, key=lambda x: severity_order.get(x.get('severity', 'Informational'), 5))

            for finding in sorted_findings:
                report_content += f"### {finding.get('title', 'Hallazgo sin título')} ({finding.get('severity', 'Informational')})\n"
                report_content += f"**Tipo:** {finding.get('type', 'N/A')}\n"
                
                if finding.get('service_id'):
                    associated_service = next((s for s in services if s['id'] == finding['service_id']), None)
                    if associated_service:
                        report_content += f"**Servicio Asociado:** {associated_service.get('service_name', 'N/A')} en puerto {associated_service.get('port')}/{associated_service.get('protocol')}\n"
                
                report_content += f"**Descripción:** {finding.get('description', 'N/A')}\n"
                if finding.get('recommendation'):
                    report_content += f"**Recomendación:** {finding.get('recommendation', 'N/A')}\n"
                if finding.get('details'):
                    # Convertir el diccionario 'details' a una cadena JSON formateada
                    report_content += f"**Detalles Adicionales:**\n```json\n{json.dumps(finding['details'], indent=2)}\n```\n"
                report_content += "\n"
        else:
            report_content += "No se encontraron hallazgos de seguridad para este host.\n\n"
            
        report_content += "\n---\n"
        report_content += "Fin del Informe. Generado por Molly Security AI."
        
        return report_content