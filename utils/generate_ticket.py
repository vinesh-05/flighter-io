import os
import tempfile
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib.colors import HexColor, black, white


def create_ticket_pdf(booking):
    temp_dir = tempfile.gettempdir()
    file_path = os.path.join(temp_dir, f"ticket_{booking.id}.pdf")

    c = canvas.Canvas(file_path, pagesize=letter)
    width, height = letter

    # Colors
    PRIMARY = HexColor("#1e3a8a")   # blue
    LIGHT_BG = HexColor("#f1f5f9")

    # ===== Header =====
    c.setFillColor(PRIMARY)
    c.rect(0, height - 90, width, 90, stroke=0, fill=1)

    c.setFillColor(white)
    c.setFont("Helvetica-Bold", 24)
    c.drawString(40, height - 55, "FLIGHT TICKET")

    c.setFont("Helvetica", 12)
    c.drawRightString(width - 40, height - 55, "Boarding Pass")

    # ===== Ticket Box =====
    c.setFillColor(LIGHT_BG)
    c.roundRect(40, 140, width - 80, height - 260, 12, stroke=0, fill=1)

    c.setFillColor(black)

    # ===== Passenger Info =====
    c.setFont("Helvetica-Bold", 14)
    c.drawString(60, height - 130, "Passenger Details")

    c.setFont("Helvetica", 12)
    c.drawString(60, height - 160, f"User ID: {booking.user_id}")

    # ===== Flight Info =====
    c.setFont("Helvetica-Bold", 14)
    c.drawString(60, height - 210, "Flight Information")

    c.setFont("Helvetica", 12)
    c.drawString(60, height - 240, f"Flight Number : {booking.flight_id}")
    c.drawString(60, height - 265, f"Airline       : {booking.airline}")
    c.drawString(60, height - 290, f"Route         : {booking.origin} → {booking.destination}")

    # ===== Timing Info =====
    c.setFont("Helvetica-Bold", 14)
    c.drawString(60, height - 340, "Schedule")

    c.setFont("Helvetica", 12)
    c.drawString(60, height - 370, f"Departure : {booking.departure_time}")
    c.drawString(60, height - 395, f"Arrival   : {booking.arrival_time}")
    c.drawString(60, height - 420, f"Date      : {booking.date}")

    # ===== Price Box =====
    c.setFillColor(PRIMARY)
    c.roundRect(width - 260, 200, 180, 70, 10, stroke=0, fill=1)

    c.setFillColor(white)
    c.setFont("Helvetica-Bold", 16)
    c.drawCentredString(width - 170, 245, "Total Fare")

    c.setFont("Helvetica-Bold", 20)
    c.drawCentredString(width - 170, 220, f"₹ {booking.price}")

    # ===== Footer =====
    c.setFillColor(black)
    c.setFont("Helvetica-Oblique", 10)
    c.drawCentredString(
        width / 2,
        80,
        "This is a system-generated ticket. Please carry a valid ID proof during travel."
    )

    c.save()
    return file_path
