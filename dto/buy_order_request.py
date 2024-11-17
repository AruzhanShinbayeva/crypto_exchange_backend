from pydantic import BaseModel


class OrderBuyRequest(BaseModel):
    order_id: int
    amount_to_buy: float
    user_id: int
