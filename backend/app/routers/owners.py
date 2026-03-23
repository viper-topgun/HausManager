from fastapi import APIRouter, HTTPException, status
from bson import ObjectId
from ..database import get_db
from ..models.owner import Owner, OwnerCreate, OwnerUpdate

router = APIRouter(prefix="/api/owners", tags=["owners"])


def _fix_id(doc: dict) -> dict:
    doc["_id"] = str(doc["_id"])
    return doc


@router.get("/", response_model=list[Owner])
async def list_owners():
    db = get_db()
    docs = await db.owners.find().sort("unit_id", 1).to_list(None)
    return [_fix_id(d) for d in docs]


@router.get("/{owner_id}", response_model=Owner)
async def get_owner(owner_id: str):
    db = get_db()
    doc = await db.owners.find_one({"_id": ObjectId(owner_id)})
    if not doc:
        raise HTTPException(status_code=404, detail="Owner not found")
    return _fix_id(doc)


@router.post("/", response_model=Owner, status_code=status.HTTP_201_CREATED)
async def create_owner(data: OwnerCreate):
    db = get_db()
    result = await db.owners.insert_one(data.model_dump())
    doc = await db.owners.find_one({"_id": result.inserted_id})
    return _fix_id(doc)


@router.put("/{owner_id}", response_model=Owner)
async def update_owner(owner_id: str, data: OwnerUpdate):
    db = get_db()
    update_data = {k: v for k, v in data.model_dump().items() if v is not None}
    if not update_data:
        raise HTTPException(status_code=400, detail="No fields to update")
    await db.owners.update_one({"_id": ObjectId(owner_id)}, {"$set": update_data})
    doc = await db.owners.find_one({"_id": ObjectId(owner_id)})
    return _fix_id(doc)


@router.delete("/{owner_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_owner(owner_id: str):
    db = get_db()
    result = await db.owners.delete_one({"_id": ObjectId(owner_id)})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Owner not found")
