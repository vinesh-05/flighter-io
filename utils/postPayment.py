def post_payment_tasks(booking_id: int, email: str):
    from database import SessionLocal
    from utils.generate_ticket import create_ticket_pdf
    from utils.emailer import send_ticket_email
    from models import FlightBooking

    db = SessionLocal()
    booking = db.query(FlightBooking).get(booking_id)

    pdf_path = create_ticket_pdf(booking)
    send_ticket_email(email, pdf_path)

    db.close()
