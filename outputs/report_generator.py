from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph
from datetime import datetime
import os

def generate_report(image_name, file_hash, detection_result, p_value, extracted_data=None):
    """Generates a PDF forensic report."""
    
    output_dir = "outputs/reports"
    os.makedirs(output_dir, exist_ok=True)
    report_path = os.path.join(output_dir, f"report_{os.path.splitext(image_name)[0]}.pdf")
    
    c = canvas.Canvas(report_path, pagesize=letter)
    width, height = letter
    
    styles = getSampleStyleSheet()
    style_normal = styles['Normal']
    style_heading = styles['h1']

    title = Paragraph("Steganography Forensic Report", style_heading)
    title.wrapOn(c, width - 100, height)
    title.drawOn(c, 50, height - 50)
    
    c.drawString(50, height - 80, f"Report Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    c.line(50, height - 90, width - 50, height - 90)
    
    text_y = height - 120
    
    c.drawString(50, text_y, f"Analyzed File: {image_name}")
    c.drawString(50, text_y - 20, f"SHA256 Hash: {file_hash}")
    
    detection_status = "Hidden Data Suspected" if detection_result else "No Hidden Data Detected"
    c.drawString(50, text_y - 50, f"Detection Status: {detection_status}")
    c.drawString(50, text_y - 70, f"Chi-Square P-Value: {p_value:.4f} (A value < 0.05 suggests non-random data)")
    
    c.line(50, text_y - 90, width - 50, text_y - 90)
    
    c.drawString(50, text_y - 110, "Extracted Data:")
    if extracted_data:
        data_p = Paragraph(extracted_data, style_normal)
        data_p.wrapOn(c, width - 100, text_y - 250)
        data_p.drawOn(c, 50, text_y - 140)
    else:
        c.drawString(60, text_y - 130, "N/A")
        
    c.save()
    return report_path