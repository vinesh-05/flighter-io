# services/pricing_service.py

class PricingService:
    ADULT_MULTIPLIER = 1.0
    CHILD_MULTIPLIER = 0.75
    INFANT_MULTIPLIER = 0.10

    @classmethod
    def calculate_total(
        cls,
        base_price: float,
        adults: int,
        children: int,
        infants: int,
        trip_type: str
    ) -> float:
        if adults < 1:
            raise ValueError("At least one adult is required")

        if infants > adults:
            raise ValueError("Infants cannot exceed adults")

        total = (
            (adults * base_price * cls.ADULT_MULTIPLIER)
            + (children * base_price * cls.CHILD_MULTIPLIER)
            + (infants * base_price * cls.INFANT_MULTIPLIER)
        )

        if trip_type == "round_trip":
            total *= 2

        return round(total, 2)
