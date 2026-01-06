from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from auth import get_current_user
from database import get_db
from models import FlightBooking
import os

router = APIRouter(prefix="/bookings", tags=["Bookings"])

@router.get("/{booking_id}/ticket")
def download_ticket(
    booking_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    booking = db.query(FlightBooking).filter(
        FlightBooking.id == booking_id,
        FlightBooking.user_id == current_user.id,
    ).first()

    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")

    if booking.status != "paid":
        raise HTTPException(status_code=403, detail="Ticket not available")

    if not booking.ticket_pdf_path or not os.path.exists(booking.ticket_pdf_path):
        raise HTTPException(status_code=404, detail="Ticket file missing")

    return FileResponse(
        booking.ticket_pdf_path,
        media_type="application/pdf",
        filename=f"ticket_{booking.id}.pdf"
    )
