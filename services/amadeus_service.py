from amadeus import Client, ResponseError
import os
from dotenv import load_dotenv
from datetime import datetime
import re

# Load environment variables
load_dotenv()

# Initialize Amadeus client
amadeus = Client(
    client_id=os.getenv("AMADEUS_API_KEY"),
    client_secret=os.getenv("AMADEUS_API_SECRET")
)

def convert_eur_to_inr(amount_eur: float):
    INR_RATE = 90  # Approx conversion rate
    return round(amount_eur * INR_RATE, 2)


def format_time(time_str):
    """
    Convert 2025-12-20T09:30:00 → 09:30
    """
    try:
        dt = datetime.fromisoformat(time_str)
        return dt.strftime("%H:%M")
    except:
        return time_str


def format_duration(duration: str):
    """
    Convert PT2H5M → 02:05
    """
    hours = 0
    minutes = 0

    h = re.search(r"(\d+)H", duration)
    m = re.search(r"(\d+)M", duration)

    if h:
        hours = int(h.group(1))
    if m:
        minutes = int(m.group(1))

    return f"{hours:02d}:{minutes:02d}"


def search_flights(origin: str, destination: str, departure_date: str):
    """
    Fetch top 5 flight options and return formatted output.
    """
    try:
        response = amadeus.shopping.flight_offers_search.get(
            originLocationCode=origin,
            destinationLocationCode=destination,
            departureDate=departure_date,
            adults=1
        )

        flights = []

        AIRLINE_NAMES = {
            "AI": "Air India",
            "6E": "IndiGo",
            "UK": "Vistara",
            "SG": "SpiceJet",
            "G8": "Go First",
            "LH": "Lufthansa",
            "QR": "Qatar Airways",
            "EK": "Emirates",
            "BA": "British Airways",
            "SQ": "Singapore Airlines",
            "CX": "Cathay Pacific"
        }

        for offer in response.data[:5]:
            try:
                itinerary = offer["itineraries"][0]
                first_segment = itinerary["segments"][0]
                last_segment = itinerary["segments"][-1]

                airline_code = offer["validatingAirlineCodes"][0]
                airline_name = AIRLINE_NAMES.get(airline_code, airline_code)

                # Price conversion
                price_eur = float(offer["price"]["total"])
                price_inr = convert_eur_to_inr(price_eur)

                # Duration formatting
                duration = format_duration(itinerary["duration"])

                # Added Offer ID for booking selection later
                offer_id = offer["id"]

                flights.append({
                    "id": offer_id,  # ← NEW FIELD
                    "airline": airline_name,
                    "price": f"{price_inr} INR",
                    "duration": duration,
                    "from": first_segment["departure"]["iataCode"],
                    "to": last_segment["arrival"]["iataCode"],
                    "departure_time": format_time(first_segment["departure"]["at"]),
                    "arrival_time": format_time(last_segment["arrival"]["at"])
                })

            except KeyError:
                continue

        return flights

    except ResponseError as error:
        return {"error": str(error)}
