import os
import httpx
from dotenv import load_dotenv
from datetime import datetime
from services.redis_client import redis_client
import json
import re

load_dotenv()

AMADEUS_CLIENT_ID = os.getenv("AMADEUS_API_KEY")
AMADEUS_CLIENT_SECRET = os.getenv("AMADEUS_API_SECRET")

TOKEN_URL = "https://test.api.amadeus.com/v1/security/oauth2/token"
FLIGHT_SEARCH_URL = "https://test.api.amadeus.com/v2/shopping/flight-offers"


async def get_access_token():
    async with httpx.AsyncClient() as client:
        response = await client.post(
            TOKEN_URL,
            data={
                "grant_type": "client_credentials",
                "client_id": AMADEUS_CLIENT_ID,
                "client_secret": AMADEUS_CLIENT_SECRET,
            }
        )
        return response.json()["access_token"]


def convert_eur_to_inr(amount_eur: float):
    return round(amount_eur * 90, 2)


def format_time(time_str):
    try:
        dt = datetime.fromisoformat(time_str)
        return dt.strftime("%H:%M")
    except:
        return time_str


def format_duration(duration: str):
    h = re.search(r"(\d+)H", duration)
    m = re.search(r"(\d+)M", duration)
    hours = int(h.group(1)) if h else 0
    minutes = int(m.group(1)) if m else 0
    return f"{hours:02d}:{minutes:02d}"


async def search_flights(origin: str, destination: str, departure_date: str):
    # --------------------------
    # 🔥 Redis Cache (2 minutes)
    # --------------------------
    cache_key = f"flights:{origin}:{destination}:{departure_date}"

    cached = await redis_client.get(cache_key)
    if cached:
        print("⚡ Redis Cache Hit → Returning cached flights")
        return json.loads(cached)

    print("🛫 Redis Cache MISS → Calling Amadeus API")

    # --------------------------
    # 🔐 Get new access token
    # --------------------------
    token = await get_access_token()

    headers = {"Authorization": f"Bearer {token}"}

    params = {
        "originLocationCode": origin,
        "destinationLocationCode": destination,
        "departureDate": departure_date,
        "adults": 1,
        "max": 10
    }

    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.get(
            FLIGHT_SEARCH_URL, params=params, headers=headers
        )

    if response.status_code != 200:
        return {"error": response.text}

    data = response.json()

    flights = []
    AIRLINE_NAMES = {
        "AI": "Air India", "6E": "IndiGo", "UK": "Vistara",
        "SG": "SpiceJet", "G8": "Go First", "LH": "Lufthansa",
        "QR": "Qatar Airways", "EK": "Emirates", "BA": "British Airways",
        "SQ": "Singapore Airlines", "CX": "Cathay Pacific"
    }

    # --------------------------
    # ✈️ Extract & format flights
    # --------------------------
    for offer in data.get("data", [])[:5]:
        itinerary = offer["itineraries"][0]
        first_segment = itinerary["segments"][0]
        last_segment = itinerary["segments"][-1]

        airline_code = offer["validatingAirlineCodes"][0]
        airline_name = AIRLINE_NAMES.get(airline_code, airline_code)

        price_eur = float(offer["price"]["total"])
        price_inr = convert_eur_to_inr(price_eur)

        flights.append({
            "id": offer["id"],
            "airline": airline_name,
            "price": f"{price_inr} INR",
            "duration": format_duration(itinerary["duration"]),
            "from": first_segment["departure"]["iataCode"],
            "to": last_segment["arrival"]["iataCode"],
            "departure_time": format_time(first_segment["departure"]["at"]),
            "arrival_time": format_time(last_segment["arrival"]["at"])
        })

    # --------------------------
    # 🧠 Save to Redis Cache
    # --------------------------
    await redis_client.set(cache_key, json.dumps(flights), ex=600)

    return flights
