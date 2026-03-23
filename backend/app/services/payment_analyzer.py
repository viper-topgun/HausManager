"""
Payment analytics:
- Regular monthly Hausgeld tracking with shift detection
  (payments arriving a few days before/after the expected month)
- BKA / Betriebskostenabrechnung separation (including cross-year settlements)
- Missing-month detection
"""

import re
from collections import defaultdict
from datetime import date, timedelta
from calendar import monthrange
from typing import Any

from motor.motor_asyncio import AsyncIOMotorDatabase

# Keywords that mark an incoming payment as BKA / annual settlement rather than regular monthly Hausgeld
_BKA_RE = re.compile(
    r"(nachzahlung|betriebskosten(?:abrechnung)?|jahresabrechnung|"
    r"\bbka\b|abrechnung\s+\d{4}|gutschrift\s+(?:bka|abr\.?)|rückzahlung|erstattung)",
    re.IGNORECASE,
)

# Extract an explicit year reference from a purpose string (e.g. "BKA 2023" → 2023)
_YEAR_RE = re.compile(r"\b(20\d{2})\b")


def _is_bka(purpose: str) -> bool:
    return bool(_BKA_RE.search(purpose))


def _year_ref(purpose: str, fallback: int) -> int:
    """Return the most relevant year mentioned in the purpose text, or fallback."""
    for m in _YEAR_RE.findall(purpose):
        y = int(m)
        if 2000 <= y <= fallback:
            return y
    return fallback


def _window(year: int, month: int) -> tuple[date, date]:
    """
    Matching window for a given month:
    5 days before the 1st up to 10 days after the last day.
    This handles month-end standing orders that tip into the next month
    and payments that arrive a few days early.
    """
    start = date(year, month, 1) - timedelta(days=5)
    last = date(year, month, monthrange(year, month)[1])
    end = last + timedelta(days=10)
    return start, end


