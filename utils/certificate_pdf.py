from flask import current_app
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.lib import colors
from datetime import datetime
import os

from my_models import db
from my_models.approval import Approval
from my_models.admin import Admin
from my_models.blockchain import Block
from my_models.student import Student  # Make sure this is imported


import json

def get_blockchain_hash(degree_id):
    try:
        blockchain_path = current_app.config['JSON_STORAGE_PATH']
        with open(blockchain_path, 'r') as f:
            chain = json.load(f)

        for block in reversed(chain):  # Start from the latest block
            data = block.get('data', {})
            if data.get('id') == degree_id:
                return block.get('hash', 'Not Found')

        return "Not Found"
    except Exception as e:
        return f"Error: {str(e)}"



def generate_pdf(degree):
    # Get student details
    student = Student.query.filter_by(student_id=degree.student_id).first()

    student_name = student.full_name if student and student.full_name else "Unnamed Student"

    # Get admin approvals
    approvals = Approval.query.filter_by(degree_id=degree.id, approval_status=True).all()
    approver_names = [Admin.query.get(a.admin_id).username for a in approvals if Admin.query.get(a.admin_id)]
    approved_by_text = "Verified By: " + ", ".join(approver_names) if approver_names else "Verified By: Not Approved"

    created_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    # Get Blockchain Hash
    hash_id = get_blockchain_hash(degree.id)

    # Certificate file path
    filename = f"{degree.student_id}_certificate.pdf"
    cert_dir = os.path.join(current_app.root_path, "data", "certificates")
    os.makedirs(cert_dir, exist_ok=True)
    filepath = os.path.join(cert_dir, filename)

    # Create canvas
    c = canvas.Canvas(filepath, pagesize=letter)
    width, height = letter

    # Logo path
    logo_path = os.path.join(current_app.root_path, "static", "images", "logo.png")

# Draw logo centered at the top
    if os.path.exists(logo_path):
     logo_width = 100
     logo_height = 100
     page_width, page_height = letter
     x = (page_width - logo_width) / 2
     y = page_height - logo_height - 70  # margin from top
     c.drawImage(logo_path, x, y, width=logo_width, height=logo_height, preserveAspectRatio=True)


    # Border
    margin = 50
    c.setStrokeColor(colors.HexColor("#1A237E"))  # Indigo
    c.setLineWidth(4)
    c.rect(margin, margin, width - 2 * margin, height - 2 * margin)

    # Title
    c.setFont("Helvetica-Bold", 24)
    c.setFillColor(colors.HexColor("#0D47A1"))
    c.drawCentredString(width / 2, height - 200, "UNIVERSITY OF KASHMIR")

    c.setFont("Helvetica-Bold", 18)
    c.setFillColor(colors.black)
    c.drawCentredString(width / 2, height - 250, "Degree Certificate")
    

    # Certificate Text
    c.setFont("Helvetica", 13)
    text_y = height - 300
    line_spacing = 40

    lines = [
        f"This is to certify that",
        f"{student_name}",
        f"bearing Student ID {degree.student_id},",
        f"has successfully completed the degree of",
        f"{degree.degree_name}",
        f"from {degree.institution}.",
       # c.drawString(100, 600, f"Created Date: {created_date}")
        #f"Course Duration: 2022 - 2025",
        f"Status: {degree.status}",
        f"Approved By: {approved_by_text}",
        f"Created Date: {created_date}",
    ]

    for i, line in enumerate(lines):
        if i in [1, 4]:  # Make name and degree bold
            c.setFont("Helvetica-Bold", 14)
        else:
            c.setFont("Helvetica", 12)
        c.drawCentredString(width / 2, text_y - i * line_spacing, line)

    # Signature
  #  c.line(width / 2 - 150, 140, width / 2 - 10, 140)
   # c.setFont("Helvetica", 10)
    #c.drawString(width / 2 - 150, 125, "Signature of Controller")

    # Blockchain Hash ID
    c.setFont("Helvetica-Oblique", 9)
    c.setFillColor(colors.gray)
    c.drawString(70, 100, f"Blockchain Hash ID: {hash_id}")

    # Footer
    c.setFont("Helvetica", 8)
    c.setFillColor(colors.black)
    c.drawCentredString(width / 2, 60, "This certificate is digitally secured and verifiable.")

    c.showPage()
    c.save()

    return filepath
