from jose import jwt
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv

load_dotenv()
SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = "HS256"

def create_password_reset_token(email: str):

    payload = {
        "sub": email,
        "type": "password_reset",
        "exp": datetime.utcnow() + timedelta(minutes=15)
    }

    token = jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

    return token