async def get_payment_status(db: AsyncIOMotorDatabase, year: int) -> list[dict[str, Any]]:
    """
    Return a per-owner payment analysis for *year*:
    - `months`: 12-entry list with ok / shifted / prepaid / missing status per month
    - `bka_payments`: surplus / BKA / Nachzahlung entries (with cross-year reference)
    - Totals and status counts
    """
    owners = await db.owners.find().sort("unit_id", 1).to_list(None)
    results = []

    for owner in owners:
        unit = owner["unit_id"]
        expected = owner.get("monthly_hausgeld", 0.0)
        tolerance = max(expected * 0.10, 1.0)  # 10% tolerance for "regular" classification

        # Wider query window: Dec(year-1) to Feb(year+1) to catch shifted boundary payments
        cursor = db.transactions.find({
            "owner_unit": unit,
            "transaction_type": "hausgeld",
            "is_fehlbuchung": {"$ne": True},
            "booking_date": {
                "$gte": date(year - 1, 12, 1).isoformat(),
                "$lte": date(year + 1, 2, 28).isoformat(),
            },
        })

        all_txs: list[dict] = []
        async for tx in cursor:
            bd = tx["booking_date"]
            if isinstance(bd, str):
                bd = date.fromisoformat(bd)
            all_txs.append({
                "_id": str(tx["_id"]),
                "date": bd,
                "amount": tx["amount"],
                "purpose": tx.get("purpose", ""),
                "booking_text": tx.get("booking_text", ""),
            })

        # ── Classify ──────────────────────────────────────────────────────────
        bka_pool: list[dict] = []
        regular_pool: list[dict] = []

        for tx in all_txs:
            full_text = tx["purpose"] + " " + tx["booking_text"]
            if _is_bka(full_text):
                bka_pool.append(tx)
            elif tx["amount"] > 0 and abs(tx["amount"] - expected) <= tolerance:
                regular_pool.append(tx)
            else:
                # Doesn't match regular amount and has no BKA keyword
                # (e.g., partial payment, refund, unusual amount) → treat as BKA/surplus
                bka_pool.append(tx)

        regular_pool.sort(key=lambda t: t["date"])

        # ── Greedy month assignment ────────────────────────────────────────────
        used: set[str] = set()
        month_results: list[dict] = []

        for m in range(1, 13):
            win_start, win_end = _window(year, m)
            anchor = date(year, m, 1)

            candidates = [
                tx for tx in regular_pool
                if tx["_id"] not in used and win_start <= tx["date"] <= win_end
            ]

            if candidates:
                # Prefer transactions that fall IN month M; otherwise closest to anchor
                in_month = [tx for tx in candidates if tx["date"].year == year and tx["date"].month == m]
                best = min(in_month or candidates, key=lambda tx: abs((tx["date"] - anchor).days))
                used.add(best["_id"])
                shift = (best["date"] - anchor).days
                # Status based on CALENDAR MONTH: "ok" if booked in the target month,
                # "shifted" if booked in a later month, "prepaid" if booked earlier.
                if best["date"].year == year and best["date"].month == m:
                    status = "ok"
                elif best["date"] < anchor:
                    status = "prepaid"
                else:
                    status = "shifted"
                month_results.append({
                    "month": m,
                    "paid": round(best["amount"], 2),
                    "expected": round(expected, 2),
                    "status": status,
                    "shift_days": shift,
                    "date": best["date"].isoformat(),
                    # legacy field for dashboard compat
                    "ok": status in ("ok", "prepaid", "shifted"),
                })
            else:
                month_results.append({
                    "month": m,
                    "paid": 0.0,
                    "expected": round(expected, 2),
                    "status": "missing",
                    "shift_days": None,
                    "date": None,
                    "ok": False,
                })

        # ── BKA / surplus list ────────────────────────────────────────────────
        # Include unmatched regular transactions that fall inside the target year
        unmatched_regular = [
            tx for tx in regular_pool
            if tx["_id"] not in used and date(year, 1, 1) <= tx["date"] <= date(year, 12, 31)
        ]
        bka_in_year = [tx for tx in bka_pool if date(year, 1, 1) <= tx["date"] <= date(year, 12, 31)]

        bka_list: list[dict] = []
        for tx in sorted(bka_in_year + unmatched_regular, key=lambda t: t["date"]):
            full_text = tx["purpose"] + " " + tx["booking_text"]
            yr = _year_ref(full_text, tx["date"].year)
            bka_list.append({
                "date": tx["date"].isoformat(),
                "amount": round(tx["amount"], 2),
                "purpose": tx["purpose"],
                "year_ref": yr,
                "cross_year": yr != tx["date"].year,
                "type": "bka" if _is_bka(full_text) else "surplus",
            })

        # ── Cross-year BKA: search beyond normal window for settlements referencing this year ──
        # Catches e.g. WE-004 Nachzahlung 2024 paid in January 2026.
        extra_txs = await db.transactions.find({
            "owner_unit": unit,
            "is_fehlbuchung": {"$ne": True},
            "booking_date": {"$gt": date(year + 1, 2, 28).isoformat()},
        }).to_list(None)
        existing_keys = {b["date"] + "|" + str(b["amount"]) for b in bka_list}
        for tx in extra_txs:
            bd = tx["booking_date"]
            if isinstance(bd, str):
                bd = date.fromisoformat(bd)
            full_text = tx.get("purpose", "") + " " + tx.get("booking_text", "")
            yr = _year_ref(full_text, bd.year)
            if yr == year:
                key = bd.isoformat() + "|" + str(round(tx["amount"], 2))
                if key not in existing_keys:
                    bka_list.append({
                        "date": bd.isoformat(),
                        "amount": round(tx["amount"], 2),
                        "purpose": tx.get("purpose", ""),
                        "year_ref": yr,
                        "cross_year": True,
                        "type": "bka" if _is_bka(full_text) else "surplus",
                    })

        # ── Totals ────────────────────────────────────────────────────────────
        total_regular = sum(m["paid"] for m in month_results)
        total_bka = sum(b["amount"] for b in bka_list if b["amount"] > 0)
        total_expected = expected * 12

        status_counts: dict[str, int] = defaultdict(int)
        for m in month_results:
            status_counts[m["status"]] += 1

        results.append({
            "unit_id": unit,
            "name": owner["name"],
            "monthly_expected": expected,
            "months": month_results,
            "bka_payments": bka_list,
            "total_regular_paid": round(total_regular, 2),
            "total_bka_paid": round(total_bka, 2),
            "total_paid": round(total_regular + total_bka, 2),   # legacy compat
            "total_expected": round(total_expected, 2),
            "balance": round(total_regular + total_bka - total_expected, 2),
            "status_counts": dict(status_counts),
        })

    return results


