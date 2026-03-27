from models import ChatMessage
from sqlalchemy.orm import Session

def save_chat_message(db: Session, user_id: int, role: str, content: str):
    msg = ChatMessage(
        user_id=user_id,
        role=role,
        content=content
    )
    db.add(msg)
    db.commit()
    db.refresh(msg)
    return msg