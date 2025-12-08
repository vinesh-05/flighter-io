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
    You are an intent detection agent.

    Today's date is {today}.
    The user message is: "{message}"

    Task:
    Extract the intent of the user based on their text message and return the user's intent.
    "intent"

    Rules:
    - When the user says "I want to book a flight", then since initially they have to be shown the list of flights, let the intent be 'flight_search'.
    - When the user says something like "show me flights from source to destination tomorrow", let intent be 'flight_search'.
    - When the user says "book the third flight" or "proceeed with the third one" or "checkout with the third one" or sentences with similar context then let intent be 'flight_booking'.
    - When the user says "sort the flights from cheapest to most expensive" or "show the cheapest flight first" or "show the longest flight first" or "show the quickest flight first" or sentences with similar context let intent be 'sorting'.

    """

    try:
        response = model.generate_content(prompt)

        import json
        return json.loads(response.text)

    except Exception as e:
        return {"error": f"Extraction failed: {str(e)}"}