async def get_surcharge_payments(db: AsyncIOMotorDatabase) -> list[dict[str, Any]]:
    """
    Return all BKA / Nachzahlung / Sonderzahlung entries across all years.
    Uses the same BKA keyword set as the payment-status analysis.
    """
    results = []
    async for tx in db.transactions.find({"amount": {"$ne": 0}, "is_fehlbuchung": {"$ne": True}}):
        purpose = tx.get("purpose", "") + " " + tx.get("booking_text", "")
        if _is_bka(purpose):
            results.append({
                "date": tx["booking_date"],
                "counterparty": tx.get("counterparty_name", ""),
                "amount": tx["amount"],
                "purpose": tx.get("purpose", ""),
                "owner_unit": tx.get("owner_unit"),
                "account": tx["account_number"],
            })

    results.sort(key=lambda x: x["date"], reverse=True)
    return results


async def get_expense_summary(db: AsyncIOMotorDatabase, year: int) -> list[dict[str, Any]]:
    """
    Summarize expenses (negative transactions) by normalized category for the given year.
    Normalization rules map counterparty / purpose to meaningful category names.
    """
    pipeline = [
        {
            "$match": {
                "amount": {"$lt": 0},
                "account_number": "6023543",  # only operating account
                "is_fehlbuchung": {"$ne": True},
                "booking_date": {
                    "$gte": date(year, 1, 1).isoformat(),
                    "$lte": date(year, 12, 31).isoformat(),
                },
            }
        },
        {
            "$group": {
                "_id": {
                    "category": "$category",
                    "counterparty": "$counterparty_name",
                    "purpose": "$purpose",
                    "booking_text": "$booking_text",
                },
                "total": {"$sum": "$amount"},
                "count": {"$sum": 1},
            }
        },
        {"$sort": {"total": 1}},
    ]

    # Accumulate into normalized buckets: {norm_category: {counterparty: {total, count}}}
    from collections import defaultdict
    buckets: dict[str, dict[str, dict]] = defaultdict(lambda: defaultdict(lambda: {"total": 0.0, "count": 0}))

    async for doc in db.transactions.aggregate(pipeline):
        raw_cat   = doc["_id"].get("category") or ""
        cp        = doc["_id"].get("counterparty") or ""
        purpose   = doc["_id"].get("purpose") or ""
        btext     = doc["_id"].get("booking_text") or ""
        norm_cat  = _normalize_expense_category(cp, purpose, btext, raw_cat)
        buckets[norm_cat][cp]["total"]  += doc["total"]
        buckets[norm_cat][cp]["count"]  += doc["count"]

    results = []
    for norm_cat, cps in buckets.items():
        for cp, data in cps.items():
            results.append({
                "category": norm_cat,
                "counterparty": cp,
                "total": round(data["total"], 2),
                "count": data["count"],
            })

    results.sort(key=lambda x: x["total"])
    return results


def _normalize_expense_category(counterparty: str, purpose: str, booking_text: str, raw_category: str) -> str:
    """
    Map raw StarMoney category + counterparty/purpose to a clean display category.
    Rules are evaluated top-down; first match wins.
    """
    cp  = (counterparty or "").lower()
    p   = (purpose or "").lower() + " " + (booking_text or "").lower()

    # ── Strom ─────────────────────────────────────────────────────────────────
    if any(k in cp for k in ("e.on", "eon energie", "e.on energie")):
        return "Strom"
    if "strom" in p or "strom" in cp:
        return "Strom"

    # ── Versicherung ──────────────────────────────────────────────────────────
    if any(k in cp for k in ("versicherung", "vkb", "allianz", "huk", "ergo", "axa", "zurich")):
        return "Versicherung"
    if "versicherung" in p:
        return "Versicherung"

    # ── Wasser / Abwasser ─────────────────────────────────────────────────────
    if any(k in cp for k in ("weilachgruppe", "wasservers", "zweckverband")):
        return "Wasser"
    if "wasser" in p:
        return "Wasser"

    # ── Abwasser / Kanal ──────────────────────────────────────────────────────
    if any(k in cp for k in ("gemeinde", "klärwerk", "abwasser", "kanal")):
        return "Abwasser/Kanal"
    if any(k in p for k in ("kanal", "abwasser", "kanalbenützung")):
        return "Abwasser/Kanal"

    # ── Heizung / Biomasse ────────────────────────────────────────────────────
    if any(k in cp for k in ("biomasse", "heiz", "fernwärme", "wärme")):
        return "Heizung"
    if any(k in p for k in ("biomasse", "heizung", "wärme")):
        return "Heizung"

    # ── Hausverwaltung ────────────────────────────────────────────────────────
    if any(k in cp for k in ("witter", "hausverwalt", "verwaltung")):
        return "Hausverwaltung"

    # ── Rücklage ──────────────────────────────────────────────────────────────
    if "rücklage" in p or "rücklage" in cp:
        return "Rücklage"
    if cp == "weg tulpenstr. 31" or "weg tulpenstr" in cp:
        return "Rücklage"

    # ── Bankgebühren ──────────────────────────────────────────────────────────
    if any(k in (booking_text or "").lower() for k in ("entgelt", "kontoführung", "bankgebühr")):
        return "Bankgebühren"
    if "entgelt" in p or "abschluss" in (booking_text or "").lower():
        return "Bankgebühren"
    if "anlage & kredite" in raw_category.lower():
        return "Bankgebühren"

    # ── Instandhaltung / Reparatur ────────────────────────────────────────────
    if any(k in p for k in ("reparatur", "instandhaltung", "wartung", "handwerker",
                             "sanitär", "elektro", "dach", "fenster")):
        return "Instandhaltung"

    # ── Steuer / Finanzamt ────────────────────────────────────────────────────
    if any(k in cp for k in ("finanzamt", "steuer")):
        return "Steuer/Finanzamt"

    # ── Fallback: keep StarMoney category or "Sonstiges" ─────────────────────
    return raw_category if raw_category and raw_category not in ("", "None") else "Sonstiges"


