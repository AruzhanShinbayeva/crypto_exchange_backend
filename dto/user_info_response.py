from pydantic import BaseModel


class WalletInfo(BaseModel):
    currency: str
    value: float


class UserInfoResponse(BaseModel):
    user_address: str
    wallets: list[WalletInfo]