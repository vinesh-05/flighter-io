def post_payment_tasks(booking_id: int, email: str):
    from database import SessionLocal
    from utils.generate_ticket import create_ticket_pdf
    from utils.emailer import send_ticket_email
    from models import FlightBooking
    import traceback

    
    db = SessionLocal()
    booking = None

    try:
        booking = db.query(FlightBooking).filter(
            FlightBooking.id == booking_id
        ).first()

        if not booking:
            print(f"Booking {booking_id} not found")
            return

        if booking.email_sent:
            print(f"Email already sent for booking {booking_id}")
            return

        pdf_path = create_ticket_pdf(booking)
        send_ticket_email(email, pdf_path)

        booking.email_sent = True
        booking.email_attempts = (booking.email_attempts or 0) + 1
        db.commit()

        print(f"Email sent successfully for booking {booking_id}")

    except Exception as e:
        if booking:
            booking.email_attempts = (booking.email_attempts or 0) + 1
            db.commit()

        print(
            f"Post-payment task failed for booking {booking_id}: {e}"
        )
        traceback.print_exc()

    finally:
        db.close()
