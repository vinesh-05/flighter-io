from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from auth import get_current_user
from database import get_db
from models import FlightBooking
import stripe
import os
from dotenv import load_dotenv
from fastapi import Request
from utils.postPayment import post_payment_tasks

load_dotenv()

router = APIRouter(prefix="/flights", tags=["Flights"])

# Load Stripe secret key
STRIPE_SECRET_KEY = os.getenv("STRIPE_SECRET_KEY")
WEBHOOK_SECRET=os.getenv("WEBHOOK_SECRET")
WEBHOOK_LOCAL=os.getenv("WEBHOOK_LOCAL")
if not STRIPE_SECRET_KEY:
    print("⚠️ WARNING: STRIPE_SECRET_KEY not found in .env")

stripe.api_key = STRIPE_SECRET_KEY
SUCCESS_LOCAL_URL=os.getenv("SUCCESS_LOCAL_URL")
CANCEL_LOCAL_URL=os.getenv("CANCEL_LOCAL_URL")
SUCCESS_DEP_URL=os.getenv("SUCCESS_DEP_URL")
CANCEL_DEP_URL=os.getenv("CANCEL_DEP_URL")
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
            success_url=f"{SUCCESS_LOCAL_URL}?session_id={{CHECKOUT_SESSION_ID}}",
            cancel_url=CANCEL_LOCAL_URL,
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

@router.post("/stripe/webhook")
async def stripe_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    print("🔥 Stripe webhook hit")  # <-- HERE (top of route)

    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")

    try:
        event = stripe.Webhook.construct_event(
            payload,
            sig_header,
            WEBHOOK_LOCAL,
        )
    except stripe.error.SignatureVerificationError:
        print("❌ Webhook signature verification failed:")
        return {"error": "Invalid Signature"}

    if event["type"] == "checkout.session.completed":
        session = event["data"]["object"]
        session_id = session["id"]
        booking = (
            db.query(FlightBooking)
            .filter(FlightBooking.stripe_session_id == session_id)
            .first()
        )

        if not booking:
            print("❌ Booking not found for session", session_id)
            return {"status": "booking_not_found"}

        print("🔥 Scheduling background task for booking", booking.id)  # <-- HERE

        if booking.status != "paid":
            booking.status = "paid"
            db.commit()

        if not booking.email_sent:
            background_tasks.add_task(
                post_payment_tasks,
                booking.id
            )

    return {"status": "ok"}


# ---------------------------
# 3️⃣ GET BOOKING HISTORY
# ---------------------------
@router.get("/history")
def get_booking_history(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    bookings = (
        db.query(FlightBooking)
        .filter(FlightBooking.user_id == current_user.id)
        .order_by(FlightBooking.timestamp.desc())
        .all()
    )

    return [
        {
            "id": b.id,
            "airline": b.airline,
            "from": b.origin,
            "to": b.destination,
            "date": b.date,
            "price": b.price,
            "status": b.status,
            "has_ticket": bool(b.ticket_pdf_path),
            "timestamp": b.timestamp
        }
        for b in bookings
    ]
