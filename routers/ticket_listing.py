from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from auth import get_current_user
from database import get_db
from models import FlightBooking
import os
from models import Passenger

router = APIRouter(prefix="/bookings", tags=["Bookings"])

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(BASE_DIR)  # adjust if needed


@router.get("/{passenger_id}/ticket")
def download_ticket(
    passenger_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    passenger = db.query(Passenger).join(FlightBooking).filter(
        Passenger.id == passenger_id,
        FlightBooking.user_id == current_user.id
    ).first()

    if not passenger or not passenger.ticket_pdf_path:
        raise HTTPException(status_code=404, detail="Ticket not found")

    # 🔥 RESOLVE ABSOLUTE PATH
    absolute_path = os.path.join(PROJECT_ROOT, passenger.ticket_pdf_path)

    if not os.path.exists(absolute_path):
        raise HTTPException(status_code=404, detail="Ticket file missing")

    return FileResponse(
        absolute_path,
        media_type="application/pdf",
        filename=os.path.basename(absolute_path)
    )
