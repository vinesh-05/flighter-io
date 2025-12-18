import json
from datetime import datetime
import os
import google.generativeai as genai

genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
model = genai.GenerativeModel("gemini-2.5-flash-lite")

UNIFIED_PROMPT = """
You are a professional AI assistant that helps users search, sort, and book flights.
Your tone must always remain polite, clear, and concise.

TODAY = {today}

You MUST output valid JSON only.

You receive:
- USER_MESSAGE
- PREVIOUS_MESSAGES (last 1–3 turns)
- LAST_KNOWN_ROUTE (origin & destination)
- BACKEND_FLIGHTS (latest displayed flights)

Your job:
1. Detect the user's intent.
2. Extract ORIGIN, DESTINATION, DATE.
3. Understand when user is referring to the latest search results.
4. If user gives a NEW ROUTE → mark needs_backend_call = true.
5. If sorting → extract sort_intent.
6. If booking → extract flight_sno.
7. If user mentions a COUNTRY (Thailand, USA, Europe, etc.) → DO NOT guess airport. Ask politely.
8. Always follow the last known route unless user overrides it.

INTENTS:
- "flight_search"
- "sorting"
- "flight_booking"
- "general"

SORT INTENTS:
- price_low_to_high
- price_high_to_low
- duration_low_to_high
- duration_high_to_low

If you are unsure about origin/destination, set them null.

Your JSON format:
{
  "intent": "",
  "origin": "",
  "destination": "",
  "date": "",
  "sort_intent": "",
  "flight_sno": "",
  "needs_backend_call": true/false,
  "ai_reply": ""
}
"""

def unified_agent(message, backend_flights=None, previous_messages=None,
                  last_route_origin=None, last_route_destination=None):

    today = datetime.now().date().isoformat()

    flights_text = json.dumps(backend_flights or [])
    history_text = json.dumps(previous_messages or [])

    prompt = UNIFIED_PROMPT.replace("{today}", today) + f"""
USER_MESSAGE: "{message}"

LAST_KNOWN_ROUTE:
origin: "{last_route_origin}"
destination: "{last_route_destination}"

PREVIOUS_MESSAGES:
{history_text}

BACKEND_FLIGHTS:
{flights_text}
"""

    try:
        response = model.generate_content([{"role": "user", "parts": [prompt]}])
        text = response.text.strip()

        if text.startswith("```"):
            text = text.split("```")[1].replace("json", "").strip()

        data = json.loads(text)
        # FORCE backend call for booking
        if data.get("intent") == "flight_booking":
            data["needs_backend_call"] = True

        return data

    except Exception as e:
        return {
            "intent": "general",
            "origin": None,
            "destination": None,
            "date": None,
            "sort_intent": None,
            "flight_sno": None,
            "needs_backend_call": False,
            "ai_reply": "I'm sorry. There's an error.",
            "error": str(e),
        }
