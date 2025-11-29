from services.amadeus_service import search_flights

flights = search_flights("DEL", "BOM", "2025-12-20")
print(flights)
