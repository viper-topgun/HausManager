from fastapi import APIRouter, HTTPException, Query
from bson import ObjectId
from pydantic import BaseModel
from typing import Optional
from ..database import get_db
from ..services.expense_classifier import EXPENSE_TAXONOMY, classify_expense, is_valid_kategorie

router = APIRouter(prefix="/api/transactions", tags=["transactions"])


def _fix_id(doc: dict) -> dict:
    doc["_id"] = str(doc["_id"])
    return doc


@router.get("/")
async def list_transactions(
    account_number: Optional[str] = None,
    transaction_type: Optional[str] = None,
    owner_unit: Optional[str] = None,
    year: Optional[int] = None,
    month: Optional[int] = None,
    search: Optional[str] = None,
    haupttyp: Optional[str] = None,
    untertyp: Optional[str] = None,
    limit: int = Query(default=200, le=1000),
    skip: int = 0,
):
    db = get_db()
    query: dict = {}
    if account_number:
        query["account_number"] = account_number
    if transaction_type:
        query["transaction_type"] = transaction_type
    if owner_unit:
        query["owner_unit"] = owner_unit
    if haupttyp:
        query["haupttyp"] = haupttyp
    if untertyp:
        query["untertyp"] = untertyp
    if search:
        import re
        pattern = re.compile(re.escape(search), re.IGNORECASE)
        query["$or"] = [
            {"counterparty_name": {"$regex": pattern}},
            {"purpose": {"$regex": pattern}},
            {"booking_text": {"$regex": pattern}},
        ]
    if year:
        from datetime import date
        date_from = date(year, month or 1, 1).isoformat()
        if month:
            from calendar import monthrange
            last_day = monthrange(year, month)[1]
            date_to = date(year, month, last_day).isoformat()
        else:
            date_to = date(year, 12, 31).isoformat()
        query["booking_date"] = {"$gte": date_from, "$lte": date_to}

    total = await db.transactions.count_documents(query)
    docs = (
        await db.transactions.find(query)
        .sort("booking_date", -1)
        .skip(skip)
        .limit(limit)
        .to_list(None)
    )
    return {"total": total, "items": [_fix_id(d) for d in docs]}


# ---------------------------------------------------------------------------
# Expense taxonomy: used by frontend to build dropdowns
# Static path – MUST be defined before the /{tx_id} wildcard route
# ---------------------------------------------------------------------------

@router.get("/taxonomy")
async def get_taxonomy():
    """Return the full Haupttyp → [Untertypen] taxonomy for expense categories."""
    return EXPENSE_TAXONOMY


@router.get("/{tx_id}")
async def get_transaction(tx_id: str):
    db = get_db()
    doc = await db.transactions.find_one({"_id": ObjectId(tx_id)})
    if not doc:
        raise HTTPException(status_code=404, detail="Transaction not found")
    return _fix_id(doc)


@router.delete("/{tx_id}", status_code=204)
async def delete_transaction(tx_id: str):
    db = get_db()
    result = await db.transactions.delete_one({"_id": ObjectId(tx_id)})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Transaction not found")


# ---------------------------------------------------------------------------
# Kategorie-Zuweisung (manual override)
# ---------------------------------------------------------------------------

class KategorieUpdate(BaseModel):
    haupttyp: Optional[str] = None   # Hauptkategorie  (None = zurücksetzen)
    untertyp: Optional[str] = None   # Unterkategorie  (None = zurücksetzen)


@router.patch("/{tx_id}/kategorie")
async def set_kategorie(tx_id: str, data: KategorieUpdate):
    """Manually assign or clear the Haupttyp/Untertyp for a transaction."""
    if data.haupttyp and data.untertyp:
        if not is_valid_kategorie(data.haupttyp, data.untertyp):
            raise HTTPException(
                status_code=422,
                detail=f"'{data.untertyp}' ist kein gültiger Untertyp von '{data.haupttyp}'",
            )
    db = get_db()
    update = {
        "haupttyp": data.haupttyp,
        "untertyp": data.untertyp,
    }
    result = await db.transactions.update_one(
        {"_id": ObjectId(tx_id)}, {"$set": update}
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Transaction not found")
    doc = await db.transactions.find_one({"_id": ObjectId(tx_id)})
    return _fix_id(doc)


# ---------------------------------------------------------------------------
# Retroactive auto-classification of uncategorised ausgabe transactions
# ---------------------------------------------------------------------------

@router.post("/reclassify", status_code=200)
async def reclassify_expenses():
    """
    Run the auto-classifier over ALL ausgabe transactions that currently have
    no category set and update them in-place.
    Returns the number of transactions that were updated.
    """
    db = get_db()
    cursor = db.transactions.find({
        "transaction_type": "ausgabe",
        "haupttyp": None,
        "is_fehlbuchung": {"$ne": True},
    })

    updated = 0
    async for tx in cursor:
        ht, ut = classify_expense(
            tx.get("counterparty_name") or "",
            tx.get("purpose") or "",
        )
        if ht:
            await db.transactions.update_one(
                {"_id": tx["_id"]},
                {"$set": {"haupttyp": ht, "untertyp": ut}},
            )
            updated += 1

    return {"updated": updated}


class FehlbuchungUpdate(BaseModel):
    is_fehlbuchung: bool
    fehlbuchung_note: Optional[str] = None


@router.patch("/{tx_id}/fehlbuchung")
async def set_fehlbuchung(tx_id: str, data: FehlbuchungUpdate):
    """Mark or unmark a transaction as an erroneous booking (Fehlbuchung).
    Fehlbuchungen are excluded from all Abrechnungen and analytics.
    """
    db = get_db()
    update: dict = {"is_fehlbuchung": data.is_fehlbuchung}
    if data.fehlbuchung_note is not None:
        update["fehlbuchung_note"] = data.fehlbuchung_note
    if not data.is_fehlbuchung:
        update["fehlbuchung_note"] = None
    result = await db.transactions.update_one(
        {"_id": ObjectId(tx_id)}, {"$set": update}
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Transaction not found")
    doc = await db.transactions.find_one({"_id": ObjectId(tx_id)})
    return _fix_id(doc)
