from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from database import get_db
from models import User
from jose import jwt, JWTError
from passlib.context import CryptContext
from auth_schema import ResetPasswordRequest
import os
from dotenv import load_dotenv


load_dotenv()
router = APIRouter()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

SECRET_KEY=os.getenv("SECRET_KEY")
ALGORITHM="HS256"
@router.post("/reset-password")
def reset_password(data: ResetPasswordRequest, db: Session = Depends(get_db)):

    try:
        payload = jwt.decode(data.token, SECRET_KEY, algorithms=[ALGORITHM])

        email = payload.get("sub")
        token_type = payload.get("type")

        if token_type != "password_reset":
            raise Exception()

    except JWTError:
        return {"error": "Invalid or expired token"}

    user = db.query(User).filter(User.email == email).first()

    if not user:
        return {"error": "User not found"}

    hashed_password = pwd_context.hash(data.new_password)

    user.password_hash = hashed_password
    db.commit()

    return {"message": "Password reset successful"}