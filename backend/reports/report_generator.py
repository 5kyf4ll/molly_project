# reports/report_generator.py
import os
import re
import logging
from datetime import datetime
from typing import List, Any, Optional

from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.units import inch
from reportlab.lib.colors import black, red, green, blue, darkred, darkgreen, orange, gray

# Importacion relativa para el entorno de paquetes (cuando se ejecuta con -m desde backend/)
from .report_formatter import ReportFormatter

logger = logging.getLogger(__name__)

class ReportGenerator:
    def __init__(self, report_path_root: str = 'instance/scans', report_formatter: ReportFormatter = None):
        self.output_dir = report_path_root
        os.makedirs(self.output_dir, exist_ok=True)

        self.styles = getSampleStyleSheet()
        self._setup_styles()

        if report_formatter is None:
            self.report_formatter = ReportFormatter()
        else:
            self.report_formatter = report_formatter

        logger.info(f"[ReportGenerator] Inicializado. Directorio de salida: {self.output_dir}")

    def _setup_styles(self):
        self.styles.add(ParagraphStyle(
            name='TitleStyle', fontSize=24, leading=28, alignment=TA_LEFT,
            spaceAfter=20, fontName='Helvetica-Bold'
        ))
        self.styles.add(ParagraphStyle(
            name='H1Style', fontSize=20, leading=24, alignment=TA_LEFT,
            spaceAfter=14, fontName='Helvetica-Bold'
        ))
        self.styles.add(ParagraphStyle(
            name='H2Style', fontSize=16, leading=18, alignment=TA_LEFT,
            spaceAfter=12, fontName='Helvetica-Bold'
        ))
        self.styles.add(ParagraphStyle(
            name='H3Style', fontSize=14, leading=16, alignment=TA_LEFT,
            spaceAfter=10, fontName='Helvetica-Bold'
        ))

        self.styles.add(ParagraphStyle(
            name='NormalStyle', fontSize=10, leading=12, alignment=TA_LEFT,
            spaceAfter=6, fontName='Helvetica'
        ))

        self.styles.add(ParagraphStyle(
            name='ListItemStyle', fontSize=10, leading=12, alignment=TA_LEFT,
            spaceAfter=4, leftIndent=20, fontName='Helvetica'
        ))

        self.styles.add(ParagraphStyle(
            name='CodeBlockStyle',
            fontSize=9, leading=11, fontName='Courier',
            backColor=gray, textColor=black,
            borderPadding=5, borderWidth=0.5, borderColor=gray,
            leftIndent=20, rightIndent=20, spaceBefore=8, spaceAfter=8
        ))

        self.styles.add(ParagraphStyle(name='CriticalSeverity', fontSize=10, leading=12, textColor=darkred))
        self.styles.add(ParagraphStyle(name='HighSeverity', fontSize=10, leading=12, textColor=red))
        self.styles.add(ParagraphStyle(name='MediumSeverity', fontSize=10, leading=12, textColor=orange))
        self.styles.add(ParagraphStyle(name='LowSeverity', fontSize=10, leading=12, textColor=blue))
        self.styles.add(ParagraphStyle(name='InformationalSeverity', fontSize=10, leading=12, textColor=darkgreen))

    def _parse_markdown(self, markdown_content: str) -> List[Any]:
        story = []
        lines = markdown_content.split('\n')
        in_code_block = False
        current_code_block: List[str] = []

        for line in lines:
            stripped = line.strip()

            if stripped.startswith('```'):
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

            if stripped == '---':
                story.append(Spacer(1, 0.2 * inch))
                continue

            if stripped.startswith('# '):
                story.append(Paragraph(stripped[2:], self.styles['TitleStyle']))
            elif stripped.startswith('## '):
                story.append(Paragraph(stripped[3:], self.styles['H1Style']))
            elif stripped.startswith('### '):
                story.append(Paragraph(stripped[4:], self.styles['H2Style']))
            elif stripped.startswith('#### '):
                story.append(Paragraph(stripped[5:], self.styles['H3Style']))
            elif stripped.startswith('- '):
                parsed = self._apply_inline_styles(stripped[2:])
                story.append(Paragraph(f"• {parsed}", self.styles['ListItemStyle']))
            else:
                parsed = self._apply_inline_styles(stripped)
                if parsed:
                    story.append(Paragraph(parsed, self.styles['NormalStyle']))

        if in_code_block and current_code_block:
            story.append(Paragraph("\n".join(current_code_block), self.styles['CodeBlockStyle']))

        return story

    def _apply_inline_styles(self, text: str) -> str:
        def bold(m):
            return f'<b>{m.group(1)}</b>'

        # Bold
        text = re.sub(r'\*\*(.*?)\*\*', bold, text)

        # Severity highlights (ReportLab supports simple <font color="..."> and <b>)
        text = text.replace('(Critical)', '<font color="darkred"><b>(Critical)</b></font>')
        text = text.replace('(High)', '<font color="red"><b>(High)</b></font>')
        text = text.replace('(Medium)', '<font color="orange"><b>(Medium)</b></font>')
        text = text.replace('(Low)', '<font color="blue"><b>(Low)</b></font>')
        text = text.replace('(Informational)', '<font color="darkgreen"><b>(Informational)</b></font>')

        return text

    def _build_scan_folder_name(self, host_ip: str) -> str:
        """
        Nombre de carpeta: Escaneo_IP_<IP_con_guiones>_<YYYYMMDD>
        Ejemplo: Escaneo_IP_192_168_1_38_20250718
        """
        date_str = datetime.now().strftime("%Y%m%d")
        ip_clean = host_ip.replace(".", "_")
        return f"Escaneo_IP_{ip_clean}_{date_str}"

    def generate_pdf_report(self,
                            report_content_markdown: str,
                            filename: str,
                            scan_session_name: str,
                            host_ip: Optional[str] = None) -> Optional[str]:
        """
        Genera un PDF. Si host_ip es provisto, se crea (o reutiliza) una carpeta
        con el nombre generado por _build_scan_folder_name(host_ip). Si no, se usa
        scan_session_name tal cual para la carpeta.
        """

        if host_ip:
            folder_name = self._build_scan_folder_name(host_ip)
        else:
            folder_name = scan_session_name

        session_dir = os.path.join(self.output_dir, folder_name)
        os.makedirs(session_dir, exist_ok=True)

        full_path = os.path.join(session_dir, filename)

        doc = SimpleDocTemplate(full_path, pagesize=letter)
        story: List[Any] = []

        # Cabecera
        story.append(Paragraph("Informe de Seguridad Generado por Molly", self.styles['TitleStyle']))
        story.append(Spacer(1, 0.5 * inch))
        story.append(Paragraph(f"Sesion: {folder_name}", self.styles['H1Style']))
        if host_ip:
            story.append(Paragraph(f"Host Analizado: {host_ip}", self.styles['H2Style']))
        story.append(Spacer(1, 0.1 * inch))
        story.append(Paragraph(f"Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", self.styles['NormalStyle']))
        story.append(PageBreak())

        # Contenido
        story.extend(self._parse_markdown(report_content_markdown))

        try:
            doc.build(story)
            logger.info(f"[ReportGenerator] PDF generado: {full_path}")
            return full_path
        except Exception as e:
            logger.error(f"[ReportGenerator ERROR] {e}")
            return None


