from datetime import datetime

SORT_KEYWORDS = {
    "cheapest": "sort_price_cheap",
    "budget": "sort_price_cheap",
    "low cost": "sort_price_cheap",
    "least expensive": "sort_price_cheap",

    "most expensive": "sort_price_exp",
    "costliest": "sort_price_exp",

    "fastest": "sort_duration_fast",
    "quickest": "sort_duration_fast",
    "shortest": "sort_duration_fast",

    "longest": "sort_duration_slow",
    "slowest": "sort_duration_slow",

    "earliest": "sort_dep_asc",
    "first flight": "sort_dep_asc",
    "morning": "sort_dep_asc",

    "latest": "sort_dep_desc",
    "night": "sort_dep_desc",
    "last flight": "sort_dep_desc"
}

def detect_sort_intent(message: str):
    msg = message.lower()
    for keyword, intent in SORT_KEYWORDS.items():
        if keyword in msg:
            return intent
    return None

def time_to_obj(t):
    return datetime.strptime(t, "%H:%M").time()

def sort_flights(sort_intent, flights):
    if not sort_intent:
        return flights

    # PRICE
    if sort_intent in ['sort_price_cheap', 'sort_price_exp']:
        return sorted(
            flights,
            key=lambda x: float(str(x["price"]).split()[0]),
            reverse=(sort_intent == 'sort_price_exp')
        )

    # DURATION
    if sort_intent in ['sort_duration_fast', 'sort_duration_slow']:
        def to_minutes(d):
            h, m = d.split(":")
            return int(h) * 60 + int(m)
        return sorted(
            flights,
            key=lambda x: to_minutes(x["duration"]),
            reverse=(sort_intent == 'sort_duration_slow')
        )

    # DEPARTURE TIME
    if sort_intent in ['sort_dep_asc', 'sort_dep_desc']:
        return sorted(
            flights,
            key=lambda x: time_to_obj(x["departure_time"]),
            reverse=(sort_intent == 'sort_dep_desc')
        )

    return flights
