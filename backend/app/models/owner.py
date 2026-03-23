from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class OwnerBase(BaseModel):
    unit_id: str                  # z.B. "WE-001"
    name: str                     # Vollständiger Name
    iban: Optional[str] = None    # IBAN des Eigentümers
    bic: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    monthly_hausgeld: float = 0.0  # Monatlicher Hausgeldbetrag
    notes: Optional[str] = None


class OwnerCreate(OwnerBase):
    pass


class OwnerUpdate(BaseModel):
    name: Optional[str] = None
    iban: Optional[str] = None
    bic: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    monthly_hausgeld: Optional[float] = None
    notes: Optional[str] = None


class Owner(OwnerBase):
    id: str = Field(alias="_id")

    class Config:
        populate_by_name = True
