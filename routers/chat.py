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
from services.redis_client import redis_client
from pydantic import BaseModel
import json

router = APIRouter(prefix="/chat", tags=["Chat"])


class ChatRequest(BaseModel):
    message: str


def get_last_flight_turn(db: Session, user_id: int):
    """Returns the LAST saved conversation containing flight_context."""
    return (
        db.query(Conversation)
        .filter(Conversation.user_id == user_id, Conversation.flight_context.isnot(None))
        .order_by(Conversation.timestamp.desc())
        .first()
    )


def get_last_three_messages(db: Session, user_id: int):
    """Return last 1–3 user+bot exchanges for context memory."""
    rows = (
        db.query(Conversation)
        .filter(Conversation.user_id == user_id)
        .order_by(Conversation.timestamp.desc())
        .limit(3)
        .all()
    )

    history = []
    for r in reversed(rows):  # oldest → newest
        history.append({
            "user": r.message,
            "bot": r.response
        })

    return history


@router.post("/message")
async def chat_with_bot(
    request: ChatRequest,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    message = request.message.strip()

    # ---------------------------------------------------------
    # 🔥 STEP 1 — LOAD LAST 1–3 MESSAGES (Redis first)
    # ---------------------------------------------------------
    redis_history = await redis_client.get(f"user:{current_user.id}:last_messages")

    if redis_history:
        previous_messages = json.loads(redis_history)
    else:
        previous_messages = get_last_three_messages(db, current_user.id)

    # ---------------------------------------------------------
    # 🔥 STEP 2 — LOAD LAST SAVED FLIGHT CONTEXT
    # ---------------------------------------------------------
    last_chat = get_last_flight_turn(db, current_user.id)
    last_flights = []

    if last_chat:
        try:
            raw = json.loads(last_chat.flight_context)
            last_flights = raw if isinstance(raw, list) else [raw]
        except:
            last_flights = []

    # ---------------------------------------------------------
    # 🔥 STEP 3 — LOAD LAST ROUTE FROM REDIS
    # ---------------------------------------------------------
    redis_route = await redis_client.get(f"user:{current_user.id}:last_route")

    if redis_route:
        redis_route = json.loads(redis_route)
        last_route_origin = redis_route.get("origin")
        last_route_destination = redis_route.get("destination")
    else:
        last_route_origin = None
        last_route_destination = None

    # ---------------------------------------------------------
    # 🔥 STEP 4 — FALLBACK FROM PREVIOUS FLIGHTS OR MESSAGES
    # ---------------------------------------------------------
    if last_flights:
        first = last_flights[0]
        last_route_origin = last_route_origin or first.get("from") or first.get("origin")
        last_route_destination = last_route_destination or first.get("to") or first.get("destination")

    if not last_route_origin or not last_route_destination:
        for msg in reversed(previous_messages):
            try:
                bot = json.loads(msg["bot"])
                if not last_route_origin and bot.get("origin"):
                    last_route_origin = bot["origin"]
                if not last_route_destination and bot.get("destination"):
                    last_route_destination = bot["destination"]
            except:
                pass

    # ---------------------------------------------------------
    # 🔥 STEP 5 — ONE GEMINI CALL (SUPREME AGENT)
    # ---------------------------------------------------------
    details = unified_agent(
        message,
        backend_flights=last_flights,
        previous_messages=previous_messages,
        last_route_origin=last_route_origin,
        last_route_destination=last_route_destination
    )

    print("\nAI DETAILS →", details, "\n")

    # Extract details
    intent = details.get("intent", "general")
    origin = details.get("origin")
    destination = details.get("destination")
    date = details.get("date") or datetime.now().date().isoformat()
    sort_intent = details.get("sort_intent")
    flight_sno = details.get("flight_sno")
    ai_reply = details.get("ai_reply")
    needs_backend = details.get("needs_backend_call", False)

    flights = last_flights

    # ---------------------------------------------------------
    # ⚠️ SPECIAL CASE: COUNTRY DESTINATION
    # ---------------------------------------------------------
    if intent == "flight_search" and origin and destination is None:
        reply = ai_reply

        # Save conversation
        new_chat = Conversation(
            user_id=current_user.id,
            message=message,
            response=json.dumps(reply),
            intent="clarification_needed",
            timestamp=datetime.utcnow(),
            flight_context=None
        )
        db.add(new_chat)
        db.commit()

        # Update only messages in Redis
        await redis_client.set(
            f"user:{current_user.id}:last_messages",
            json.dumps(previous_messages + [{"user": message, "bot": reply}]),
            ex=3600
        )

        return {
            "bot_response": reply,
            "intent": "clarification_needed"
        }

    # ---------------------------------------------------------
    # 1️⃣ FLIGHT SEARCH
    # ---------------------------------------------------------
    if intent == "flight_search" and needs_backend:

        if not origin or not destination:
            reply = ai_reply
        else:
            flights = await search_flights(origin, destination, date)
            reply = ai_reply

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

        # Save new route ONLY if valid
        if origin and destination:
            await redis_client.set(
                f"user:{current_user.id}:last_route",
                json.dumps({"origin": origin, "destination": destination}),
                ex=3600
            )

        # Always save messages
        await redis_client.set(
            f"user:{current_user.id}:last_messages",
            json.dumps(previous_messages + [{"user": message, "bot": reply}]),
            ex=3600
        )

        return {
            "bot_response": reply,
            "intent": intent,
            "flights": flights,
            "origin": origin,
            "destination": destination,
            "date": date
        }

    # ---------------------------------------------------------
    # 2️⃣ SORTING
    # ---------------------------------------------------------
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

        # Save route if valid
        if origin and destination:
            await redis_client.set(
                f"user:{current_user.id}:last_route",
                json.dumps({"origin": origin, "destination": destination}),
                ex=3600
            )

        # Save messages
        await redis_client.set(
            f"user:{current_user.id}:last_messages",
            json.dumps(previous_messages + [{"user": message, "bot": reply}]),
            ex=3600
        )

        return {
            "bot_response": reply,
            "intent": intent,
            "flights": sorted_flights
        }

    # ---------------------------------------------------------
    # 3️⃣ BOOKING
    # ---------------------------------------------------------
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

        # Save route if valid
        if origin and destination:
            await redis_client.set(
                f"user:{current_user.id}:last_route",
                json.dumps({"origin": origin, "destination": destination}),
                ex=3600
            )

        # Save message memory
        await redis_client.set(
            f"user:{current_user.id}:last_messages",
            json.dumps(previous_messages + [{"user": message, "bot": reply}]),
            ex=3600
        )

        return {
            "bot_response": reply,
            "intent": intent
        }

    # ---------------------------------------------------------
    # 4️⃣ GENERAL / SMALLTALK
    # ---------------------------------------------------------
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

    # Save route if valid
    if origin and destination:
        await redis_client.set(
            f"user:{current_user.id}:last_route",
            json.dumps({"origin": origin, "destination": destination}),
            ex=3600
        )

    # Save last messages
    await redis_client.set(
        f"user:{current_user.id}:last_messages",
        json.dumps(previous_messages + [{"user": message, "bot": reply}]),
        ex=3600
    )

    return {
        "bot_response": reply,
        "intent": intent
    }