# Bloque de prueba que genera un reporte cuando se ejecuta como modulo.
if __name__ == '__main__':
    import sys
    # logging basico para ver output
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    # Fallback en caso de que alguien ejecute el archivo directamente (no como paquete).
    # Al ejecutar con: python3 -m reports.report_generator desde backend/ el import relativo debe funcionar.
    # Si alguien ejecuta `python3 reports/report_generator.py` desde backend/ tambien deberia funcionar,
    # pero si se ejecuta desde otra carpeta, intentamos ajustar sys.path.
    try:
        # si ReportFormatter ya esta importado arriba, esto no hace nada
        _ = ReportFormatter
    except Exception:
        # intentar importar con ruta absoluta como respaldo
        try:
            sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
            from reports.report_formatter import ReportFormatter  # type: ignore
        except Exception:
            logger.exception("No se pudo importar ReportFormatter. Asegurate de ejecutar desde la raiz del proyecto (backend/).")
            raise

    # Creamos el generator apuntando a instance/scans
    formatter = ReportFormatter()
    generator = ReportGenerator(report_path_root='instance/scans', report_formatter=formatter)

    # Datos de ejemplo rapidos
    sample_host_ip = "192.168.1.10"
    sample_scan_name = "network_summary_report.pdf"
    sample_markdown = (
        "# Resumen de Prueba\n\n"
        "Este es un reporte de prueba generado por ReportGenerator.\n\n"
        "## Hosts detectados\n"
        "- 192.168.1.10 **(High)** - Servicio FTP con acceso anonimo.\n"
        "- 192.168.1.20 (Low) - Banner SSH expone version.\n\n"
        "### Recomendaciones\n"
        "- Deshabilitar FTP anonimo.\n"
        "- Revisar configuracion de SSH.\n\n"
        "```\n# Ejemplo de bloque de codigo\nnmap -sV 192.168.1.0/24\n```"
    )

    logger.info("Generando reporte de prueba en instance/scans/ ...")
    # Llamada: pasamos host_ip para que se cree la carpeta con formato Escaneo_IP_<ip>_<YYYYMMDD>
    result_path = generator.generate_pdf_report(
        report_content_markdown=sample_markdown,
        filename=sample_scan_name,
        scan_session_name="test_session",  # no se usa si host_ip esta presente
        host_ip=sample_host_ip
    )

    if result_path:
        logger.info(f"Reporte de prueba generado en: {result_path}")
    else:
        logger.error("Fallo la generacion del reporte de prueba.")
