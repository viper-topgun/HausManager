from fastapi import APIRouter, HTTPException, status
from bson import ObjectId
from ..database import get_db
from ..models.account import Account, AccountCreate, AccountUpdate

router = APIRouter(prefix="/api/accounts", tags=["accounts"])


def _fix_id(doc: dict) -> dict:
    doc["_id"] = str(doc["_id"])
    return doc


@router.get("/", response_model=list[Account])
async def list_accounts():
    db = get_db()
    docs = await db.accounts.find().to_list(None)
    return [_fix_id(d) for d in docs]


@router.get("/{account_id}", response_model=Account)
async def get_account(account_id: str):
    db = get_db()
    doc = await db.accounts.find_one({"_id": ObjectId(account_id)})
    if not doc:
        raise HTTPException(status_code=404, detail="Account not found")
    return _fix_id(doc)


@router.post("/", response_model=Account, status_code=status.HTTP_201_CREATED)
async def create_account(data: AccountCreate):
    db = get_db()
    result = await db.accounts.insert_one(data.model_dump())
    doc = await db.accounts.find_one({"_id": result.inserted_id})
    return _fix_id(doc)


@router.put("/{account_id}", response_model=Account)
async def update_account(account_id: str, data: AccountUpdate):
    db = get_db()
    update_data = {k: v for k, v in data.model_dump().items() if v is not None}
    if not update_data:
        raise HTTPException(status_code=400, detail="No fields to update")
    await db.accounts.update_one({"_id": ObjectId(account_id)}, {"$set": update_data})
    doc = await db.accounts.find_one({"_id": ObjectId(account_id)})
    return _fix_id(doc)
