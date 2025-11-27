# reports/report_generator.py
import os
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.units import inch
from reportlab.lib.colors import black, red, green, blue, darkred, darkgreen, darkblue, orange, gray
import re # Para procesar Markdown básico
from datetime import datetime
from typing import List, Dict, Any, Optional
import logging # Añadimos logging para mejor trazabilidad

# Importación relativa para el entorno de la aplicación
from .report_formatter import ReportFormatter 

logger = logging.getLogger(__name__)

class ReportGenerator:
    # EL CAMBIO CRUCIAL ESTÁ AQUÍ: 
    # Cambiamos 'output_dir' por 'report_path_root' para que coincida con el código que llama.
    def __init__(self, report_path_root: str = 'scans', report_formatter: ReportFormatter = None):
        # La variable interna sigue siendo 'self.output_dir'
        self.output_dir = report_path_root 
        
        # Asegurarse de que el directorio base 'scans' exista
        os.makedirs(self.output_dir, exist_ok=True)
        self.styles = getSampleStyleSheet()
        self._setup_styles()

        # Almacena la instancia de ReportFormatter
        if report_formatter is None:
            self.report_formatter = ReportFormatter()
        else:
            self.report_formatter = report_formatter

        logger.info(f"[ReportGenerator] Inicializado. Directorio de salida: {self.output_dir}")

    def _setup_styles(self):
        """
        Configura estilos personalizados para el informe.
        """
        self.styles.add(ParagraphStyle(name='TitleStyle', fontSize=24, leading=28, alignment=TA_LEFT, spaceAfter=20, fontName='Helvetica-Bold'))
        self.styles.add(ParagraphStyle(name='H1Style', fontSize=20, leading=24, alignment=TA_LEFT, spaceAfter=14, fontName='Helvetica-Bold'))
        self.styles.add(ParagraphStyle(name='H2Style', fontSize=16, leading=18, alignment=TA_LEFT, spaceAfter=12, fontName='Helvetica-Bold'))
        self.styles.add(ParagraphStyle(name='H3Style', fontSize=14, leading=16, alignment=TA_LEFT, spaceAfter=10, fontName='Helvetica-Bold'))
        
        self.styles.add(ParagraphStyle(name='NormalStyle', fontSize=10, leading=12, alignment=TA_LEFT, spaceAfter=6, fontName='Helvetica'))
        
        self.styles.add(ParagraphStyle(name='BoldStyle', fontSize=10, leading=12, alignment=TA_LEFT, spaceAfter=6, fontName='Helvetica-Bold'))

        self.styles.add(ParagraphStyle(name='ListItemStyle', fontSize=10, leading=12, alignment=TA_LEFT, spaceAfter=4, leftIndent=20, fontName='Helvetica'))

        self.styles.add(ParagraphStyle(name='CodeBlockStyle', 
                                         fontSize=9, leading=11, fontName='Courier', 
                                         backColor=gray, textColor=black, 
                                         borderPadding=5, borderWidth=0.5, borderColor=gray,
                                         leftIndent=20, rightIndent=20, spaceBefore=8, spaceAfter=8))
        
        self.styles.add(ParagraphStyle(name='CriticalSeverity', fontSize=10, leading=12, textColor=darkred, fontName='Helvetica-Bold'))
        self.styles.add(ParagraphStyle(name='HighSeverity', fontSize=10, leading=12, textColor=red, fontName='Helvetica-Bold'))
        self.styles.add(ParagraphStyle(name='MediumSeverity', fontSize=10, leading=12, textColor=orange, fontName='Helvetica-Bold'))
        self.styles.add(ParagraphStyle(name='LowSeverity', fontSize=10, leading=12, textColor=blue, fontName='Helvetica-Bold'))
        self.styles.add(ParagraphStyle(name='InformationalSeverity', fontSize=10, leading=12, textColor=darkgreen, fontName='Helvetica-Bold'))


    def _parse_markdown(self, markdown_content: str) -> List[Any]:
        """
        Parsea un contenido Markdown básico y lo convierte en elementos de ReportLab Story.
        Soporta: # H1, ## H2, ### H3, **bold**, - list items, ```code blocks```, --- separator.
        """
        story = []
        lines = markdown_content.split('\n')
        in_code_block = False
        current_code_block = []

        for line in lines:
            stripped_line = line.strip()

            if stripped_line.startswith('```'):
                if in_code_block:
                    story.append(Paragraph("\n".join(current_code_block), self.styles['CodeBlockStyle']))
                    current_code_block = []
                    in_code_block = False
                else:
                    in_code_block = True
                continue

            if in_code_block:
                current_code_block.append(line)
                continue

            if stripped_line == '---':
                story.append(Spacer(1, 0.2 * inch))
                continue

            if stripped_line.startswith('# '):
                # Utiliza el estilo TitleStyle para el encabezado principal del Markdown
                story.append(Paragraph(stripped_line[2:], self.styles['TitleStyle']))
            elif stripped_line.startswith('## '):
                # H1
                story.append(Paragraph(stripped_line[3:], self.styles['H1Style']))
            elif stripped_line.startswith('### '):
                # H2
                story.append(Paragraph(stripped_line[4:], self.styles['H2Style']))
            elif stripped_line.startswith('#### '):
                # H3
                story.append(Paragraph(stripped_line[5:], self.styles['H3Style']))
            elif stripped_line.startswith('- '):
                text_content = self._apply_inline_styles(stripped_line[2:])
                # Añade un bullet point para la lista
                story.append(Paragraph(f"• {text_content}", self.styles['ListItemStyle']))
            else:
                text_content = self._apply_inline_styles(stripped_line)
                if text_content:
                    story.append(Paragraph(text_content, self.styles['NormalStyle']))
        
        # Si el bloque de código termina abruptamente al final del archivo
        if in_code_block and current_code_block:
            story.append(Paragraph("\n".join(current_code_block), self.styles['CodeBlockStyle']))

        return story

    def _apply_inline_styles(self, text: str) -> str:
        """
        Aplica estilos inline como negritas (**texto**) y colores de severidad
        al texto Markdown, convirtiéndolo a etiquetas XML de ReportLab.
        """
        def replace_bold(match):
            return f'<font name="Helvetica-Bold">{match.group(1)}</font>'
        
        # Negritas Markdown (**) a etiqueta <font> de ReportLab
        text = re.sub(r'\*\*(.*?)\*\*', replace_bold, text)
        
        # Reemplazo de severidades por tags de color y negrita
        text = text.replace('(Critical)', '<font name="Helvetica-Bold" color="darkred">(Critical)</font>')
        text = text.replace('(High)', '<font name="Helvetica-Bold" color="red">(High)</font>')
        text = text.replace('(Medium)', '<font name="Helvetica-Bold" color="orange">(Medium)</font>')
        text = text.replace('(Low)', '<font name="Helvetica-Bold" color="blue">(Low)</font>')
        text = text.replace('(Informational)', '<font name="Helvetica-Bold" color="darkgreen">(Informational)</font>')

        return text


    def generate_pdf_report(self, 
                            report_content_markdown: str, 
                            filename: str, 
                            scan_session_name: str,
                            host_ip: Optional[str] = None) -> str:
        """
        Genera un informe PDF a partir del contenido Markdown.
        La ruta de salida es: self.output_dir / scan_session_name / [host_ip_dir] / filename
        """
        # Crear el directorio específico de la sesión dentro de self.output_dir ('scans')
        session_dir = os.path.join(self.output_dir, scan_session_name)
        os.makedirs(session_dir, exist_ok=True)

        # Determinar la ruta completa del archivo PDF
        if host_ip:
            # Si es un informe de host, crear un subdirectorio para el host
            host_dir = os.path.join(session_dir, f"Escaneo_IA_{host_ip.replace('.', '_')}") 
            os.makedirs(host_dir, exist_ok=True)
            full_path = os.path.join(host_dir, filename)
        else:
            # Si es un informe de resumen de escaneo, va directamente en el directorio de la sesión
            full_path = os.path.join(session_dir, filename)
        
        doc = SimpleDocTemplate(full_path, pagesize=letter)
        story = []

        # Contenido de la primera página (Cabecera)
        story.append(Paragraph(f"Informe de Seguridad Generado por Molly AI", self.styles['TitleStyle']))
        story.append(Spacer(1, 0.5 * inch))
        story.append(Paragraph(f"Sesión: {scan_session_name}", self.styles['H1Style']))
        if host_ip:
            story.append(Paragraph(f"Host Analizado: {host_ip}", self.styles['H2Style']))
        story.append(Spacer(1, 0.2 * inch))
        story.append(Paragraph(f"Fecha de Generación: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", self.styles['NormalStyle']))
        story.append(PageBreak()) # Salto de página antes del contenido del informe

        # Añadir el contenido parseado del Markdown
        story.extend(self._parse_markdown(report_content_markdown))

        try:
            doc.build(story)
            logger.info(f"[ReportGenerator] Informe PDF generado exitosamente: {full_path}")
            return full_path
        except Exception as e:
            logger.error(f"[ReportGenerator ERROR] Error al generar el PDF '{full_path}': {e}")
            return None

