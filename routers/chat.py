from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from datetime import datetime
from database import get_db
from models import Conversation
from models import FlightBooking
from auth import get_current_user
from services.main_agent import unified_agent
from services.amadeus_service import search_flights
from services.sorter_agent import sort_flights
from routers.flights import select_flight
from pydantic import BaseModel
import json
from datetime import date as dt_date

def ensure_future_date(date_str: str) -> str:
    d = dt_date.fromisoformat(date_str)
    today = dt_date.today()

    if d < today:
        return d.replace(year=today.year + 1).isoformat()

    return d.isoformat()

router = APIRouter(prefix="/chat", tags=["Chat"])


class ChatRequest(BaseModel):
    message: str
def normalize_response(reply):
    return reply if isinstance(reply, str) else json.dumps(reply)


def get_last_three_messages(db: Session, user_id: int):
    rows = (
        db.query(Conversation)
        .filter(Conversation.user_id == user_id)
        .order_by(Conversation.timestamp.desc())
        .limit(3)
        .all()
    )
    history = []
    for r in reversed(rows):
        history.append({"user": r.message, "bot": r.response})
    return history


@router.post("/message")
async def chat_with_bot(
    request: ChatRequest,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    message = request.message.strip()

    # -----------------------------  
    # Load short-term message memory  
    # -----------------------------
    previous_messages = get_last_three_messages(db, current_user.id)

    # -----------------------------  
    # Load last route  
    # -----------------------------
    
    last_route_origin = None
    last_route_destination = None
    last_route_date=None

    # -----------------------------  
    # Load last flights from DB  
    # -----------------------------
    last_chat = (
        db.query(Conversation)
        .filter(Conversation.user_id == current_user.id,
                Conversation.flight_context.isnot(None))
        .order_by(Conversation.timestamp.desc())
        .first()
    )

    flights = []
    if last_chat:
        try:
            flights = json.loads(last_chat.flight_context)
            if isinstance(flights, dict):
                flights = [flights]
        except:
            flights = []

    # -----------------------------  
    # Call Unified AI Agent  
    # -----------------------------
    details = unified_agent(
        message,
        backend_flights=flights,
        previous_messages=previous_messages,
        last_route_origin=last_route_origin,
        last_route_destination=last_route_destination
    )
    print(details)

    intent = details.get("intent", "general")
    origin = details.get("origin")
    destination = details.get("destination")
    date = details.get("date")
    if date:
        date = ensure_future_date(date)
    else:
        date = datetime.now().date().isoformat()
    sort_intent = details.get("sort_intent")
    flight_sno = details.get("flight_sno")
    ai_reply = details.get("ai_reply")
    needs_backend = details.get("needs_backend_call", False)

    # -----------------------------  
    # ⚠ CASE: Destination is country → ask clarification  
    # -----------------------------
    if intent == "flight_search" and destination is None and "airport" in ai_reply.lower():
        new_chat = Conversation(
            user_id=current_user.id,
            message=message,
            response=json.dumps(ai_reply),
            intent="clarification_needed",
            timestamp=datetime.utcnow(),
            flight_context=None
        )
        db.add(new_chat)
        db.commit()

        return {"bot_response": ai_reply, "intent": "clarification_needed"}

    # -----------------------------  
    # 1️⃣ FLIGHT SEARCH  
    # -----------------------------
    if intent == "flight_search" and needs_backend:

        # RESET: old routes, flights, booking state
        

        # If missing fields → return AI reply only
        if not origin or not destination:
            reply = ai_reply
            flights = []
        else:
            flights = await search_flights(origin, destination, date)
            reply = ai_reply

        # Save new search results
        new_chat = Conversation(
            user_id=current_user.id,
            message=message,
            response=normalize_response(reply),
            intent="flight_search",
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

    # -----------------------------  
    # 2️⃣ SORTING  
    # -----------------------------
    if intent == "sorting" and needs_backend:

        sorted_flights = sort_flights(sort_intent, flights)
        reply = ai_reply

        new_chat = Conversation(
            user_id=current_user.id,
            message=message,
            response=normalize_response(reply),
            intent=intent,
            timestamp=datetime.utcnow(),
            flight_context=json.dumps(sorted_flights)
        )
        db.add(new_chat)
        db.commit()

        # Save messages

        return {"bot_response": reply, "intent": intent, "flights": sorted_flights}

    # -----------------------------  
    # 3️⃣ BOOKING  
    # -----------------------------
    if intent == "flight_booking" and needs_backend:

        # Fail-safe
        if isinstance(flights, dict):
            flights = [flights]

        flight = next((f for f in flights if f.get("id") == str(flight_sno)), None)

        if not flight:
            reply = (
                "I couldn’t locate that flight number in the latest search results. "
                "Please select a flight from the currently displayed list."
            )
        else:
            reply = select_flight(
                str(flight_sno),
                flight["airline"],
                float(flight["price"].replace("INR", "").strip()),
                last_route_date or date,
                flight["from"],
                flight["to"],
                flight["departure_time"],
                flight["arrival_time"],
                db,
                current_user
            )

        new_chat = Conversation(
            user_id=current_user.id,
            message=message,
            response=normalize_response(reply),
            intent="flight_booking",
            timestamp=datetime.utcnow(),
            flight_context=json.dumps(flights)  # keep full list
        )
        db.add(new_chat)
        db.commit()

        return {"bot_response": reply, "intent": intent}
        
    # -----------------------------  
    # 4️⃣ GENERAL  
    # -----------------------------
    new_chat = Conversation(
        user_id=current_user.id,
        message=message,
        response=normalize_response(ai_reply),
        intent=intent,
        timestamp=datetime.utcnow(),
        flight_context=None
    )
    db.add(new_chat)
    db.commit()

    return {"bot_response": ai_reply, "intent": intent}

@router.get("/history")
def get_chat_history(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    conversations = (
        db.query(Conversation)
        .filter(Conversation.user_id == current_user.id)
        .order_by(Conversation.timestamp.asc())
        .all()
    )
    routes=(
        db.query(FlightBooking)
        .filter(FlightBooking.user_id == current_user.id)
        .order_by(FlightBooking.timestamp.asc())
        .all()
    )

    messages = []

    for c in conversations:
        # User message
        if c.message:
            messages.append({
                "sender": "user",
                "text": c.message
            })

        # Bot reply
        if c.response:
            messages.append({
                "sender": "bot",
                "text": c.response if isinstance(c.response, str) else json.dumps(c.response)
            })

        # ✅ FIXED flight replay
        if c.intent == "flight_search" and c.flight_context:
            try:
                flights = json.loads(c.flight_context)
                if not isinstance(flights, list) or len(flights) == 0:
                    flights = []
            except Exception:
                flights = []

            if flights:
                origin = flights[0].get("from")
                destination = flights[0].get("to")
            else:
                origin = None
                destination = None

            messages.append({
                "sender": "bot",
                "text": "FLIGHT_DATA_JSON::" + json.dumps({
                    "origin": origin,
                    "destination": destination,
                    "date": None,   # date not stored, fine
                    "flights": flights
                })
            })

    return messages
