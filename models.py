from sqlalchemy import Column, Integer, String, Text, ForeignKey, DateTime, Float, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime
from database import Base
import json
from sqlalchemy.dialects.postgresql import JSON

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, nullable=False)
    email=Column(String, unique=True, nullable=False)
    password_hash = Column(String, nullable=False)
    conversations = relationship("Conversation", back_populates="user")
    bookings = relationship("FlightBooking", back_populates="user")

class FlightBooking(Base):
    __tablename__ = "flight_bookings"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))

    flight_id = Column(String)            # new (from Amadeus offer["id"])
    airline = Column(String)              # new
    price = Column(Float)                 # new
    date = Column(String)                 # new

    origin = Column(String)
    destination = Column(String)

    departure_time = Column(String)       # changed from DateTime → String
    arrival_time = Column(String)         # changed from DateTime → String

    status = Column(String, default="pending")  # keep
    payment_url = Column(String)          # new
    ticket_pdf_path = Column(Text, nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow)  # new
    stripe_session_id = Column(String, nullable=True)
    email_sent = Column(Boolean, default=False)
    email_attempts = Column(Integer, default=0)
    user = relationship("User", back_populates="bookings")
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