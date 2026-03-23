from fastapi import APIRouter, Query
from ..database import get_db
from ..services.payment_analyzer import (
    get_payment_status,
    get_surcharge_payments,
    get_expense_summary,
    get_income_summary,
)

router = APIRouter(prefix="/api/analytics", tags=["analytics"])


@router.get("/payment-status")
async def payment_status(year: int = Query(default=2025)):
    db = get_db()
    return await get_payment_status(db, year)


@router.get("/surcharges")
async def surcharges():
    db = get_db()
    return await get_surcharge_payments(db)


@router.get("/expenses")
async def expenses(year: int = Query(default=2025)):
    db = get_db()
    return await get_expense_summary(db, year)


@router.get("/income")
async def income(year: int = Query(default=2025)):
    db = get_db()
    return await get_income_summary(db, year)


@router.get("/account-balance-history")
async def account_balance_history():
    """
    Return the reconstructed account balance at 01.01 and 31.12 for every year
    that has transaction data, for each account.

    Algorithm:
      balance_at(date) = current_balance
                         - sum(tx.amount for tx where tx.booking_date > date)
    """
    from datetime import date as Date
    db = get_db()

    accounts = await db.accounts.find().to_list(None)
    result = []

    for acc in accounts:
        account_number = acc["account_number"]
        current_balance = acc.get("current_balance", 0.0)

        # Get all transactions for this account sorted by date desc
        txs = await db.transactions.find(
            {"account_number": account_number},
            {"booking_date": 1, "amount": 1},
        ).sort("booking_date", 1).to_list(None)

        if not txs:
            result.append({"account_number": account_number, "name": acc["name"], "snapshots": []})
            continue

        # Determine year range from actual transaction data
        first_date = txs[0]["booking_date"]
        last_date  = txs[-1]["booking_date"]
        if isinstance(first_date, str):
            first_date = Date.fromisoformat(first_date)
        if isinstance(last_date, str):
            last_date = Date.fromisoformat(last_date)

        first_year = first_date.year
        last_year  = last_date.year

        # Build suffix-sum: sum of all amounts AFTER a given date
        # We walk backwards from current_balance
        # Step 1: index amounts by date string for fast lookup
        from collections import defaultdict
        daily: dict[str, float] = defaultdict(float)
        for tx in txs:
            d = tx["booking_date"]
            if hasattr(d, 'isoformat'):
                d = d.isoformat()
            daily[d] += tx["amount"]

        # Step 2: sorted unique dates descending
        sorted_dates = sorted(daily.keys(), reverse=True)

        # Step 3: compute cumulative suffix-sum table
        # suffix_sum[date] = sum of all transactions AFTER date (strictly)
        # current_balance - suffix_sum["YYYY-12-31"] = balance at end of YYYY
        # We'll compute on-the-fly for each key date

        def balance_at(target_iso: str) -> float:
            """Balance after processing all transactions on target_iso date."""
            future_sum = sum(
                v for d, v in daily.items() if d > target_iso
            )
            return round(current_balance - future_sum, 2)

        snapshots = []
        for year in range(first_year, last_year + 1):
            jan1  = f"{year}-01-01"
            dec31 = f"{year}-12-31"

            # Balance at 01.01: BEFORE any transactions on that day
            # = balance AFTER all transactions on 31.12 of previous year
            b_jan1 = balance_at(f"{year - 1}-12-31")

            # Balance at 31.12: AFTER all transactions on that day
            b_dec31 = balance_at(dec31)

            # Change over the year
            change = round(b_dec31 - b_jan1, 2)

            # Only include if we actually have transactions in that year
            has_data = any(jan1 <= d <= dec31 for d in daily)
            if has_data:
                snapshots.append({
                    "year": year,
                    "balance_jan1":  b_jan1,
                    "balance_dec31": b_dec31,
                    "change":        change,
                })

        result.append({
            "account_number": account_number,
            "name": acc["name"],
            "account_type": acc.get("account_type", ""),
            "current_balance": current_balance,
            "snapshots": snapshots,
        })

    return result


@router.get("/dashboard")
async def dashboard(year: int = Query(default=2025)):
    """
    Combined dashboard data: account balances, payment overview, recent transactions.
    """
    db = get_db()
    accounts = await db.accounts.find().to_list(None)
    for a in accounts:
        a["_id"] = str(a["_id"])

    payment_data = await get_payment_status(db, year)
    expenses = await get_expense_summary(db, year)

    # Recent transactions (last 20)
    recent = (
        await db.transactions.find()
        .sort("booking_date", -1)
        .limit(20)
        .to_list(None)
    )
    for t in recent:
        t["_id"] = str(t["_id"])

    # Count missing payments (months before today that have status "missing")
    today_month = __import__("datetime").date.today().month
    missing_count = sum(
        1
        for owner in payment_data
        for month_info in owner["months"]
        if month_info["status"] == "missing" and month_info["month"] <= today_month
    )

    total_income = sum(
        t["amount"] for t in await db.transactions.find(
            {"amount": {"$gt": 0}, "transaction_type": "hausgeld",
             "is_fehlbuchung": {"$ne": True},
             "booking_date": {"$gte": f"{year}-01-01", "$lte": f"{year}-12-31"}}
        ).to_list(None)
    )
    total_expenses = sum(
        t["amount"] for t in await db.transactions.find(
            {"amount": {"$lt": 0}, "account_number": "6023543",
             "is_fehlbuchung": {"$ne": True},
             "booking_date": {"$gte": f"{year}-01-01", "$lte": f"{year}-12-31"}}
        ).to_list(None)
    )

    return {
        "accounts": accounts,
        "payment_overview": payment_data,
        "expense_summary": expenses,
        "recent_transactions": recent,
        "stats": {
            "total_hausgeld_income": round(total_income, 2),
            "total_expenses": round(total_expenses, 2),
            "missing_payments": missing_count,
        },
    }
