from pydantic import BaseModel


class OrderInfoResponse(BaseModel):
    order_id: int
    from_currency: str
    to_currency: str
    amount_sold: float
    exchange_rate: float
    amount_to_receive: float
    status: str

    class Config:
        orm_mode = True