async def get_income_summary(db: AsyncIOMotorDatabase, year: int) -> dict[str, Any]:
    """
    Summarize all income (positive transactions) for the given year on the Betriebskonto.
    Returns:
    - by_owner: regular Hausgeld per owner
    - bka: BKA / Nachzahlung / surplus entries per owner
    - other: other positive transactions (refunds, etc.)
    - totals
    """
    cursor = db.transactions.find({
        "amount": {"$gt": 0},
        "account_number": "6023543",
        "is_fehlbuchung": {"$ne": True},
        "booking_date": {
            "$gte": date(year, 1, 1).isoformat(),
            "$lte": date(year, 12, 31).isoformat(),
        },
    })

    from collections import defaultdict
    by_owner: dict[str, dict] = {}
    bka_entries: list[dict] = []
    other_entries: list[dict] = []

    # Pre-load owners for lookup
    owners = {o["unit_id"]: o["name"] for o in await db.owners.find().to_list(None)}

    async for tx in cursor:
        unit  = tx.get("owner_unit")
        cp    = tx.get("counterparty_name", "")
        purp  = tx.get("purpose", "") + " " + tx.get("booking_text", "")
        amt   = tx["amount"]
        bdate = tx["booking_date"]
        tx_type = tx.get("transaction_type", "")

        if _is_bka(purp) and unit:
            # BKA / Nachzahlung takes priority over regular hausgeld classification
            bka_entries.append({
                "date": bdate,
                "unit_id": unit,
                "name": owners.get(unit, unit),
                "counterparty": cp,
                "amount": amt,
                "purpose": tx.get("purpose", ""),
            })
        elif tx_type == "hausgeld" or (unit and not _is_bka(purp)):
            if unit:
                if unit not in by_owner:
                    by_owner[unit] = {
                        "unit_id": unit,
                        "name": owners.get(unit, unit),
                        "total": 0.0,
                        "count": 0,
                    }
                by_owner[unit]["total"] += amt
                by_owner[unit]["count"] += 1
            else:
                other_entries.append({"date": bdate, "counterparty": cp, "amount": amt, "purpose": tx.get("purpose", "")})
        else:
            other_entries.append({"date": bdate, "counterparty": cp, "amount": amt, "purpose": tx.get("purpose", "")})

    owner_list = sorted(by_owner.values(), key=lambda x: x["unit_id"])
    for o in owner_list:
        o["total"] = round(o["total"], 2)

    bka_entries.sort(key=lambda x: x["date"])
    other_entries.sort(key=lambda x: x["date"])

    total_regular = sum(o["total"] for o in owner_list)
    total_bka     = sum(b["amount"] for b in bka_entries)
    total_other   = sum(e["amount"] for e in other_entries)

    return {
        "by_owner": owner_list,
        "bka": bka_entries,
        "other": other_entries,
        "totals": {
            "regular": round(total_regular, 2),
            "bka":     round(total_bka, 2),
            "other":   round(total_other, 2),
            "total":   round(total_regular + total_bka + total_other, 2),
        },
    }
