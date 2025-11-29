from models import Conversation
from database import get_db
from sqlalchemy.orm import Session


def get_conversation_history(db: Session, user_id: int):
    history = (
        db.query(Conversation)
        .filter(Conversation.user_id == user_id)
        .order_by(Conversation.timestamp.desc())
        .all()
    )