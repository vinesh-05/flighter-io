import google.generativeai as genai
import os
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()

genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))

model = genai.GenerativeModel(
    "gemini-2.5-flash-lite",
    generation_config={
        "response_mime_type": "application/json",
    }
)

def extract_intent(message: str):
    """
    Extract intent from natural text.
    Date is computed RELATIVE TO today's date (from the backend),
    so 'tomorrow' etc are always correct.
    """

    # 👇 Use your server's real current date as the reference
    today = datetime.now().date().isoformat()

    prompt = f"""
    You are an advanced Intent Classification Agent for a Flight-Booking AI system.

    Today's date is {today}.
    The user message is: "{message}"

    Your job:
    1. Understand the user's message deeply — even if it is vague, indirect, slang-filled, or incomplete.
    2. Infer hidden meaning and context like a human.
    3. Output a JSON object containing:
    {
        "intent": "<one of: flight_search, flight_booking, sorting, greeting, smalltalk, other>"
    }

    General Rules:
    - Be extremely accurate.
    - Do not hallucinate flights, details, cities, or dates.
    - Focus ONLY on the intent, not the content details.

    INTENT DEFINITIONS:

    1. **flight_search**
    Trigger when the user:
    - asks to book a flight
    - asks to check flights
    - mentions source, destination, or travel dates
    - uses phrases like: "show me flights", "find flights", "I want to go to ___", 
        "looking for flights", "tomorrow to Delhi", etc.
    - expresses exploring options: "what flights are available", "any cheap flights?"

    2. **flight_booking**
    Trigger when:
    - the user selects or confirms a specific option
    - says things like:
        "book the third flight",
        "go ahead with the cheapest one",
        "confirm number 2",
        "proceed with that flight",
        “checkout this one”
    - OR expresses final commitment: "yes I want this flight", "confirm this", etc.

    3. **sorting**
    Trigger when:
    - user wants sorting by price, duration, or time:
        "sort by cheapest",
        "show quickest first",
        "show longest flight first",
        "arrange from lowest to highest"
    - Comparison-based requests: 
        "which is the cheapest?", "show the fast ones first"

    4. **greeting**
    Trigger when:
    - user says "hi", "hello", "good morning", "hey"
    - simple courtesy messages.

    5. **smalltalk**
    Trigger when:
    - user asks non-flight personal questions:
        "how are you?",
        "what can you do?",
        "tell me a joke",
        "who created you?"

    6. **other**
    Trigger when:
    - message doesn't match any of the above categories.

    Additional Intelligence Rules:
    - Understand indirect or conversational phrasing.
    (Example: “I’m thinking to fly to Mumbai this weekend” → flight_search)
    - Understand multi-step reasoning.
    (Example: “Which one is shorter? Show that first” → sorting)
    - If the message contains both flight search and sorting:
    → sorting should take priority.
    - If the user expresses desire to finalize something:
    → flight_booking.
    - Detect intent even if the user does not use exact keywords.

    Output ONLY valid JSON with the field: "intent".
    No explanations. No natural language. Only JSON.
    """
    try:
        response = model.generate_content(prompt)

        import json
        return json.loads(response.text)

    except Exception as e:
        return {"error": f"Extraction failed: {str(e)}"}
