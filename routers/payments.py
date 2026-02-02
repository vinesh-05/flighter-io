from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
import stripe
from database import get_db
from dotenv import load_dotenv
import os
from auth import get_current_user
from models import FlightBooking
from services.price_service import PricingService
from utils.payments import CreateStripeSessionRequest

load_dotenv()
stripe.api_key=os.getenv("STRIPE_SECRET_KEY")
SUCCESS_LOCAL_URL=os.getenv("SUCCESS_LOCAL_URL")
CANCEL_LOCAL_URL=os.getenv("CANCEL_LOCAL_URL")
router = APIRouter(prefix="/payments", tags=["Payments"])

@router.post("/create-session")
def create_stripe_session(
    payload: CreateStripeSessionRequest,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    booking = db.query(FlightBooking).filter(
        FlightBooking.id == payload.booking_id,
        FlightBooking.user_id == current_user.id
    ).first()

    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")

    if booking.status != "pending":
        raise HTTPException(status_code=400, detail="Booking is not payable")

    # 🔐 Recalculate price (DO NOT TRUST DB blindly)
    adults = sum(1 for p in booking.passengers if p.type == "ADULT")
    children = sum(1 for p in booking.passengers if p.type == "CHILD")
    infants = sum(1 for p in booking.passengers if p.type == "INFANT")

    recalculated_total = PricingService.calculate_total(
        base_price=booking.price,
        adults=adults,
        children=children,
        infants=infants,
        trip_type=booking.trip_type
    )

    if recalculated_total != booking.total_amount:
        raise HTTPException(status_code=400, detail="Price mismatch detected")

    # 🔁 Prevent duplicate Stripe sessions
    if booking.stripe_session_id:
        session = stripe.checkout.Session.retrieve(
            booking.stripe_session_id
        )
        return {"checkout_url": session.url}

    # 💳 Create Stripe checkout session
    session = stripe.checkout.Session.create(
        payment_method_types=["card"],
        mode="payment",
        customer_email=booking.booking_contact_email,
        line_items=[{
            "price_data": {
                "currency": booking.currency.lower(),
                "product_data": {
                    "name": f"Flight {booking.origin} → {booking.destination}",
                    "description": f"{booking.trip_type.replace('_', ' ').title()}"
                },
                "unit_amount": int(booking.total_amount * 100)
            },
            "quantity": 1
        }],
        metadata={
            "booking_id": booking.id
        },
            success_url=f"{SUCCESS_LOCAL_URL}?session_id={{CHECKOUT_SESSION_ID}}",
            cancel_url=CANCEL_LOCAL_URL,
    )

    booking.stripe_session_id = session.id
    booking.payment_url = session.url
    db.commit()

    return {"checkout_url": session.url}
