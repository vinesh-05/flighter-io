def sort_flights(message, flights):
    msg = message.lower()

    # PRICE
    if "price" in msg or "cheapest" in msg or "cost" in msg:
        return sorted(
            flights,
            key=lambda x: float(str(x["price"]).split()[0]),
            reverse=("desc" in msg or "high" in msg or "expensive" in msg)
        )

    # DURATION
    if "duration" in msg or "fastest" in msg or "time taken" in msg:
        def to_minutes(d):
            h, m = d.split(":")
            return int(h) * 60 + int(m)

        return sorted(
            flights,
            key=lambda x: to_minutes(x["duration"]),
            reverse=("desc" in msg or "long" in msg or "slow" in msg)
        )

    # DEPARTURE
    if "departure" in msg or "take off" in msg:
        return sorted(
            flights,
            key=lambda x: x["departure_time"],
            reverse=("desc" in msg or "late" in msg)
        )

    # ARRIVAL
    if "arrival" in msg or "reach" in msg:
        return sorted(
            flights,
            key=lambda x: x["arrival_time"],
            reverse=("desc" in msg or "late" in msg)
        )

    return flights
