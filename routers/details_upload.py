from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from models import PassengerIdentity
from database import get_db
from auth import get_current_user
from datetime import date
from datetime import date
from services.bookings.booking import BookingPassenger
router=APIRouter(prefix="/details",tags=["identities"])

@router.post("/upload")
async def upload_details(
    payload: BookingPassenger,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):

    if payload.dob >= date.today():
        raise HTTPException(status_code=400, detail="Invalid DOB")

    if payload.gender not in ['MALE','FEMALE','OTHER']:
        raise HTTPException(status_code=400, detail="Invalid Gender")
        
    


    # 2️⃣ Save identity EVEN IF PARTIAL
    details = PassengerIdentity(
        user_id=current_user.id,
        full_name=payload.full_name,   # may be None
        dob=payload.dob,
        email=payload.email,
        gender=payload.gender,
        phone=payload.phone,
        Address=payload.address
    )

    db.add(details)
    db.commit()
    db.refresh(details)

    # 3️⃣ Prepare response
    response = {
        "message": "Passenger Details uploaded successfully",
        "identity": {
            "id": details.id,
            "full_name": details.full_name,
            "dob": details.dob,
            "gender": details.gender,
            "phone": details.phone,
            "address": details.Address
        }
    }

    return response


@router.get("/get")
async def get_uploaded_identities(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    identities = (
        db.query(PassengerIdentity)
        .filter(PassengerIdentity.user_id == current_user.id)
        .all()
    )

    return [
        {
            "id": p.id,
            "full_name": p.full_name,
            "dob": p.dob,
            "gender": p.gender,
            "email": p.email,
            "phone": p.phone,
            "address": p.Address
        }
        for p in identities
    ]
