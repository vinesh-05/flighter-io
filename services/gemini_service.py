import google.generativeai as genai
import os
from dotenv import load_dotenv

load_dotenv()

# Configure the Gemini client
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))

# Load the model (use gemini-1.5-flash for speed or gemini-1.5-pro for depth)
model = genai.GenerativeModel("gemini-2.5-flash")

def ask_gemini(message: str, history=None):
    """
    Send user message + conversation history to Gemini.
    Includes date grounding, history, and correct roles (user/model).
    """
    try:
        from datetime import datetime
        today = datetime.now().strftime("%Y-%m-%d")

        if history is None:
            history = []

        formatted = []

        # SYSTEM INSTRUCTIONS → use role = "model"
        system_prompt = f"""
        Today's date is {today}.
        When the user asks for today's date, 'current date', or relative terms
        like 'tomorrow', ALWAYS use {today} as the reference date.
        """
        formatted.append({
            "role": "model",
            "parts": [system_prompt]
        })

        # Add past conversation history (roles: user / assistant → must convert assistant → model)
        for h in history:
            gemini_role = "user" if h["role"] == "user" else "model"
            formatted.append({
                "role": gemini_role,
                "parts": [h["content"]]
            })

        # Add the latest user message
        formatted.append({
            "role": "user",
            "parts": [message]
        })

        # Gemini call
        response = model.generate_content(formatted)
        return response.text

    except Exception as e:
        return f"Error while contacting Gemini: {str(e)}"

def rewrite_flight_response(details, flights):
    """
    Gemini generates a natural-sounding human reply 
    using REAL flights provided by backend and also sorts the flights when user asks to sort.
    """
    message = f"""
    You are an AI assistant helping the user search flights and sort the flights by price or duration or on any parameter which the user asks you to do.

    The extracted flight details:
    {details}

    The actual flights returned by the server:
    {flights}

    SORTING RULES:
    - If the user asks you to sort the list of flights in {flights} by any parameter like price or duration, you have to return the sorted flights back.
    IMPORTANT RULES:
    - Do NOT invent or hallucinate flights.
    - ONLY describe the flights provided.
    - Be friendly and conversational.
    - If flights exist, summarize them nicely.
    - If no flights exist, apologize politely and suggest alternatives.
    - If airport not detected, ask user naturally to rephrase.

    Now generate a natural and friendly reply to the user.
    """

    try:
        response = model.generate_content(message)
        return response.text
    except Exception as e:
        return f"Error generating AI reply: {str(e)}"

def sort_flights(message, flights):
    msg = message.lower()

    # PRICE
    if "price" in msg or "cheapest" in msg or "cost" in msg:
        return sorted(
            flights,
            key=lambda x: float(str(x["price"]).split()[0]),
            reverse=("desc" in msg or "high" in msg or "expensive" in msg)
        )

    # DURATION
    if "duration" in msg or "fastest" in msg or "time taken" in msg:
        def to_minutes(d):
            h, m = d.split(":")
            return int(h) * 60 + int(m)

        return sorted(
            flights,
            key=lambda x: to_minutes(x["duration"]),
            reverse=("desc" in msg or "long" in msg or "slow" in msg)
        )

    # DEPARTURE
    if "departure" in msg or "take off" in msg:
        return sorted(
            flights,
            key=lambda x: x["departure_time"],
            reverse=("desc" in msg or "late" in msg)
        )

    # ARRIVAL
    if "arrival" in msg or "reach" in msg:
        return sorted(
            flights,
            key=lambda x: x["arrival_time"],
            reverse=("desc" in msg or "late" in msg)
        )

    return flights
