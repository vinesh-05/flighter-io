def post_payment_tasks(booking_id: int, email: str):
    from database import SessionLocal
    from utils.generate_ticket import create_ticket_pdf
    from utils.emailer import send_ticket_email
    from models import FlightBooking
    import logging

    logger = logging.getLogger(__name__)

    db = SessionLocal()

    try:
        booking = db.query(FlightBooking).filter(
            FlightBooking.id == booking_id
        ).first()

        if not booking:
            logger.error(f"Booking {booking_id} not found")
            return

        # Idempotency guard
        if booking.email_sent:
            return

        pdf_path = create_ticket_pdf(booking)
        send_ticket_email(email, pdf_path)

        booking.email_sent = True
        db.commit()

    except Exception as e:
        db.rollback()
        booking.email_attempts = (booking.email_attempts or 0) + 1
        db.commit()
        logger.error(f"Post-payment task failed for booking {booking_id}: {e}")

        # ❌ DO NOT RAISE

    finally:
        db.close()
