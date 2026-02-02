from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import date

from database import get_db
from auth import get_current_user
from models import FlightBooking, Passenger
from services.bookings.booking import BookingCreateRequest
from services.price_service import PricingService

router = APIRouter(prefix="/bookings", tags=["Bookings"])


def get_passenger_type(dob: date, travel_date: date) -> str:
    age = travel_date.year - dob.year - (
        (travel_date.month, travel_date.day) < (dob.month, dob.day)
    )
    if age < 2:
        return "INFANT"
    elif age < 12:
        return "CHILD"
    return "ADULT"


@router.post("/create")
def create_booking(
    payload: BookingCreateRequest,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    if not payload.passengers:
        raise HTTPException(400, "At least one passenger is required")

    passenger_types = []
    for p in payload.passengers:
        if p.dob >= payload.flight.date:
            raise HTTPException(400, "Invalid DOB")

        passenger_types.append(
            get_passenger_type(p.dob, payload.flight.date)
        )

    adults = passenger_types.count("ADULT")
    infants = passenger_types.count("INFANT")
    childs = passenger_types.count("CHILD")
    if infants or childs > adults:
        raise HTTPException(
            400, "Each infant/child must be accompanied by an adult"
        )
    # 🔒 Rule validation
    for idx, (p, p_type) in enumerate(zip(payload.passengers, passenger_types)):
        if p_type == "ADULT":
            if not p.email or not p.phone or not p.address:
                raise HTTPException(
                    400,
                    f"Adult passenger at index {idx} must provide email, phone, and address"
                )

        if p_type in ("CHILD", "INFANT"):
            if p.guardian_index is None:
                raise HTTPException(
                    400,
                    f"Guardian index required for {p_type.lower()} at index {idx}"
                )

            if p.guardian_index >= len(payload.passengers):
                raise HTTPException(
                    400,
                    f"Invalid guardian index for passenger at index {idx}"
                )

            if passenger_types[p.guardian_index] != "ADULT":
                raise HTTPException(
                    400,
                    f"Guardian must be an adult for passenger at index {idx}"
                )

    # 💰 Pricing
    total_amount = PricingService.calculate_total(
        base_price=payload.flight.price,
        adults=passenger_types.count("ADULT"),
        children=passenger_types.count("CHILD"),
        infants=passenger_types.count("INFANT"),
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
    db.flush()

    passenger_objects = []

    # 👤 Create passengers
    for p, p_type in zip(payload.passengers, passenger_types):
        passenger = Passenger(
            booking_id=booking.id,
            full_name=p.full_name,
            dob=p.dob,
            gender=p.gender,
            type=p_type,
            email=p.email,
            phone=p.phone,
            address=p.address
        )
        db.add(passenger)
        db.flush()
        passenger_objects.append(passenger)

    # 👶 Assign guardians + inherit contact info
    for idx, p_type in enumerate(passenger_types):
        if p_type in ("CHILD", "INFANT"):
            guardian = passenger_objects[payload.passengers[idx].guardian_index]

            passenger_objects[idx].guardian_passenger_id = guardian.id
            passenger_objects[idx].email = guardian.email
            passenger_objects[idx].phone = guardian.phone
            passenger_objects[idx].address = guardian.address

    db.commit()

    return {
        "booking_id": booking.id,
        "total_amount": total_amount,
        "currency": "INR",
        "status": "pending"
    }
