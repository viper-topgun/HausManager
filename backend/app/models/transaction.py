from pydantic import BaseModel, Field
from typing import Optional
from datetime import date


class TransactionBase(BaseModel):
    account_id: str               # Referenz auf Account._id
    account_number: str           # Kontonummer (6023543 oder 6023550)
    booking_date: date
    value_date: date
    amount: float
    currency: str = "EUR"
    counterparty_name: Optional[str] = None
    counterparty_iban: Optional[str] = None
    counterparty_bic: Optional[str] = None
    purpose: str = ""             # VWZ1..14 zusammengefasst
    booking_text: str = ""        # BuchText
    category: Optional[str] = None
    subcategory: Optional[str] = None
    haupttyp: Optional[str] = None    # HausManager Hauptkategorie (Wasserkosten, Nebenkosten, …)
    untertyp: Optional[str] = None    # HausManager Unterkategorie
    transaction_type: Optional[str] = None  # "hausgeld" | "ausgabe" | "rücklage" | "sonstiges"
    owner_unit: Optional[str] = None        # WE-001 etc. wenn erkannt
    seq_no: Optional[int] = None            # Lfd.Nr
    starmoney_id: Optional[int] = None      # ID aus StarMoney


class TransactionCreate(TransactionBase):
    pass


class Transaction(TransactionBase):
    id: str = Field(alias="_id")

    class Config:
        populate_by_name = True
