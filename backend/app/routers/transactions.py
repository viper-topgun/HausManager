from fastapi import APIRouter, HTTPException, Query
from bson import ObjectId
from typing import Optional
from ..database import get_db

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
