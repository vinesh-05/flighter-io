from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from datetime import datetime
from database import get_db
from models import Conversation
from auth import get_current_user
from services.main_agent import unified_agent
from services.amadeus_service import search_flights
from services.sorter_agent import sort_flights
from routers.flights import select_flight
from pydantic import BaseModel
import json

router = APIRouter(prefix="/chat", tags=["Chat"])


class ChatRequest(BaseModel):
    message: str


def get_last_flight_turn(db: Session, user_id: int):
    return (
        db.query(Conversation)
        .filter(Conversation.user_id == user_id, Conversation.flight_context.isnot(None))
        .order_by(Conversation.timestamp.desc())
        .first()
    )


@router.post("/message")
async def chat_with_bot(
    request: ChatRequest,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    message = request.message

    # Load last flights from DB if available
    last_chat = get_last_flight_turn(db, current_user.id)
    last_flights = []

    if last_chat:
        try:
            raw = json.loads(last_chat.flight_context)
            last_flights = raw if isinstance(raw, list) else [raw]
        except:
            last_flights = []

    # 🔥 ONE GEMINI CALL ONLY
    details = unified_agent(message, last_flights)
    print(details)
    intent = details.get("intent", "general")
    origin = details.get("origin")
    destination = details.get("destination")
    date = details.get("date") or datetime.now().date().isoformat()
    sort_intent = details.get("sort_intent")
    flight_sno = details.get("flight_sno")
    ai_reply = details.get("ai_reply")
    needs_backend = details.get("needs_backend_call", False)

    flights = last_flights

    # -------------------------------------------
    # 1️⃣ FLIGHT SEARCH
    # -------------------------------------------
    if intent == "flight_search" and needs_backend:
        if not origin or not destination:
            reply = ai_reply  # LLM already explained missing details
        else:
            flights = await search_flights(origin, destination, date)
            print(flights)
            reply = ai_reply  # LLM crafted a friendly message

        # save chat
        new_chat = Conversation(
            user_id=current_user.id,
            message=message,
            response=json.dumps(reply),
            intent=intent,
            timestamp=datetime.utcnow(),
            flight_context=json.dumps(flights)
        )
        db.add(new_chat)
        db.commit()

        return {
            "bot_response": reply,
            "intent": intent,
            "flights": flights,
            "origin": origin,
            "destination": destination,
            "date": date
        }

    # -------------------------------------------
    # 2️⃣ SORTING
    # -------------------------------------------
    if intent == "sorting" and needs_backend:
        sorted_flights = sort_flights(sort_intent, flights)
        reply = ai_reply

        new_chat = Conversation(
            user_id=current_user.id,
            message=message,
            response=json.dumps(reply),
            intent=intent,
            timestamp=datetime.utcnow(),
            flight_context=json.dumps(sorted_flights)
        )
        db.add(new_chat)
        db.commit()

        return {
            "bot_response": reply,
            "intent": intent,
            "flights": sorted_flights
        }

    # -------------------------------------------
    # 3️⃣ BOOKING
    # -------------------------------------------
    if intent == "flight_booking" and needs_backend:
        flight = next((f for f in flights if f["id"] == str(flight_sno)), None)

        if flight:
            reply = select_flight(
                str(flight_sno),
                flight["airline"],
                float(flight["price"].replace("INR", "").strip()),
                date,
                flight["from"],
                flight["to"],
                flight["departure_time"],
                flight["arrival_time"],
                db,
                current_user
            )
        else:
            reply = "I could not find that flight number."

        new_chat = Conversation(
            user_id=current_user.id,
            message=message,
            response=json.dumps(reply),
            intent=intent,
            timestamp=datetime.utcnow(),
            flight_context=json.dumps(flight or {})
        )
        db.add(new_chat)
        db.commit()

        return {
            "bot_response": reply,
            "intent": intent
        }

    # -------------------------------------------
    # 4️⃣ GENERAL CHAT (NO BACKEND WORK)
    # -------------------------------------------
    reply = ai_reply

    new_chat = Conversation(
        user_id=current_user.id,
        message=message,
        response=reply,
        intent=intent,
        timestamp=datetime.utcnow(),
        flight_context=None
    )
    db.add(new_chat)
    db.commit()

    return {
        "bot_response": reply,
        "intent": intent
    }
