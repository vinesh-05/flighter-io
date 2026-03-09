from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.units import cm
from reportlab.lib.colors import HexColor
from reportlab.graphics.barcode import code128
import os
from datetime import datetime

def generate_ticket_pdf(booking, passenger):
    file_name = f"ticket_booking_{booking.id}_passenger_{passenger.id}.pdf"
    file_path = f"tickets/{file_name}"

    os.makedirs("tickets", exist_ok=True)

    c = canvas.Canvas(file_path, pagesize=A4)
    width, height = A4

    # --- Modern Brand Colors ---
    primary_blue = HexColor("#1976D2")
    dark_blue = HexColor("#0A2540")
    text_gray = HexColor("#64748B")
    bg_light_blue = HexColor("#F0F4F9")
    border_color = HexColor("#E2E8F0")
    black = HexColor("#000000")
    white = HexColor("#FFFFFF")

    # --- Dynamic Card Dimensions ---
    num_passengers = len(booking.passengers)
    card_width = width - 3 * cm
    card_x = 1.5 * cm
    
    base_card_height = 14 * cm
    extra_height = (num_passengers * 0.5 * cm)
    card_height = base_card_height + extra_height
    card_y = height - 2 * cm - card_height

    # --- 1. Draw Main Ticket Card ---
    c.setFillColor(white)
    c.setStrokeColor(border_color)
    c.setLineWidth(1.5)
    c.roundRect(card_x, card_y, card_width, card_height, 15, stroke=1, fill=1)

    # --- 2. Perforated Edge ---
    perforation_x = card_x + card_width - 3.5 * cm
    c.setStrokeColor(border_color)
    c.setDash(4, 4)
    c.line(perforation_x, card_y, perforation_x, card_y + card_height)
    c.setDash()

    content_width = perforation_x - card_x
    cur_y = card_y + card_height - 1.8 * cm
    left_margin = card_x + 1.5 * cm

    # --- 3. Header ---
    c.setFont("Helvetica-Bold", 16)
    c.setFillColor(primary_blue)
    c.drawString(left_margin, cur_y, "✈ FLIGHTER AI")

    box_w = 4 * cm
    box_h = 0.8 * cm
    box_x = perforation_x - box_w - 1 * cm
    c.setFillColor(white)
    c.setStrokeColor(border_color)
    c.roundRect(box_x, cur_y - 0.2 * cm, box_w, box_h, 5, stroke=1, fill=1)
    
    c.setFont("Helvetica-Bold", 9)
    c.setFillColor(dark_blue)
    c.drawString(box_x + 0.4 * cm, cur_y + 0.05 * cm, f"BOOKING ID: {booking.id}")

    cur_y -= 1.5 * cm

    # --- 4. Main Title & Passenger ---
    c.setFont("Helvetica-Bold", 22)
    c.setFillColor(dark_blue)
    c.drawString(left_margin, cur_y, "FLIGHT TICKET")
    
    cur_y -= 1.2 * cm
    
    c.setFont("Helvetica", 9)
    c.setFillColor(text_gray)
    c.drawString(left_margin, cur_y, "PASSENGER:")
    
    c.setFont("Helvetica-Bold", 12)
    c.setFillColor(black)
    c.drawString(left_margin + 2.5 * cm, cur_y, passenger.full_name)

    cur_y -= 2.2 * cm

    # --- 5. Route Section ---
    c.setFont("Helvetica-Bold", 26)
    c.setFillColor(black)
    
    origin_str = str(booking.origin).upper()
    dest_str = str(booking.destination).upper()
    
    c.drawString(left_margin, cur_y, origin_str)
    
    dest_w = c.stringWidth(dest_str, "Helvetica-Bold", 26)
    dest_x = perforation_x - 1 * cm - dest_w
    c.drawString(dest_x, cur_y, dest_str)

    c.setStrokeColor(primary_blue)
    c.setLineWidth(2)
    line_y = cur_y + 0.3 * cm
    origin_w = c.stringWidth(origin_str, "Helvetica-Bold", 26)
    line_start = left_margin + origin_w + 0.5 * cm
    line_end = dest_x - 0.5 * cm
    c.line(line_start, line_y, line_end, line_y)
    
    c.setFillColor(primary_blue)
    c.saveState()
    c.translate(line_end, line_y)
    path = c.beginPath()
    path.moveTo(0, 0)
    path.lineTo(-6, 4)
    path.lineTo(-6, -4)
    path.close()
    c.drawPath(path, stroke=0, fill=1)
    c.restoreState()

    cur_y -= 1.5 * cm

    # --- 6. Time Details ---
    c.setFont("Helvetica", 8)
    c.setFillColor(text_gray)
    c.drawString(left_margin, cur_y, "DEPARTURE")
    
    c.setFont("Helvetica-Bold", 12)
    c.setFillColor(black)
    c.drawString(left_margin, cur_y - 0.5 * cm, f"{booking.date} | {booking.departure_time}")

    c.setFont("Helvetica", 8)
    c.setFillColor(text_gray)
    c.drawString(dest_x, cur_y, "ARRIVAL")
    
    c.setFont("Helvetica-Bold", 12)
    c.setFillColor(black)
    c.drawString(dest_x, cur_y - 0.5 * cm, f"{booking.arrival_time}")

    cur_y -= 2.5 * cm

    # --- 7. "Travelling With" Box ---
    box2_w = content_width - 2.5 * cm
    box2_h = 1 * cm + (num_passengers * 0.5 * cm)
    c.setFillColor(bg_light_blue)
    c.setStrokeColor(primary_blue)
    c.setLineWidth(1)
    
    c.roundRect(left_margin, cur_y - box2_h + 0.4 * cm, box2_w, box2_h, 8, stroke=1, fill=1)

    py = cur_y - 0.1 * cm
    c.setFont("Helvetica-Bold", 10)
    c.setFillColor(dark_blue)
    c.drawString(left_margin + 0.5 * cm, py, "Travelling With:")
    
    py -= 0.6 * cm
    c.setFont("Helvetica", 9)
    c.setFillColor(black)
    
    for p in booking.passengers:
        label = f"{p.full_name} ({p.type.title()})"
        if p.id == passenger.id:
            label += "  <-- This ticket"
        
        c.drawString(left_margin + 0.8 * cm, py, f"• {label}")
        py -= 0.5 * cm

    cur_y = cur_y - box2_h - 0.2 * cm

    # --- 8. Total Amount Box (FIXED ALIGNMENT) ---
    box3_h = 1.2 * cm
    c.setFillColor(white)
    c.setStrokeColor(border_color)
    c.roundRect(left_margin, cur_y - box3_h, box2_w, box3_h, 8, stroke=1, fill=1)

    # Left align the label
    c.setFont("Helvetica-Bold", 12)
    c.setFillColor(black)
    c.drawString(left_margin + 0.5 * cm, cur_y - 0.8 * cm, "Total Booking Amount:")
    
    # Right align the price
    price_str = f"INR {booking.total_amount}"
    c.setFont("Helvetica-Bold", 14)
    c.setFillColor(primary_blue)
    price_w = c.stringWidth(price_str, "Helvetica-Bold", 14)
    
    # Draw it at the far right of the box, minus 0.5cm of padding
    c.drawString(left_margin + box2_w - price_w - 0.5 * cm, cur_y - 0.8 * cm, price_str)

    cur_y = cur_y - box3_h - 0.6 * cm

    # --- 9. Footer Text ---
    c.setFont("Helvetica", 8)
    c.setFillColor(text_gray)
    c.drawString(left_margin, cur_y, f"Issued on: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}")

    # --- 10. Draw Barcode ---
    c.saveState()
    c.translate(perforation_x + 1 * cm, card_y + 1.5 * cm)
    c.rotate(90)
    
    barcode_data = f"BID{booking.id}-PID{passenger.id}"
    barcode = code128.Code128(barcode_data, barHeight=1.5 * cm, barWidth=1.1)
    barcode.drawOn(c, 0, 0)
    
    c.restoreState()

    c.showPage()
    c.save()

    return file_path