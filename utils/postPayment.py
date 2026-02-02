def post_payment_tasks(booking_id: int):
    from database import SessionLocal
    from utils.generate_ticket import generate_ticket_pdf
    from utils.emailer import send_ticket_email
    from models import FlightBooking, Passenger
    import traceback

    db = SessionLocal()

    try:
        booking = db.query(FlightBooking).filter(
            FlightBooking.id == booking_id
        ).first()

        if not booking:
            print(f"Booking {booking_id} not found")
            return

        # 🔁 Process each passenger individually
        for passenger in booking.passengers:

            # 🔒 Idempotency guard (per passenger)
            if passenger.ticket_email_sent:
                continue

            # 1️⃣ Generate ticket PDF
            pdf_path = generate_ticket_pdf(booking, passenger)
            passenger.ticket_pdf_path = pdf_path

            # 2️⃣ Decide recipient email
            if passenger.type == "ADULT":
                recipient_email = passenger.email
            else:
                # CHILD / INFANT → guardian email
                guardian = db.query(Passenger).filter(
                    Passenger.id == passenger.guardian_passenger_id
                ).first()

                if not guardian:
                    print(
                        f"Guardian not found for passenger {passenger.id}"
                    )
                    continue

                recipient_email = guardian.email

            # 3️⃣ Send email
            try:
                send_ticket_email(recipient_email, pdf_path)
                passenger.ticket_email_sent = True
            except Exception:
                booking.email_attempts = (booking.email_attempts or 0) + 1
                print(
                    f"Failed sending ticket for passenger {passenger.id}"
                )

        # ✅ Mark booking as fully processed
        booking.email_sent = True
        db.commit()

        print(f"All tickets processed for booking {booking_id}")

    except Exception as e:
        print(
            f"Post-payment task failed for booking {booking_id}: {e}"
        )
        traceback.print_exc()
        db.rollback()

    finally:
        db.close()
