from sqlalchemy import Column, Integer, String, Text, ForeignKey, DateTime, Float, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime
from database import Base
import json
from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy.sql import func

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, nullable=False)
    email=Column(String, unique=True, nullable=False)
    password_hash = Column(String, nullable=False)
    conversations = relationship("Conversation", back_populates="user")
    bookings = relationship("FlightBooking", back_populates="user")

class Passenger(Base):
    __tablename__ = "passengers"

    id = Column(Integer, primary_key=True, index=True)

    booking_id = Column(Integer, ForeignKey("flight_bookings.id", ondelete="CASCADE"))

    type = Column(String)  # adult | child | infant
    name = Column(String, nullable=False)
    age = Column(Integer, nullable=False)

    email = Column(String, nullable=True)
    phone = Column(String, nullable=True)
    address = Column(String, nullable=True)

    guardian_id = Column(Integer, ForeignKey("passengers.id"), nullable=True)

    booking = relationship("FlightBooking", back_populates="passengers")
    guardian = relationship("Passenger", remote_side=[id])
    ticket_pdf_path = Column(Text, nullable=True)
    ticket_email_sent = Column(Boolean, default=False)

class FlightBooking(Base):
    __tablename__ = "flight_bookings"

    id = Column(Integer, primary_key=True, index=True)

    # Auth
    user_id = Column(Integer, ForeignKey("users.id"))

    # Flight info
    flight_id = Column(String)            # Amadeus offer ID
    airline = Column(String)
    price = Column(Float)                 # base price (one adult, one-way)
    date = Column(String)

    origin = Column(String)
    destination = Column(String)

    departure_time = Column(String)
    arrival_time = Column(String)

    # 🆕 Booking configuration
    trip_type = Column(String, default="one_way")   # one_way | round_trip
    booking_contact_email = Column(String, nullable=False)

    # 🆕 Pricing
    total_amount = Column(Float)
    currency = Column(String, default="INR")

    # Status & payment
    status = Column(String, default="pending")      # pending | paid | ticket_emailed
    payment_url = Column(String)
    stripe_session_id = Column(String, nullable=True)

    # Ticket & email
    ticket_pdf_path = Column(Text, nullable=True)
    email_sent = Column(Boolean, default=False)
    email_attempts = Column(Integer, default=0)

    # Timestamp
    timestamp = Column(DateTime, default=datetime.utcnow)

    # Relations
    user = relationship("User", back_populates="bookings")
    passengers = relationship(
        "Passenger",
        back_populates="booking",
        cascade="all, delete-orphan"
    )
    
class Conversation(Base):
    __tablename__ = "conversations"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    message = Column(Text)
    response = Column(Text)
    intent=Column(String,nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    user = relationship("User", back_populates="conversations")
    flight_context = Column(JSON, nullable=True)


class PassengerIdentity(Base):
    __tablename__= "passenger_identities"
    id=Column(Integer, primary_key=True, index=True)
       # user who owns this identity
    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False
    )

    full_name = Column(String(100), nullable=False)
    dob = Column(Date, nullable=True)
    gender = Column(String(10), nullable=True)

    email = Column(String(100), nullable=True)
    phone = Column(String(20), nullable=True)

    # Aadhaar / Passport / Other
    document_type = Column(String(20), nullable=True)

    # last 4 digits only (masked storage)
    document_last4 = Column(String(4), nullable=True)

    verified = Column(Boolean, default=False)

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now()
    )

