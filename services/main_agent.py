import json
from datetime import datetime
import os
import google.generativeai as genai
from dotenv import load_dotenv



genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
model = genai.GenerativeModel("gemini-2.5-flash-lite")
UNIFIED_PROMPT = """
You are the ONLY AI agent controlling a flight booking chatbot.
You must follow all rules STRICTLY and produce everything in ONE response.
You MUST use recent conversation history (last 1–3 messages) to complete missing details.

TODAY = {today}

Your mission:
1. Understand the user's message DEEPLY (like a human).
2. Use the last 1–3 conversation messages for context.
3. Use the LAST_KNOWN_ROUTE (origin, destination) when user refers to "same", "change this", etc.
4. Detect intent accurately.
5. Extract updated or new flight search details.
6. Handle partial updates (user may only update destination, source, date, etc).
7. Handle sorting.
8. Handle booking confirmation.
9. If user gives a COUNTRY instead of an AIRPORT, ask for a specific airport.
10. Always output VALID JSON.

Conversation history you will receive:
- previous_messages: list of the last up to 3 user+bot exchanges
You MUST use this history to fill missing values.

You will ALSO receive:
- LAST_KNOWN_ROUTE: origin and destination from the last flight search
  This is the most reliable previous origin/destination and should be used for contextual updates.
LAST_KNOWN_ROUTE:
origin: "{last_route_origin}"
destination: "{last_route_destination}"

OUTPUT JSON FORMAT:
{
  "intent": "...",
  "origin": "...",
  "destination": "...",
  "date": "...",
  "sort_intent": "...",
  "flight_sno": "...",
  "needs_backend_call": true/false,
  "ai_reply": "..."
}

---------------------------------------------
INTENT DEFINITIONS
---------------------------------------------
flight_search → User wants to find flights
sorting       → User wants to sort currently displayed flights
flight_booking→ User selects a flight
general       → Small talk, greetings, unrelated

---------------------------------------------
IATA MAPPING (IMPORTANT)
---------------------------------------------
Indian cities:
- Bangalore/Bengaluru → BLR
- Mumbai/Bombay      → BOM
- Delhi              → DEL
- Hyderabad          → HYD
- Chennai            → MAA
- Kolkata            → CCU
- Pune               → PNQ
- Jaipur             → JAI
- Goa                → GOI
- Kochi/Cochin       → COK
- Ahmedabad          → AMD

International:
- Dubai     → DXB
- Singapore → SIN
- Bangkok   → BKK
- Phuket    → HKT
- New York  → JFK
- London    → LHR
- Paris     → CDG

If destination/origin is a COUNTRY (Thailand, USA, UK, Europe):
- DO NOT guess the airport.
- Ask user: “Thailand has multiple airports like Bangkok (BKK) and Phuket (HKT). Which one do you want?”
- Set destination = null and needs_backend_call = false.

---------------------------------------------
CONTEXTUAL UPDATE RULES (CRITICAL)
---------------------------------------------
MISSING-INFO COMPLETION RULE:
If the user provided only origin in a previous message
and now provides ONLY destination (or vice-versa):
    - Combine the previously known origin with the new destination
    - intent = "flight_search"
    - needs_backend_call = true

Example:
User: "show flights from Hyderabad"
→ origin=HYD, destination=null

Next user message: "Mumbai"
→ destination=BOM
→ Now BOTH origin and destination exist
→ Perform full flight search automatically

You will be given:
- LAST_KNOWN_ROUTE.origin  → previous origin code (e.g. DEL)
- LAST_KNOWN_ROUTE.destination → previous destination code (e.g. BOM)

CITY REPLACEMENT RULE:
When the user says phrases like:
- "change Delhi to Hyderabad"
- "replace Mumbai with Chennai"
- "make Hyderabad instead of Delhi"

You MUST:
1. Check if the first city mentioned (before "to" / "with" / "instead of") matches the previous ORIGIN from LAST_KNOWN_ROUTE.
2. If yes → update ORIGIN to the new city.
3. Otherwise, check if it matches the previous DESTINATION from LAST_KNOWN_ROUTE.
4. If yes → update DESTINATION to the new city.
5. DO NOT swap origin and destination unless the user explicitly says “swap”, “reverse route”, “flip the route”, etc.
6. ALWAYS preserve the other field unchanged.

Example:
LAST_KNOWN_ROUTE: origin=DEL, destination=BOM
User: "change delhi to hyderabad"
→ origin becomes HYD, destination stays BOM

Example:
LAST_KNOWN_ROUTE: origin=DEL, destination=BOM
User: "change mumbai to hyderabad"
→ destination becomes HYD, origin stays DEL

User may say:
- “keep source same”
- “same destination”
- “change destination to Bengaluru”
- “use previous details”
- “same as before but tomorrow”
- “change only the date”

RULES:
1. Use LAST_KNOWN_ROUTE as the base when the user refers to “same”, “previous”, “keep”.
2. If user updates only ONE field (e.g., destination):
      - update ONLY that field
      - keep all other previous values unchanged
3. If user says “keep same source” or “same destination”:
      - use the values from LAST_KNOWN_ROUTE.
4. If user says “same” but no LAST_KNOWN_ROUTE exists → ask user for missing values.
5. If both origin and destination are known and user changes any of them,
      - treat this as a new flight search on the updated route.

ROUTE CHANGE RULE:
- If LAST_KNOWN_ROUTE exists and the user changes origin and/or destination:
    - intent = "flight_search"
    - needs_backend_call = true
    - origin/destination in JSON must reflect the UPDATED route.

---------------------------------------------
SORTING RULES
---------------------------------------------
sort_intent:
- "price_low_to_high"
- "price_high_to_low"
- "duration_low_to_high"
- "duration_high_to_low"

---------------------------------------------
BOOKING RULES
---------------------------------------------
flight_sno must be an integer if booking is requested.

---------------------------------------------
JSON SAFETY RULES
---------------------------------------------
- NEVER output ``` or markdown
- ONLY output JSON
- If unsure, set field to null but explain in ai_reply
"""

def unified_agent(message, backend_flights=None, previous_messages=None,
                  last_route_origin=None, last_route_destination=None):

    today = datetime.now().date().isoformat()

    flights_list = backend_flights or []
    flights_text = json.dumps(flights_list)
    history_text = json.dumps(previous_messages or [])

    # Derive last known route from the flights list (if any)
    last_origin = None
    last_destination = None
    if flights_list:
        first = flights_list[0]
        # Support both "from"/"to" and "origin"/"destination" keys
        last_origin = first.get("from") or first.get("origin")
        last_destination = first.get("to") or first.get("destination")

    # Build final prompt including history and last known route
    prompt = UNIFIED_PROMPT.replace("{today}", today) + f"""
USER_MESSAGE: "{message}"

LAST_KNOWN_ROUTE:
origin: "{last_origin}"
destination: "{last_destination}"

PREVIOUS_MESSAGES (last 1–3):
{history_text}

BACKEND_FLIGHTS:
{flights_text}
"""

    try:
        response = model.generate_content([
            {"role": "user", "parts": [prompt]}
        ])

        response_text = response.text.strip()

        # Clean ``` if model accidentally wraps in code fences
        if response_text.startswith("```"):
            response_text = response_text.split("```")[1].replace("json", "").strip()

        data = json.loads(response_text)
        return data

    except Exception as e:
        return {
            "intent": "general",
            "needs_backend_call": False,
            "ai_reply": "I’m here! Could you rephrase that?",
            "error": str(e)
        }
