from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from auth import get_current_user
from database import get_db
from models import FlightBooking
import stripe
import os

router = APIRouter(prefix="/flights", tags=["Flights"])

# Load Stripe secret key
STRIPE_SECRET_KEY = os.getenv("STRIPE_SECRET_KEY")

if not STRIPE_SECRET_KEY:
    print("⚠️ WARNING: STRIPE_SECRET_KEY not found in .env")

stripe.api_key = STRIPE_SECRET_KEY


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
            success_url="https://example.com/success?session_id={CHECKOUT_SESSION_ID}",
            cancel_url="https://example.com/cancel",
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Stripe error: {str(e)}")

    payment_url = checkout_session.url

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
        payment_url=payment_url
    )

    db.add(booking)
    db.commit()
    db.refresh(booking)

    return {
        "message": "Flight selected. Complete payment using the link.",
        "payment_url": payment_url,
        "booking_id": booking.id
    }


# ---------------------------
# 2️⃣ CONFIRM BOOKING (manual confirm)
# ---------------------------
@router.post("/confirm")
def confirm_booking(
    booking_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    """
    Mark booking as paid (manual confirmation for now).
    """

    booking = db.query(FlightBooking)\
        .filter(FlightBooking.id == booking_id,
                FlightBooking.user_id == current_user.id)\
        .first()

    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")

    booking.status = "paid"
    db.commit()

    return {
        "message": "Payment confirmed. Your flight is booked!",
        "booking_details": {
            "airline": booking.airline,
            "from": booking.origin,
            "to": booking.destination,
            "date": booking.date,
            "price": booking.price
        }
    }


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
