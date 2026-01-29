from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from auth import get_current_user
from models import FlightBooking
from models import Passenger
from services.bookings.booking import BookingCreateRequest
from services.price_service import PricingService
from services.bookings.booking_validator import validate_passengers

router = APIRouter(prefix="/bookings", tags=["Bookings"])


@router.post("/create")
def create_booking(
    payload: BookingCreateRequest,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    print(payload)
    try:
        validation = validate_passengers(payload.passengers)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # 💰 Calculate price
    total_amount = PricingService.calculate_total(
        base_price=payload.flight.price,
        adults=validation["adults"],
        children=validation["children"],
        infants=validation["infants"],
        trip_type=payload.trip_type
    )

    # 📦 Create booking
    booking = FlightBooking(
        user_id=current_user.id,
        flight_id=payload.flight.flight_id,
        airline=payload.flight.airline,
        price=payload.flight.price,
        date=payload.flight.date,
        origin=payload.flight.origin,
        destination=payload.flight.destination,
        departure_time=payload.flight.departure_time,
        arrival_time=payload.flight.arrival_time,
        trip_type=payload.trip_type,
        booking_contact_email=payload.booking_contact_email,
        total_amount=total_amount,
        currency="INR",
        status="pending"
    )

    db.add(booking)
    db.flush()  # booking.id available

    passenger_objects = []

    # 👤 Create passengers
    for idx, p in enumerate(payload.passengers):
        passenger = Passenger(
            booking_id=booking.id,
            type=p.type,
            name=p.name,
            age=p.age,
            email=p.email,
            phone=p.phone,
            address=p.address
        )
        db.add(passenger)
        db.flush()
        passenger_objects.append(passenger)

    # 👶 Assign guardians
    for idx, p in enumerate(payload.passengers):
        if p.type in ("child", "infant"):
            passenger_objects[idx].guardian_id = passenger_objects[p.guardian_index].id

    db.commit()

    return {
        "booking_id": booking.id,
        "total_amount": total_amount,
        "currency": "INR",
        "status": "pending"
    }
