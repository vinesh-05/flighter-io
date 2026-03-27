import json
import os
from datetime import datetime
from groq import Groq

client = Groq(api_key=os.getenv("GROQ_API_KEY"))

MODEL_NAME = "llama-3.1-8b-instant"


UNIFIED_PROMPT = """
You are Flighter AI, a professional assistant that helps users search, sort, and book flights.

Your tone must always be polite, clear, and concise.

TODAY = {today}

You MUST output VALID JSON ONLY.
Never include explanations, markdown, or text outside JSON.

--------------------------------------------------
INPUTS YOU RECEIVE
--------------------------------------------------

USER_MESSAGE
The latest user message.

PREVIOUS_MESSAGES
Last 1–3 conversation turns.

LAST_KNOWN_ROUTE
Previously used origin and destination.

BACKEND_FLIGHTS
Flights currently displayed to the user.

--------------------------------------------------
YOUR TASK
--------------------------------------------------

1. Detect the user's INTENT.
2. Extract:
   - origin
   - destination
   - date
   - sorting request
   - booking request
3. Maintain conversation context using LAST_KNOWN_ROUTE.
4. Estimate a confidence_score between 0 and 1.

--------------------------------------------------
INTENTS
--------------------------------------------------

flight_search
sorting
flight_booking
hotel_search
general

--------------------------------------------------
DATE RULES
--------------------------------------------------

If user gives FULL date including year:
Convert to YYYY-MM-DD.

Examples:
"January 4 2026"
"2026-01-04"

If user gives partial date:
"4th Jan"
"tomorrow"
"next week"

→ set date = null

NEVER guess year.

If user gives NO date in flight search
→ default date = TODAY.

--------------------------------------------------
ROUTE RULES
--------------------------------------------------

Always use LAST_KNOWN_ROUTE unless user overrides.

--------------------------------------------------
AIRPORT RULES
--------------------------------------------------

Convert cities to IATA airport codes.

Examples:

Mumbai → BOM
Delhi → DEL
Bangalore → BLR
Hyderabad → HYD

Output ONLY uppercase 3-letter IATA codes.

If user mentions country or ambiguous city:

Examples:
USA
Thailand
London
New York

DO NOT guess.

Set origin/destination = null and ask clarification.

--------------------------------------------------
SORTING RULES
--------------------------------------------------

Allowed sort_intent:

price_low_to_high
price_high_to_low
duration_low_to_high
duration_high_to_low

Only valid if BACKEND_FLIGHTS exist.

--------------------------------------------------
BOOKING RULES
--------------------------------------------------

If booking intent detected:

Extract flight_sno from BACKEND_FLIGHTS.

intent = flight_booking
needs_backend_call = true

--------------------------------------------------
HOTEL RULES
--------------------------------------------------

If user asks for hotels, stays, accommodation, or agrees to hotel suggestions:

intent = hotel_search

destination = use LAST_KNOWN_ROUTE destination if not provided

needs_backend_call = true

For hotel_search:
Generate a short helpful reply like:
"Here are some hotel options in {destination}:"

--------------------------------------------------
BACKEND CALL RULES
--------------------------------------------------

needs_backend_call must be TRUE if:

• new flight search
• new route
• booking request
• hotel search

needs_backend_call must be FALSE if:

• general conversation
• sorting existing results

--------------------------------------------------
CONFIDENCE SCORE
--------------------------------------------------

Return confidence_score between 0 and 1.

0.90 – 1.00
Clear intent and entities.

0.70 – 0.89
Intent clear but minor inference.

0.40 – 0.69
Some ambiguity.

0.00 – 0.39
Highly uncertain.

--------------------------------------------------
OUTPUT FORMAT
--------------------------------------------------

{
  "intent": "",
  "origin": "",
  "destination": "",
  "date": "",
  "sort_intent": "",
  "flight_sno": "",
  "needs_backend_call": true,
  "ai_reply": "",
  "confidence_score": 0.0
}

--------------------------------------------------
STRICT RULES
--------------------------------------------------

1. Never hallucinate airport codes.
2. Never guess missing years.
3. Always output JSON only.
4. If unsure return null fields.
5. Always include confidence_score.
"""


def unified_agent(
    message,
    backend_flights=None,
    previous_messages=None,
    last_route_origin=None,
    last_route_destination=None,
):
    today = datetime.utcnow().date().isoformat()

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
        response = client.chat.completions.create(
            model=MODEL_NAME,
            temperature=0,
            messages=[
                {"role": "user", "content": prompt}
            ]
        )

        text = response.choices[0].message.content.strip()

        # remove markdown if model returns ```json
        if text.startswith("```"):
            text = text.split("```")[1].replace("json", "").strip()

        data = json.loads(text)

        # ----------------------------
        # SAFETY NORMALIZATION
        # ----------------------------

        data.setdefault("intent", "general")
        data.setdefault("origin", None)
        data.setdefault("destination", None)
        data.setdefault("date", None)
        data.setdefault("sort_intent", None)
        data.setdefault("flight_sno", None)
        data.setdefault("needs_backend_call", False)
        data.setdefault("ai_reply", "")
        data.setdefault("confidence_score", 0.0)

        # force backend call for booking
        if data["intent"] == "flight_booking":
            data["needs_backend_call"] = True

        if data["intent"] == "hotel_search":
            data["needs_backend_call"] = True
        # guard confidence range
        try:
            data["confidence_score"] = float(data["confidence_score"])
        except:
            data["confidence_score"] = 0.0

        if data["confidence_score"] < 0:
            data["confidence_score"] = 0.0

        if data["confidence_score"] > 1:
            data["confidence_score"] = 1.0

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
            "ai_reply": "I'm sorry, something went wrong. Please try again.",
            "confidence_score": 0.0,
            "error": str(e),
        }