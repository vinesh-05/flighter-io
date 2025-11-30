from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from datetime import datetime
from database import get_db
from models import Conversation
from auth import get_current_user
from services.gemini_service import ask_gemini, rewrite_flight_response
from utils.sorting import sort_flights
from services.amadeus_service import search_flights
from services.intent_extraction import extract_flight_details
from pydantic import BaseModel
from routers.flights import select_flight
import json
router = APIRouter(prefix="/chat", tags=["Chat"])


class ChatRequest(BaseModel):
    message: str

def get_conversation_history(db: Session, user_id: int, limit: int = 20):
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
def get_last_flight_turn(db: Session, user_id: int):
    """
    Get the most recent conversation turn that has flight_context saved.
    """
    return (
        db.query(Conversation)
        .filter(Conversation.user_id == user_id, Conversation.flight_context.isnot(None))
        .order_by(Conversation.timestamp.desc())
        .first()
    )



@router.post("/message")
def chat_with_bot(
    request: ChatRequest,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    message = request.message
    msg_lower = message.lower()
    intent = "general"

    flights=[]
    origin=None
    destination=None
    date=None
    flight_sno=None
    last_chat = (
    db.query(Conversation)
    .filter(Conversation.user_id == current_user.id)
    .order_by(Conversation.timestamp.desc())
    .first()
    )
    
    if last_chat and last_chat.flight_context:
        flights = last_chat.flight_context
        # print(type(flights))
        # origin_list=list({item['from'] for item in flights})
        # origin="".join(origin_list)
        # print(type(origin))
        # destination_list=list({item['to'] for item in flights})
        # destination="".join(destination_list)
        # print(type(destination))
        origin = next(iter({item["from"] for item in flights}), None)
        destination = next(iter({item["to"] for item in flights}), None)


    

    # Detect possible flight booking intent
    booking_keywords=['booking','book','checkout','payment','pay','select']
    flight_keywords = ["flight","flights", "show", "ticket", "del", "blr", "mumbai", "bangalore", "goa"]
    sort_keywords=['sort','arrange','ascending','descending','asc','desc','order']
    details=extract_flight_details(message)
    print(details)
    if "error" in details:
        reply = "Sorry, I couldn't understand the flight details. Could you rephrase?"
    else:
        origin = details.get("origin")
        # print(origin)
        # print(type(origin))
        destination = details.get("destination")
        date = details.get("date") or datetime.now().date().isoformat()
        flight_sno=details.get("flight_sno")
        if not origin or not destination:
            # Ask Gemini to respond humanly about missing information
            reply = rewrite_flight_response(details, [])
        else:
        # Fetch flights
            flights = search_flights(origin, destination, date)
            print(flights)
            # print(type(flights))
        # reply = rewrite_flight_response(details, flights)
        
    if any(k in msg_lower for k in flight_keywords):
        intent = "flight_search"
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
        origin = next(iter({f["from"] for f in flights}), None)
        destination = next(iter({f["to"] for f in flights}), None)

        sorted_flights = sort_flights(message, flights)
        reply = rewrite_flight_response(
            {"origin": origin, "destination": destination, "date": date},
            sorted_flights
        )
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
        return {
            "bot_response": reply,
            "intent": intent,
            "origin": origin,
            "destination": destination,
            "date": date,
            "flights": sort_flights(message,flights)
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


        # If details missing
    elif any(b in msg_lower for b in booking_keywords):
        flight_sno_str=str(flight_sno)
        intent = 'booking'
        origin = next(iter({f["from"] for f in flights}), None)
        destination = next(iter({f["to"] for f in flights}), None)
        # sorted_flights = sort_flights(message, flights)
        flight = next((f for f in flights if f["id"] ==flight_sno_str), None)

        if flight:
            airline = flight["airline"]
            clean_price = flight["price"].replace("INR", "").strip()
            price = float(clean_price)
            duration = flight["duration"]
            from_city = flight["from"]
            to_city = flight["to"]
            departure_time = flight["departure_time"]
            arrival_time = flight["arrival_time"]
            # Corrected line: Pass the full current_user object, not its ID
            reply=select_flight(flight_sno_str,airline,price,date,from_city,to_city,departure_time,arrival_time,db,current_user)
            # print(airline, price, duration, from_city, to_city, departure_time, arrival_time)
        # reply = rewrite_flight_response(
        #     {"origin": origin, "destination": destination, "date": date, "flight_sno": flight_sno_str},
        #     flights
        # )
        
        new_chat = Conversation(
            user_id=current_user.id,
            message=message,
            response=json.dumps(reply),
            intent=intent,
            timestamp=datetime.utcnow(),
            flight_context=flight
        )
        db.add(new_chat)
        db.commit()
        # return {
        #     "bot_response": reply,
        #     "intent": intent,
        #     "origin": origin,
        #     "destination": destination,
        #     "date": date,
        #     "flights": flights
        # }
        # if details missing
        new_chat = Conversation(
            user_id=current_user.id,
            message=message,
            response=json.dumps(reply),
            intent=intent,
            timestamp=datetime.utcnow(),
            flight_context=flight
        )
        db.add(new_chat)
        db.commit()

        return {"bot_response": reply, "intent": intent}

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
