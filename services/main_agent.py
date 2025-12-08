import json
from datetime import datetime
import os
import google.generativeai as genai
from dotenv import load_dotenv



genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
model = genai.GenerativeModel("gemini-2.5-flash-lite")
UNIFIED_PROMPT = """
You are the ONLY AI agent controlling a flight booking chatbot.
You must do everything in ONE response.

TODAY = {today}

Your job:
1. Understand the user message.
2. Detect intent.
3. Extract flight search details.
4. Extract sorting request.
5. Extract flight booking choice.
6. If needed: use the flights provided by backend and write a natural reply.
7. Produce the FINAL reply text (no second LLM call).

INPUT YOU RECEIVE:
- user message
- backend flights list (if any)

YOU MUST OUTPUT ONLY JSON:

{
  "intent": "...",
  "origin": "...",
  "destination": "...",
  "date": "...",
  "sort_intent": "...",
  "flight_sno": "...",
  "needs_backend_call": true/false,
  "ai_reply": "THE FINAL REPLY USER SHOULD SEE"
}

RULES:
- If user asks for flights: intent = "flight_search" → needs_backend_call = true
- If city names are given for source and destination (e.g. Bangalore, Delhi, Mumbai), map
    them to their primary IATA codes (BLR, DEL, BOM, etc).
- If you are unsure about a field, set it to null.
- If sorting: intent = "sorting" → needs_backend_call = true
- If booking: intent = "flight_booking" → needs_backend_call = true
- If general conversation: intent = "general" → needs_backend_call = false
- If needs_backend_call = true: DO NOT hallucinate flights, backend will provide real flights
- ai_reply MUST be final message to user
"""

def unified_agent(message, backend_flights=None):
    today = datetime.now().date().isoformat()
    flights_text = json.dumps(backend_flights or [])

    prompt = UNIFIED_PROMPT.replace("{today}", today) + f"""
USER MESSAGE: "{message}"

BACKEND_FLIGHTS:
{flights_text}
"""

    try:
        response = model.generate_content([
        {"role": "user", "parts": [prompt]}
        ])

        response_text = response.text.strip()

    # Clean ```
        if response_text.startswith("```"):
            response_text = response_text.split("```")[1].replace("json", "").strip()

    # Parse cleaned JSON
        data = json.loads(response_text)

        return data   # <-- RETURN CLEANED DATA

    except Exception as e:
        return {
        "intent": "general",
        "needs_backend_call": False,
        "ai_reply": "I’m here! Could you rephrase that?",
        "error": str(e)
        }
