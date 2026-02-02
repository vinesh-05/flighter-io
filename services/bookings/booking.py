from pydantic import BaseModel
from typing import List, Optional, Literal
from datetime import date

class FlightInfo(BaseModel):
    flight_id: str
    airline: str
    price: float
    date: date
    origin: str
    destination: str
    departure_time: str
    arrival_time: str


class BookingPassenger(BaseModel):
    full_name: str
    dob: date
    gender: Literal['MALE','FEMALE','OTHER']

    email: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None

    guardian_index: Optional[int] = None


class BookingCreateRequest(BaseModel):
    flight: FlightInfo
    trip_type: Literal["one_way", "round_trip"]
    booking_contact_email: str
    passengers: list[BookingPassenger]

