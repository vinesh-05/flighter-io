from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from database import get_db
import models
from auth import hash_password, verify_password, create_access_token
from pydantic import BaseModel
from sqlalchemy import or_

router = APIRouter(prefix="/users", tags=["Users"])
class UserCreate(BaseModel):
    username: str
    email: str
    password: str
@router.post("/signup")
def signup(request: UserCreate, db: Session = Depends(get_db)):
    existing_user = db.query(models.User).filter(models.User.username == request.username).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Username already exists")

    hashed_pw = hash_password(request.password)
    new_user = models.User(username=request.username,email=request.email, password_hash=hashed_pw)
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return {"message": "User created successfully", "user_id": new_user.id}


class UserLogin(BaseModel):
    identifier: str
    password: str


@router.post("/login")
def login(request: UserLogin, db: Session = Depends(get_db)):
    user = (
        db.query(models.User)
        .filter(
            or_(
                models.User.username == request.identifier,
                models.User.email == request.identifier
            )
        )
        .first()
    )

    if not user or not verify_password(request.password, user.password_hash):
        raise HTTPException(status_code=400, detail="Invalid username or password")

    token = create_access_token(
        data={
            "sub": str(user.id),     # MUST be string
            "email": user.email
        }
    )
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "id": user.id,
            "name": user.username,
            "email": user.email
        }
    }
