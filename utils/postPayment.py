def post_payment_tasks(booking_id: int, email: str):
    from database import SessionLocal
    from utils.generate_ticket import create_ticket_pdf
    from utils.emailer import send_ticket_email
    from models import FlightBooking
    import time

    db = SessionLocal()
    booking = db.query(FlightBooking).get(booking_id)

    if booking.email_sent:
        db.close()
        return

    try:
        pdf_path = create_ticket_pdf(booking)
        send_ticket_email(email, pdf_path)

        booking.email_sent = True
        db.commit()

    except Exception as e:
        booking.email_attempts += 1
        db.commit()
        raise e

    finally:
        db.close()
