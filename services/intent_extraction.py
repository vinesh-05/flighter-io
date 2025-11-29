import google.generativeai as genai
import os
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()

genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))

model = genai.GenerativeModel(
    "gemini-2.5-flash",
    generation_config={
        "response_mime_type": "application/json",
    }
)

def extract_flight_details(message: str):
    """
    Extract origin, destination, date, time, passengers from natural text.
    Date is computed RELATIVE TO today's date (from the backend),
    so 'tomorrow' etc are always correct.
    """

    # 👇 Use your server's real current date as the reference
    today = datetime.now().date().isoformat()

    prompt = f"""
    You are a flight booking parser.

    Today's date is {today}.
    The user message is: "{message}"

    Task:
    Extract these fields and return a JSON object with EXACTLY these keys:
    - origin: IATA airport code (like DEL, BLR, BOM) or null
    - destination: IATA airport code or null
    - date: a concrete calendar date in YYYY-MM-DD format or null
    - time: "morning", "afternoon", "evening", "night", or null
    - passengers: integer (default 1 if not mentioned)

    Rules:
    - When the user says things like "tomorrow", "day after tomorrow",
      "next Monday", "next Friday", etc., you MUST compute the exact
      calendar date RELATIVE TO today's date {today}. Do NOT assume 
      any other 'today' than the one explicitly given.
    - If city names are given (e.g. Bangalore, Delhi, Mumbai), map
      them to their primary IATA codes (BLR, DEL, BOM, etc).
    - If you are unsure about a field, set it to null.
    """

    try:
        response = model.generate_content(prompt)

        import json
        return json.loads(response.text)

    except Exception as e:
        return {"error": f"Extraction failed: {str(e)}"}
