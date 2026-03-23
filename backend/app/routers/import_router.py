"""
Import router: handles StarMoney TXT file uploads and seeds initial data.
"""

import os
from fastapi import APIRouter, UploadFile, File, HTTPException, Form
from bson import ObjectId
from ..database import get_db
from ..services.starmoney_parser import parse_starmoney_file

router = APIRouter(prefix="/api/import", tags=["import"])


@router.post("/starmoney")
async def import_starmoney(
    file: UploadFile = File(...),
    account_number: str = Form(...),
):
    """
    Upload a StarMoney TXT export file for a given account_number.
    Existing entries (by starmoney_id) are skipped (upsert logic).
    """
    db = get_db()

    # Find or create the account
    account_doc = await db.accounts.find_one({"account_number": account_number})
    if not account_doc:
        raise HTTPException(
            status_code=404,
            detail=f"Account with number '{account_number}' not found. Please create it first.",
        )
    account_id = str(account_doc["_id"])

    # Load owner IBANs from DB for better classification
    owners = await db.owners.find({"iban": {"$ne": None}}).to_list(None)
    extra_ibans = {o["iban"]: o["unit_id"] for o in owners if o.get("iban")}

    content = await file.read()
    inserted = 0
    skipped = 0

    for tx in parse_starmoney_file(content, account_id, account_number, extra_ibans):
        tx_dict = tx.model_dump()
        # Convert date objects to ISO strings for MongoDB
        tx_dict["booking_date"] = tx_dict["booking_date"].isoformat()
        tx_dict["value_date"] = tx_dict["value_date"].isoformat()

        # Upsert by starmoney_id to avoid duplicates
        if tx_dict.get("starmoney_id"):
            existing = await db.transactions.find_one({
                "starmoney_id": tx_dict["starmoney_id"],
                "account_number": account_number,
            })
            if existing:
                skipped += 1
                continue

        await db.transactions.insert_one(tx_dict)
        inserted += 1

    # Update account balance from the last transaction's Saldo
    # (not stored in our model; instead compute from all transactions)
    return {
        "status": "ok",
        "inserted": inserted,
        "skipped": skipped,
        "account_number": account_number,
    }


@router.post("/seed")
async def seed_initial_data():
    """
    Seed the database with the known WEG accounts and owners.
    Safe to call multiple times (skips existing entries).
    """
    db = get_db()
    seeded = {"accounts": 0, "owners": 0}

    accounts = [
        {
            "account_number": "6023543",
            "iban": "DE34720512100006023543",
            "name": "WEG Betriebskonto",
            "account_type": "betriebskonto",
            "bank_name": "Raiffeisenbank",
            "current_balance": 3970.48,
            "currency": "EUR",
        },
        {
            "account_number": "6023550",
            "iban": "DE34720512100006023550",
            "name": "WEG Rücklagenkonto",
            "account_type": "rücklagenkonto",
            "bank_name": "Raiffeisenbank",
            "current_balance": 12677.11,
            "currency": "EUR",
        },
    ]

    for acc in accounts:
        existing = await db.accounts.find_one({"account_number": acc["account_number"]})
        if not existing:
            await db.accounts.insert_one(acc)
            seeded["accounts"] += 1

    owners = [
        {
            "unit_id": "WE-001",
            "name": "Veronika Patrignani",
            "iban": "DE38700915000002620090",
            "bic": "GENODEF1DCA",
            "monthly_hausgeld": 238.00,
        },
        {
            "unit_id": "WE-002",
            "name": "Siegfried Losch",
            "iban": "DE51700915000003638065",
            "bic": "GENODEF1DCA",
            "monthly_hausgeld": 269.00,
            "notes": "WE-002 und Büro 005",
        },
        {
            "unit_id": "WE-003",
            "name": "Horn Enrico und Bianca",
            "iban": "DE94721690800000052930",
            "bic": "GENODEF1GSB",
            "monthly_hausgeld": 178.00,
        },
        {
            "unit_id": "WE-004",
            "name": "Christian Schmach",
            "iban": "DE19721516500000914267",
            "bic": "BYLADEM1PAF",
            "monthly_hausgeld": 235.00,
        },
    ]

    for owner in owners:
        existing = await db.owners.find_one({"unit_id": owner["unit_id"]})
        if not existing:
            await db.owners.insert_one(owner)
            seeded["owners"] += 1

    return {"status": "ok", "seeded": seeded}


