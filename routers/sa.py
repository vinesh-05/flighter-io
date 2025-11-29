from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from datetime import datetime
from database import get_db
from models import Conversation
from auth import get_current_user
from services.gemini_service import ask_gemini, rewrite_flight_response,sort_flights
from services.amadeus_service import search_flights
from services.intent_extraction import extract_flight_details
from pydantic import BaseModel

router = APIRouter(prefix="/chat", tags=["Chat"])


class ChatRequest(BaseModel):
    message: str

def get_conversation_history(db: Session, user_id: int, limit: int = 10):
    history = (
        db.query(Conversation)
        .filter(Conversation.user_id == user_id)
        .order_by(Conversation.timestamp.desc())
        .limit(limit)
        .all()
    )

    # Convert DB objects → Gemini format (or OpenAI format)
    history.reverse()  # oldest → newest

    messages = []
    for h in history:
        messages.append({"role": "user", "content": h.message})
        messages.append({"role": "assistant", "content": h.response})

    return messages


@router.post("/message")
def chat_with_bot(
    request: ChatRequest,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    message = request.message
    msg_lower = message.lower()
    intent = "general"

    # Detect possible flight booking intent
    flight_keywords = ["flight", "book", "ticket", "del", "blr", "mumbai", "bangalore", "goa"]
    sort_keywords=['sort','arrange','ascending','descending','asc','desc','order']
    details=extract_flight_details(message)
    print(details)
    if "error" in details:
        reply = "Sorry, I couldn't understand the flight details. Could you rephrase?"
    else:
        origin = details.get("origin")
        destination = details.get("destination")
        date = details.get("date") or datetime.now().date().isoformat()
        if not origin or not destination:
            # Ask Gemini to respond humanly about missing information
            reply = rewrite_flight_response(details, [])
        else:
        # Fetch flights
            flights = search_flights(origin, destination, date)
            print(flights)
            print(type(flights))
        # reply = rewrite_flight_response(details, flights)
        
    if any(k in msg_lower for k in flight_keywords):
        intent = "flight_booking"
        reply=rewrite_flight_response(details,flights)
        new_chat = Conversation(
        user_id=current_user.id,
        message=message,
        response=reply,
        intent=intent,
        timestamp=datetime.utcnow(),
        flight_context=flights
        )
        db.add(new_chat)
        db.commit()

        return {
            "bot_response": reply,
            "intent": intent,
            "origin": origin,
            "destination": destination,
            "date": date,
            "flights": flights
        }
        #if details missing
        new_chat = Conversation(
            user_id=current_user.id,
            message=message,
            response=reply,
            intent=intent,
            timestamp=datetime.utcnow(),
            flight_context=flights
        )
        db.add(new_chat)
        db.commit()

        return {"bot_response": reply, "intent": intent}

    elif any(sort in msg_lower for sort in sort_keywords):
        intent = 'sorting'
        reply=rewrite_flight_response(details,sort_flights(message,flights))
        new_chat = Conversation(
            user_id=current_user.id,
            message=message,
            response=reply,
            intent=intent,
            timestamp=datetime.utcnow(),
            flight_context=flights
        )
        db.add(new_chat)
        db.commit()
        return {
            "bot_response": reply,
            "intent": intent,
            "origin": origin,
            "destination": destination,
            "date": date,
            "flights": flights
        }
        #if details missing
        new_chat = Conversation(
            user_id=current_user.id,
            message=message,
            response=reply,
            intent=intent,
            timestamp=datetime.utcnow(),
            flight_context=sort_flights(message,flights)
        )
        db.add(new_chat)
        db.commit()

        return {"bot_response": reply, "intent": intent}
        # Extract structured flight details using Gemini
        # details = extract_flight_details(message)
        # print(details)
        # if "error" in details:
        #     reply = "Sorry, I couldn't understand the flight details. Could you rephrase?"
        # else:
        #     origin = details.get("origin")
        #     destination = details.get("destination")
        #     date = details.get("date") or datetime.now().date().isoformat()

        #     if not origin or not destination:
        #         # Ask Gemini to respond humanly about missing information
        #         reply = rewrite_flight_response(details, [])
        #     else:
        #         # Fetch flights
        #         flights = search_flights(origin, destination, date)
        #         print(flights)
        #         print(type(flights))
        #         reply = rewrite_flight_response(details, flights)

                # Save in DB


        # If details missing

    # General chat handled by Gemini
    history = get_conversation_history(db, current_user.id, limit=10)

    ai_reply = ask_gemini(
        message=message,
        history=history
    )


    new_chat = Conversation(
        user_id=current_user.id,
        message=message,
        response=ai_reply,
        intent=intent,
        timestamp=datetime.utcnow()
    )
    db.add(new_chat)
    db.commit()

    return {
        "bot_response": ai_reply,
        "intent": intent
    }
    # sort_keywords=['sort','ascending','descending','arrange','asc','desc']
    # if any(x in msg_lower for x in sort_keywords):
    #     intent='sorting'
        