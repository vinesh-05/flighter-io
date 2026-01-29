from pydantic import BaseModel

class CreateStripeSessionRequest(BaseModel):
    booking_id: int
