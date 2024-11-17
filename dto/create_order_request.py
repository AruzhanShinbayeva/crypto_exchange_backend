from pydantic import BaseModel


class CreateOrderRequest(BaseModel):
    user_id: int
    from_currency: str
    to_currency: str
    value: float
    exchange_rate: float