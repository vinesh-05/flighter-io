import os
import tempfile
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter

def create_ticket_pdf(booking):
    # Create temp directory for ticket files
    temp_dir = tempfile.gettempdir()  # Works on Windows/Mac/Linux

    file_path = os.path.join(temp_dir, f"ticket_{booking.id}.pdf")

    c = canvas.Canvas(file_path, pagesize=letter)

    c.setFont("Helvetica-Bold", 20)
    c.drawString(200, 750, "Flight Ticket")

    c.setFont("Helvetica", 14)
    c.drawString(50, 700, f"Passenger User ID : {booking.user_id}")
    c.drawString(50, 670, f"Flight Number     : {booking.flight_id}")
    c.drawString(50, 640, f"Airline           : {booking.airline}")
    c.drawString(50, 610, f"Route             : {booking.origin} → {booking.destination}")
    c.drawString(50, 580, f"Departure         : {booking.departure_time}")
    c.drawString(50, 550, f"Arrival           : {booking.arrival_time}")
    c.drawString(50, 520, f"Date              : {booking.date}")
    c.drawString(50, 490, f"Price             : ₹{booking.price}")

    c.save()
    return file_path
