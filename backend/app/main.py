from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .routers import owners, accounts, transactions, analytics, import_router, abrechnungen
from .database import get_client

app = FastAPI(
    title="HausManager API",
    description="Hausverwaltung WEG Tulpenstr. 31, Hilgertshausen-Tandern",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(owners.router)
app.include_router(accounts.router)
app.include_router(transactions.router)
app.include_router(analytics.router)
app.include_router(import_router.router)
app.include_router(abrechnungen.router)


@app.on_event("startup")
async def startup():
    from .database import get_db
    db = get_db()
    # Create indexes
    await db.transactions.create_index([("starmoney_id", 1), ("account_number", 1)], unique=True, sparse=True)
    await db.transactions.create_index([("booking_date", -1)])
    await db.transactions.create_index([("owner_unit", 1), ("booking_date", -1)])
    await db.owners.create_index("unit_id", unique=True)
    await db.accounts.create_index("account_number", unique=True)


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/api")
async def api_root():
    return {"message": "HausManager API", "docs": "/docs"}