# Ejemplo de uso (para pruebas rápidas)
if __name__ == '__main__':
    import sys
    import logging
    # Configurar el logging básico para ver la salida del logger.info/error
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    # Ajustar el path para la ejecución directa de módulos si es necesario (asumo la estructura reports/report_formatter.py)
    # Aquí es crucial asegurarse de que ReportFormatter es importable.
    try:
        from report_formatter import ReportFormatter
    except ImportError:
        # Fallback para el entorno de prueba, ajusta según la estructura real de tu proyecto
        sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
        from reports.report_formatter import ReportFormatter
    
    formatter = ReportFormatter()
    # Ahora llamará al constructor con el nombre de argumento correcto si se pasa
    generator = ReportGenerator(report_path_root='scans_test') 

    sample_scan_info = {
        "session_name": "Escaneo_IA_192_168_1_38_20250718_182516", 
        "scan_type": "Network Discovery",
        "target": "192.168.1.0/24",
        "start_time": "2025-07-07T10:00:00",
        "status": "completed",
        "summary": "Escaneo inicial de red completado. Se encontraron 3 hosts activos."
    }
    sample_hosts = [
        {"id": 1, "scan_id": 1, "ip_address": "192.168.1.1", "hostname": "router.local", "os_info": "Linux"},
        {"id": 2, "scan_id": 1, "ip_address": "192.168.1.10", "hostname": "kali-molly", "os_info": "Linux"},
        {"id": 3, "scan_id": 1, "ip_address": "192.168.1.20", "hostname": "win-server", "os_info": "Windows"}
    ]
    sample_services_by_host = {
        "192.168.1.1": [
            {"id": 101, "host_id": 1, "port": 80, "protocol": "tcp", "service_name": "http", "version": "nginx", "state": "open"},
            {"id": 102, "host_id": 1, "port": 443, "protocol": "tcp", "service_name": "https", "version": "nginx", "state": "open"}
        ],
        "192.168.1.10": [
            {"id": 201, "host_id": 2, "port": 22, "protocol": "tcp", "service_name": "ssh", "version": "OpenSSH 8.9", "state": "open"},
            {"id": 202, "host_id": 2, "port": 21, "protocol": "tcp", "service_name": "ftp", "version": "vsftpd 3.0.3", "state": "open"}
        ],
        "192.168.1.20": [
            {"id": 301, "host_id": 3, "port": 3389, "protocol": "tcp", "service_name": "ms-wbt-server", "version": "Microsoft Terminal Services", "state": "open"}
        ]
    }

    network_markdown = formatter.format_network_scan_summary(sample_scan_info, sample_hosts, sample_services_by_host)
    logger.info("\n--- Generando Resumen de Red PDF ---")
    network_pdf_path = generator.generate_pdf_report(
        network_markdown, 
        "network_summary_report.pdf", 
        sample_scan_info['session_name']
    )
    logger.info(f"Resumen de Red PDF en: {network_pdf_path}")

    sample_host_info = {"id": 2, "scan_id": 1, "ip_address": "192.168.1.10", "hostname": "kali-molly", "os_info": "Linux"}
    sample_services_for_host = [
        {"id": 201, "host_id": 2, "port": 22, "protocol": "tcp", "service_name": "ssh", "version": "OpenSSH 8.9", "state": "open"},
        {"id": 202, "host_id": 2, "port": 21, "protocol": "tcp", "service_name": "ftp", "version": "vsftpd 3.0.3", "state": "open"}
    ]
    sample_findings_for_host = [
        {
            "id": 1, "scan_id": 1, "host_id": 2, "service_id": 202,
            "type": "vulnerability", "title": "FTP Acceso Anónimo Permitido",
            "description": "El servidor FTP en el puerto 21 permite el acceso anónimo, lo que podría exponer información sensible.",
            "severity": "High", "recommendation": "Deshabilitar el acceso FTP anónimo.",
            "timestamp": datetime.now().isoformat(),
            "details": {"accessed_files": ["README.txt", "users.txt"]}
        },
        {
            "id": 2, "scan_id": 1, "host_id": 2, "service_id": 201,
            "type": "info_leak", "title": "Banner SSH Enumera Versión",
            "description": "El banner SSH revela la versión exacta del servidor (OpenSSH 8.9), lo que facilita la búsqueda de exploits específicos.",
            "severity": "Low", "recommendation": "Configurar el servidor SSH para ocultar o generalizar el banner.",
            "timestamp": datetime.now().isoformat(),
            "details": {"banner": "SSH-2.0-OpenSSH_8.9p1 Ubuntu-3ubuntu0.6"}
        },
        {
            "id": 3, "scan_id": 1, "host_id": 2, "service_id": None,
            "type": "misconfiguration", "title": "Firewall Deshabilitado",
            "description": "El firewall UFW no está activo en el sistema, dejando los puertos expuestos.",
            "severity": "Medium", "recommendation": "Activar y configurar el firewall UFW para solo permitir el tráfico necesario.",
            "timestamp": datetime.now().isoformat(),
            "details": {"ufw_status": "inactive"}
        }
    ]

    detailed_host_markdown = formatter.format_detailed_host_report(sample_host_info, sample_services_for_host, sample_findings_for_host)
    logger.info("\n--- Generando Informe Detallado de Host PDF ---")
    detailed_pdf_path = generator.generate_pdf_report(
        detailed_host_markdown, 
        "detailed_host_report.pdf", 
        sample_scan_info['session_name'],
        sample_host_info['ip_address']
    )
    logger.info(f"Informe Detallado de Host PDF en: {detailed_pdf_path}")