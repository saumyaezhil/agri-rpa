from pathlib import Path
from reportlab.pdfgen import canvas

OUTPUT = Path("sample-data/documents")
OUTPUT.mkdir(parents=True, exist_ok=True)


def create_pdf(filename, lines):
    path = OUTPUT / filename

    pdf = canvas.Canvas(str(path))
    y = 750

    for line in lines:
        pdf.drawString(70, y, line)
        y -= 40

    pdf.save()


create_pdf("aadhaar.pdf", [
    "IDENTITY PROOF",
    "Name: Ravi Kumar",
    "Address: Kanchipuram, Tamil Nadu"
])

create_pdf("land_record.pdf", [
    "LAND RECORD",
    "Name: Ravi Kumar",
    "Survey Number: 124/3A",
    "Village: Kanchipuram",
    "Land Area: 2.4 acres"
])

create_pdf("address_proof.pdf", [
    "ADDRESS PROOF",
    "Name: Ravi Kumar",
    "Address: Kanchipuram, Tamil Nadu",
    "Village: Kanchipuram"
])

print("Sample documents created successfully.")
