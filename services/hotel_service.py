import requests
import json
import re
from dotenv import load_dotenv
import os
from groq import Groq
load_dotenv()

TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")
client = Groq(api_key=os.getenv("GROQ_API_KEY"))
MODEL_NAME = "llama-3.1-8b-instant"
# 🔍 Step 1: Tavily Search
def tavily_search(city: str):
    query = f"top hotels in {city} with names, ratings, price per nightsite:booking.com OR site:agoda.com OR site:makemytrip.com{city} hotels list"

    response = requests.post(
        "https://api.tavily.com/search",
        json={
            "api_key": TAVILY_API_KEY,
            "query": query,
            "search_depth": "basic"
        }
    )

    data = response.json()
    results=data.get("results",[])
    print("results",results)
    return results


# 🧠 Step 2: LLM Structuring
def extract_hotels_with_llm(results, city: str):

    filtered_results = [
    r for r in results
    if city.lower() in (r.get("title", "") + r.get("content", "")).lower()
    ]
    use_results = filtered_results if filtered_results else results
    context = "\n\n".join([
    f"Title: {r.get('title')}\nContent: {r.get('content')}\nURL: {r.get('url')}"
    for r in use_results if r.get("content")
    ])
    prompt = f"""
    You are a strict data extraction engine.

    TASK:
    Extract hotel data for the city: {city}

    You MUST return ONLY valid JSON.
    NO explanations. NO extra text.

    --------------------------------
    EXAMPLE INPUT DATA:
    [
    {{
        "url": "https://www.makemytrip.com/hotels/fabhotel_pushpa_grand-details-hyderabad.html",
        "title": "FabHotel Pushpa Grand BOOK Hyderabad Hotel - MakeMyTrip",
        "content": "Most Booked Hotels in Hyderabad ; Lemon Tree Premier HITEC City Hyderabad · ₹ 8,487. ₹ 6,381 ; Lemon Tree Hotel Gachibowli · ₹ 8,332. ₹ 6,265 ; Red Fox by Lemon Tree",
        "score": 0.73
    }},
    {{
        "url": "https://www.makemytrip.com/hotels/hotel_shubham_palace_karmanghat-details-hyderabad.html",
        "title": "HOTEL SHUBHAM PALACE KARMANGHAT BOOK Hyderabad Hotel",
        "content": "Most Booked Hotels in Hyderabad ; Lemon Tree Premier HITEC City Hyderabad · ₹ 12,399. ₹ 9,579 ; Lemon Tree Hotel Gachibowli · ₹ 14,737. ₹ 11,385 ; Red Fox by Lemon Tree",
        "score": 0.71
    }}
    ]

    --------------------------------
    EXAMPLE OUTPUT:
    HOTEL_DATA_JSON::{{
    "city": "Hyderabad",
    "hotels": [
        {{
        "name": "Lemon Tree Premier HITEC City Hyderabad",
        "price_per_night": 6381,
        "rating": 4.2,
        "booking_link": "https://www.makemytrip.com/hotels/fabhotel_pushpa_grand-details-hyderabad.html"
        }},
        {{
        "name": "Lemon Tree Hotel Gachibowli",
        "price_per_night": 6265,
        "rating": 4.1,
        "booking_link": "https://www.makemytrip.com/hotels/hotel_shubham_palace_karmanghat-details-hyderabad.html"
        }}
    ]
    }}

    --------------------------------
    NOW YOUR TASK:

    Extract hotels for: {city}

    STRICT OUTPUT FORMAT:
    HOTEL_DATA_JSON::{{
    "city": "{city}",
    "hotels": [
        {{
        "name": "string",
        "price_per_night": number,
        "rating": number,
        "booking_link": "string"
        }}
    ]
    }}

    RULES:
    - If the price is in any other currency(ex: dollar, yen, etc) convert and return the INR(Indian Rupee) value of it only.
    - ONLY return name, price_per_night, rating, booking_link
    - Extract hotel names from "content"
    - Extract prices (remove ₹ and commas, return only number)
    - booking_link MUST be taken from "url"
    - rating → if not present, estimate between 3.5–5.0
    - Return 3–5 hotels
    - DO NOT return empty JSON
    - DO NOT add extra keys
    - DO NOT add text before/after JSON
    - ONLY include hotels located in {city}
    - If hotel is from a different city, IGNORE it
    - If DATA does not contain enough hotels for {city}, still generate realistic hotels for {city}
    --------------------------------
    DATA:
    {context}
    """

    response = client.chat.completions.create(
        model=MODEL_NAME,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.2
    )

    content = response.choices[0].message.content
    print("content",content)
    return clean_output(content)

# 🧹 Step 3: Clean Output

def clean_output(text: str):
    try:
        json_part = text.split("HOTEL_DATA_JSON::")[-1].strip()
        return json.loads(json_part)
    except Exception as e:
        print("❌ JSON parse failed:", e)
        return {}


def get_hotels(city: str):
    print(f"🔍 Searching hotels for: {city}")

    results = tavily_search(city)
    print("🧾 Tavily sample:", results[:])

    output = extract_hotels_with_llm(results, city)
    print("🧠 LLM Output:", output)

    return output