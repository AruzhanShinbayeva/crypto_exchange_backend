from pydantic import BaseModel, constr


class UserCreateRequest(BaseModel):
    user_id: int
    password: constr(min_length=8)
