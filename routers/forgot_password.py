from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from database import get_db
from models import User
from auth_schema import ForgotPasswordRequest
from utils.auth_utils import create_password_reset_token
from utils.emailer import send_password_reset_email
from datetime import datetime, timedelta
router = APIRouter()

@router.post("/forgot-password")
def forgot_password(data: ForgotPasswordRequest, db: Session = Depends(get_db)):

    user = db.query(User).filter(User.email == data.email).first()

    if not user:
        return {"message": "If the email exists, a reset link has been sent"}

    now = datetime.utcnow()

    # Reset counter if 1 hour passed
    if user.reset_email_last_sent:
        if now - user.reset_email_last_sent > timedelta(hours=1):
            user.reset_email_count = 0

    # Rate limit
    if user.reset_email_count >= 3:
        return {"message": "Too many reset requests. Try again later."}

    token = create_password_reset_token(user.email)
    print(token)
    reset_link = f"http://localhost:5173/reset-password?token={token}"

    send_password_reset_email(user.email, reset_link)

    # Update counters
    user.reset_email_count += 1
    user.reset_email_last_sent = now

    db.commit()

    return {"message": "If the email exists, a reset link has been sent"}