@router.get("/available-files")
async def list_available_files():
    """
    List all StarMoney TXT files in /app/data with their metadata.
    Returns each file with account info and how many transactions are already imported.
    """
    db = get_db()
    data_dir = "/app/data"

    if not os.path.isdir(data_dir):
        return {"files": []}

    file_account_map = {
        "6023543": ("6023543", "Betriebskonto"),
        "6023550": ("6023550", "Rücklagenkonto"),
    }

    files = []
    for filename in sorted(os.listdir(data_dir)):
        if not filename.endswith(".txt"):
            continue

        account_number = None
        account_name = None
        for key, (acct, name) in file_account_map.items():
            if key in filename:
                account_number = acct
                account_name = name
                break

        if not account_number:
            continue

        # Extract year from filename prefix like "2024_..."
        year = None
        parts = filename.split("_")
        if parts[0].isdigit() and len(parts[0]) == 4:
            year = parts[0]

        # Count already-imported transactions for this file by starmoney IDs
        # (rough estimate: count transactions in that account for that year)
        count_imported = 0
        if year:
            count_imported = await db.transactions.count_documents({
                "account_number": account_number,
                "booking_date": {"$gte": f"{year}-01-01", "$lte": f"{year}-12-31"},
            })
        else:
            count_imported = await db.transactions.count_documents({
                "account_number": account_number,
            })

        file_size = os.path.getsize(os.path.join(data_dir, filename))

        files.append({
            "filename": filename,
            "year": year,
            "account_number": account_number,
            "account_name": account_name,
            "size_bytes": file_size,
            "already_imported": count_imported,
        })

    return {"files": files}


@router.post("/import-single")
async def import_single_file(filename: str = Form(...)):
    """
    Import a single named file from /app/data.
    """
    import re
    data_dir = "/app/data"

    # Security: only allow simple filenames without path traversal
    if not re.match(r'^[\w\-. ]+\.txt$', filename) or "/" in filename or "\\" in filename:
        raise HTTPException(status_code=400, detail="Invalid filename")

    filepath = os.path.join(data_dir, filename)
    if not os.path.isfile(filepath):
        raise HTTPException(status_code=404, detail=f"File '{filename}' not found in /app/data")

    db = get_db()

    file_account_map = {
        "6023543": "6023543",
        "6023550": "6023550",
    }

    account_number = None
    for key in file_account_map:
        if key in filename:
            account_number = file_account_map[key]
            break

    if not account_number:
        raise HTTPException(status_code=400, detail="Cannot determine account number from filename")

    account_doc = await db.accounts.find_one({"account_number": account_number})
    if not account_doc:
        raise HTTPException(status_code=404, detail=f"Account '{account_number}' not found in DB")

    account_id = str(account_doc["_id"])
    owners = await db.owners.find({"iban": {"$ne": None}}).to_list(None)
    extra_ibans = {o["iban"]: o["unit_id"] for o in owners if o.get("iban")}

    with open(filepath, "rb") as f:
        content = f.read()

    inserted = skipped = 0
    for tx in parse_starmoney_file(content, account_id, account_number, extra_ibans):
        tx_dict = tx.model_dump()
        tx_dict["booking_date"] = tx_dict["booking_date"].isoformat()
        tx_dict["value_date"] = tx_dict["value_date"].isoformat()

        if tx_dict.get("starmoney_id"):
            existing = await db.transactions.find_one({
                "starmoney_id": tx_dict["starmoney_id"],
                "account_number": account_number,
            })
            if existing:
                skipped += 1
                continue

        await db.transactions.insert_one(tx_dict)
        inserted += 1

    return {
        "status": "ok",
        "file": filename,
        "account_number": account_number,
        "inserted": inserted,
        "skipped": skipped,
    }


@router.post("/seed-files")
async def seed_from_files():
    """
    Automatically import the StarMoney files found in /app/data.
    Useful for initial setup.
    """
    db = get_db()
    data_dir = "/app/data"
    results = []

    file_account_map = {
        "6023543": "6023543",
        "6023550": "6023550",
    }

    for filename in sorted(os.listdir(data_dir)):
        if not filename.endswith(".txt"):
            continue

        # Detect account number from filename
        account_number = None
        for acct in file_account_map:
            if acct in filename:
                account_number = acct
                break

        if not account_number:
            continue

        account_doc = await db.accounts.find_one({"account_number": account_number})
        if not account_doc:
            results.append({"file": filename, "status": "skipped", "reason": "account not found"})
            continue

        account_id = str(account_doc["_id"])
        owners = await db.owners.find({"iban": {"$ne": None}}).to_list(None)
        extra_ibans = {o["iban"]: o["unit_id"] for o in owners if o.get("iban")}

        filepath = os.path.join(data_dir, filename)
        with open(filepath, "rb") as f:
            content = f.read()

        inserted = skipped = 0
        for tx in parse_starmoney_file(content, account_id, account_number, extra_ibans):
            tx_dict = tx.model_dump()
            tx_dict["booking_date"] = tx_dict["booking_date"].isoformat()
            tx_dict["value_date"] = tx_dict["value_date"].isoformat()

            if tx_dict.get("starmoney_id"):
                existing = await db.transactions.find_one({
                    "starmoney_id": tx_dict["starmoney_id"],
                    "account_number": account_number,
                })
                if existing:
                    skipped += 1
                    continue

            await db.transactions.insert_one(tx_dict)
            inserted += 1

        results.append({
            "file": filename,
            "account": account_number,
            "inserted": inserted,
            "skipped": skipped,
        })

    return {"status": "ok", "results": results}
