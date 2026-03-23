from pydantic import BaseModel, Field
from typing import Optional


class AccountBase(BaseModel):
    account_number: str           # Kontonummer z.B. "6023543"
    iban: str                     # Vollständige IBAN
    name: str                     # Bezeichnung des Kontos
    account_type: str             # "betriebskonto" | "rücklagenkonto"
    bank_name: Optional[str] = None
    current_balance: float = 0.0
    currency: str = "EUR"


class AccountCreate(AccountBase):
    pass


class AccountUpdate(BaseModel):
    name: Optional[str] = None
    current_balance: Optional[float] = None
    bank_name: Optional[str] = None


class Account(AccountBase):
    id: str = Field(alias="_id")

    class Config:
        populate_by_name = True
