from pydantic import BaseModel, EmailStr
from typing import List, Optional, Literal


class FlightInfo(BaseModel):
    flight_id: str
    airline: str
    price: float
    date: str
    origin: str
    destination: str
    departure_time: str
    arrival_time: str


class PassengerCreate(BaseModel):
    type: Literal["adult", "child", "infant"]
    name: str
    age: int

    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    address: Optional[str] = None

    guardian_index: Optional[int] = None


class BookingCreateRequest(BaseModel):
    flight: FlightInfo
    trip_type: Literal["one_way", "round_trip"]
    booking_contact_email: EmailStr
    passengers: List[PassengerCreate]
