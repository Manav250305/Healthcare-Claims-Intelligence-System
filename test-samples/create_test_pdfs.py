import json
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

with open("test_claims.json") as f:
    claims = json.load(f)

for i, claim in enumerate(claims, 1):
    filename = f"test_claim_{i:02d}.pdf"
    c = canvas.Canvas(filename, pagesize=letter)
    
    c.setFont("Helvetica-Bold", 14)
    c.drawString(50, 750, "HEALTH INSURANCE CLAIM FORM")
    
    c.setFont("Helvetica-Bold", 10)
    c.drawString(50, 720, "PATIENT INFORMATION")
    
    c.setFont("Helvetica", 9)
    y = 700
    for line in [
        f"Name: {claim['patient_name']}",
        f"DOB: {claim['dob']} | Gender: {claim['gender']}",
        f"Member ID: {claim['member_id']}",
        f"Date of Service: {claim['date_of_service']}",
        f"Provider: {claim['provider']}",
        f"Facility: {claim['facility']}",
        "",
        f"Diagnosis Codes: {', '.join(claim['diagnoses'])}",
        f"Procedure Codes: {', '.join(claim['procedures'])}",
        "",
        f"Total Charge: ${claim['total_charge']}",
        f"Insurance Paid: ${claim['insurance_paid']}",
    ]:
        c.drawString(50, y, line)
        y -= 15
    
    c.save()
    print(f"✅ {filename}")

print("✅ All PDFs created!")
