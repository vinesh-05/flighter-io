from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.units import cm
import os
from datetime import datetime

def generate_ticket_pdf(booking, passenger):
    file_name = f"ticket_booking_{booking.id}_passenger_{passenger.id}.pdf"
    file_path = f"tickets/{file_name}"

    os.makedirs("tickets", exist_ok=True)

    c = canvas.Canvas(file_path, pagesize=A4)
    width, height = A4
    y = height - 2 * cm

    # Header
    c.setFont("Helvetica-Bold", 18)
    c.drawString(2 * cm, y, "FLIGHT TICKET")
    y -= 1.2 * cm

    c.setFont("Helvetica", 10)
    c.drawString(2 * cm, y, f"Booking ID: {booking.id}")
    y -= 0.6 * cm

    # 🔹 Primary passenger (THIS ticket belongs to)
    c.setFont("Helvetica-Bold", 12)
    c.drawString(2 * cm, y, f"Passenger: {passenger.full_name}")
    y -= 0.5 * cm

    c.setFont("Helvetica", 10)
    y -= 0.8 * cm

    # 🔹 All passengers (group context)
    c.setFont("Helvetica-Bold", 11)
    c.drawString(2 * cm, y, "Travelling With:")
    y -= 0.5 * cm

    c.setFont("Helvetica", 10)
    for p in booking.passengers:
        label = f"{p.full_name} ({p.type.title()})"
        if p.id == passenger.id:
            label += "  ← This ticket"

        c.drawString(2.5 * cm, y, f"- {label}")
        y -= 0.4 * cm

    y -= 0.6 * cm

    # Flight info
    c.setFont("Helvetica", 10)
    c.drawString(
        2 * cm,
        y,
        f"Route: {booking.origin} → {booking.destination}"
    )
    y -= 0.4 * cm

    c.drawString(
        2 * cm,
        y,
        f"Date: {booking.date} | Departure: {booking.departure_time} | Arrival: {booking.arrival_time}"
    )
    y -= 0.8 * cm

    # Payment info
    c.setFont("Helvetica-Bold", 11)
    c.drawString(2 * cm, y, f"Total Booking Amount: ₹{booking.total_amount}")
    y -= 0.6 * cm

    c.setFont("Helvetica", 9)
    c.drawString(
        2 * cm,
        y,
        f"Issued on: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}"
    )

    c.showPage()
    c.save()

    return file_path
