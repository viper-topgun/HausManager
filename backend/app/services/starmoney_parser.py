"""
StarMoney Deluxe CSV/TXT import parser.

The StarMoney export is a semicolon-separated file with German number
formatting (comma as decimal separator) and date format DD.MM.YYYY.
First row is the header.
"""

import csv
import io
import re
from datetime import date, datetime
from typing import Iterator

from ..models.transaction import TransactionCreate

# Known WE-unit patterns extracted from purpose text
_WE_PATTERN = re.compile(r"\bWE[-\s]?(\d{3})\b", re.IGNORECASE)

# Mapping IBAN → unit_id (populated from DB at runtime, here as fallback seed)
KNOWN_OWNER_IBANS: dict[str, str] = {
    "DE38700915000002620090": "WE-001",
    "DE51700915000003638065": "WE-002",
    "DE94721690800000052930": "WE-003",
    "DE19721516500000914267": "WE-004",
}


def _parse_decimal(value: str) -> float:
    """Convert German decimal string '1.234,56' → float 1234.56"""
    if not value or value.strip() == "":
        return 0.0
    cleaned = value.strip().replace(".", "").replace(",", ".")
    try:
        return float(cleaned)
    except ValueError:
        return 0.0


def _parse_date(value: str) -> date:
    """Parse DD.MM.YYYY → date"""
    return datetime.strptime(value.strip(), "%d.%m.%Y").date()


def _build_purpose(row: dict) -> str:
    """Concatenate VWZ1..VWZ14 into a single purpose string."""
    parts = []
    for i in range(1, 15):
        v = row.get(f"VWZ{i}", "").strip()
        if v:
            parts.append(v)
    return " ".join(parts)


def _classify(row: dict, purpose: str, owner_ibans: dict[str, str]) -> tuple[str, str | None]:
    """Return (transaction_type, owner_unit_id)."""
    counterparty_iban = row.get("AgKto", "").strip()
    booking_text = row.get("BuchText", "").strip().lower()
    amount = _parse_decimal(row.get("Betrag", "0"))

    # Try to detect unit from purpose
    m = _WE_PATTERN.search(purpose)
    unit = f"WE-{m.group(1)}" if m else owner_ibans.get(counterparty_iban)

    if unit and amount > 0:
        return "hausgeld", unit

    if "rücklage" in purpose.lower() or "rücklage" in booking_text:
        return "rücklage", None

    if "entgeltabschluss" in booking_text or "abschluss" in booking_text:
        return "bankgebühr", None

    if amount < 0:
        return "ausgabe", None

    return "sonstiges", unit


def parse_starmoney_file(
    content: bytes | str,
    account_id: str,
    account_number: str,
    extra_owner_ibans: dict[str, str] | None = None,
) -> Iterator[TransactionCreate]:
    """
    Parse a StarMoney SEPA export file and yield TransactionCreate objects.

    Args:
        content: Raw file bytes or string content.
        account_id: MongoDB _id of the account these transactions belong to.
        account_number: Short account number string (e.g. "6023543").
        extra_owner_ibans: Additional IBAN→unit_id mapping from the database.
    """
    if isinstance(content, bytes):
        # StarMoney exports with latin-1 / cp1252 encoding
        for encoding in ("utf-8-sig", "cp1252", "latin-1"):
            try:
                content = content.decode(encoding)
                break
            except UnicodeDecodeError:
                continue

    owner_ibans = dict(KNOWN_OWNER_IBANS)
    if extra_owner_ibans:
        owner_ibans.update(extra_owner_ibans)

    reader = csv.DictReader(
        io.StringIO(content),
        delimiter=";",
        quotechar='"',
    )

    seen_ids: set[int] = set()

    for row in reader:
        sm_id_raw = row.get("ID", "").strip()
        if not sm_id_raw:
            continue
        try:
            sm_id = int(sm_id_raw)
        except ValueError:
            sm_id = None

        if sm_id in seen_ids:
            continue
        if sm_id:
            seen_ids.add(sm_id)

        purpose = _build_purpose(row)
        tx_type, unit = _classify(row, purpose, owner_ibans)

        try:
            booking_date = _parse_date(row.get("BuchDatum", ""))
            value_date = _parse_date(row.get("WertDatum", ""))
        except ValueError:
            continue

        amount = _parse_decimal(row.get("Betrag", "0"))
        # Skip zero-amount settlement entries (Abschluss with 0,00)
        if amount == 0.0:
            tx_type = "abschluss"

        seq_no_raw = row.get("Lfd.Nr", "").strip()
        seq_no = int(seq_no_raw) if seq_no_raw.isdigit() else None

        counterparty_iban = row.get("AgKto", "").strip()
        counterparty_bic = row.get("AgBlz", "").strip()
        counterparty_name = row.get("AgName1", "").strip()

        yield TransactionCreate(
            account_id=account_id,
            account_number=account_number,
            booking_date=booking_date,
            value_date=value_date,
            amount=amount,
            currency=row.get("BtgWaehr", "EUR").strip().strip('"'),
            counterparty_name=counterparty_name or None,
            counterparty_iban=counterparty_iban or None,
            counterparty_bic=counterparty_bic or None,
            purpose=purpose,
            booking_text=row.get("BuchText", "").strip(),
            category=row.get("Kategorie", "").strip() or None,
            subcategory=row.get("Unterkat", "").strip() or None,
            transaction_type=tx_type,
            owner_unit=unit,
            seq_no=seq_no,
            starmoney_id=sm_id,
        )
