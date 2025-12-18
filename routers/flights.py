from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from auth import get_current_user
from database import get_db
from models import FlightBooking
import stripe
import os
from dotenv import load_dotenv

load_dotenv()

router = APIRouter(prefix="/flights", tags=["Flights"])

# Load Stripe secret key
STRIPE_SECRET_KEY = os.getenv("STRIPE_SECRET_KEY")

if not STRIPE_SECRET_KEY:
    print("⚠️ WARNING: STRIPE_SECRET_KEY not found in .env")

stripe.api_key = STRIPE_SECRET_KEY

from pydantic import BaseModel

class ConfirmRequest(BaseModel):
    session_id: str

# ----------------------------------------------------------
# 1️⃣  SELECT FLIGHT → CREATE BOOKING → GENERATE PAYMENT LINK
# ----------------------------------------------------------
@router.post("/select")
def select_flight(
    flight_id: str,
    airline: str,
    price: float,
    date: str,
    origin: str,
    destination: str,
    departure_time: str,
    arrival_time: str,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    """
    Create a booking after user selects a flight.
    Then generate a Stripe Checkout payment link.
    """

    try:
        # Create a Stripe checkout session
        checkout_session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=[{
                'price_data': {
                    'currency': 'inr',
                    'product_data': {
                        'name': f"Flight {origin} → {destination} ({airline})",
                    },
                    'unit_amount': int(price * 100),  # amount in paise
                },
                'quantity': 1,
            }],
            mode='payment',
            success_url="https://flighter-io-frontend.vercel.app/success?session_id={CHECKOUT_SESSION_ID}",
            cancel_url="https://flighter-io-frontend.vercel.app/cancel",
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Stripe error: {str(e)}")

    payment_url = checkout_session.url
    print("SESSION URL:", payment_url)
    print("NEW CHECKOUT SESSION:", checkout_session.id)
    print("NEW CHECKOUT URL:", checkout_session.url)


    # Save booking
    booking = FlightBooking(
        user_id=current_user.id,
        flight_id=flight_id,
        airline=airline,
        price=price,
        date=date,
        origin=origin,
        destination=destination,
        departure_time=departure_time,
        arrival_time=arrival_time,
        status="pending",
        payment_url=payment_url,
        stripe_session_id=checkout_session.id  # ← ADD THIS
    )

    db.add(booking)
    db.commit()
    db.refresh(booking)

    response= f"thank you for choosing flight {flight_id}. Please pay through this link: {payment_url}"
    return response


# ---------------------------
# 2️⃣ CONFIRM BOOKING (manual confirm)
# ---------------------------
@router.post("/confirm-payment")
def confirm_payment(payload: ConfirmRequest, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    session_id = payload.session_id

    booking = db.query(FlightBooking)\
        .filter(FlightBooking.stripe_session_id == session_id)\
        .first()

    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")

    # Mark booking as paid
    booking.status = "paid"
    db.commit()

    # Generate ticket
    from utils.generate_ticket import create_ticket_pdf
    pdf_path = create_ticket_pdf(booking)

    # Email to user
    from utils.emailer import send_ticket_email
    send_ticket_email(current_user.email, pdf_path)

    return {"message": "Payment confirmed. Ticket emailed."}


# ---------------------------
# 3️⃣ GET BOOKING HISTORY
# ---------------------------
@router.get("/history")
def get_booking_history(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    bookings = db.query(FlightBooking)\
        .filter(FlightBooking.user_id == current_user.id)\
        .order_by(FlightBooking.timestamp.desc())\
        .all()

    return [
        {
            "id": b.id,
            "airline": b.airline,
            "from": b.origin,
            "to": b.destination,
            "date": b.date,
            "price": b.price,
            "status": b.status,
            "payment_url": b.payment_url,
            "timestamp": b.timestamp
        }
        for b in bookings
    ]
