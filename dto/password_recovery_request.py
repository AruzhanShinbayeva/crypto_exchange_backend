from pydantic import BaseModel, constr


class PasswordRecoveryRequest(BaseModel):
    user_id: int
    mnemonic_phrase: constr(min_length=12)
    new_password: constr(min_length=8)
