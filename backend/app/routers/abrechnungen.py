from fastapi import APIRouter
from ..database import get_db
from typing import Optional, Dict
from pydantic import BaseModel

router = APIRouter(prefix="/api/abrechnungen", tags=["abrechnungen"])

# ---------------------------------------------------------------------------
# Stammdaten
# ---------------------------------------------------------------------------

UNIT_ORDER = ["WE-001", "WE-002", "WE-003", "WE-004", "WE-005"]

OWNERS_META = {
    "WE-001": {"name": "Veronika Patrignani", "address1": "Tulpenstr. 31",    "city": "86567 Hilgertshausen", "mea": 250.06},
    "WE-002": {"name": "Siegfried Lösch",     "address1": "Tulpenstr. 31",    "city": "86567 Hilgertshausen", "mea": 267.26},
    "WE-003": {"name": "Enrico Horn",          "address1": "Lichthausen 5a",  "city": "85302 Gerolsbach",      "mea": 216.10},
    "WE-004": {"name": "Christian Schmach",    "address1": "Beethovenstr. 94","city": "86551 Aichach",         "mea": 232.18},
    "WE-005": {"name": "Siegfried Lösch",      "address1": "Tulpenstr. 31",   "city": "86567 Hilgertshausen",  "mea":  34.40},
}

# 2024 – vollständig abgeschlossene Abrechnung (aus den erstellten Dokumenten)
DATA_2024 = {
    "bka1_ges_betrag": 9025.69,
    "kosten": {
        "ruecklagen":      2400.00,
        "witter":           159.59,
        "kontogebuehren":   196.05,
        "instandhaltung":  2211.32,
    },
    "vorauszahlungen": {
        "WE-001": 2856.00,
        "WE-002": 2184.00,
        "WE-003": 2136.00,
        "WE-004": 2820.00,
        "WE-005": 1044.00,
    },
    # anteilige BKA-1-Werte je Einheit (Gem. BetrKV – aus Witter-Abrechnung 2024)
    "owner_bka1": {
        "WE-001": 1560.46,
        "WE-002": 1889.53,
        "WE-003": 2442.17,
        "WE-004": 2625.30,
        "WE-005":  508.23,
    },
    # Exakte Gesamt-Beträge aus den Abrechnung-Dokumenten (Rundungsdifferenzen vermeiden)
    "owner_gesamt": {
        "WE-001": 2802.50,
        "WE-002": 3217.00,
        "WE-003": 3515.53,
        "WE-004": 3778.53,
        "WE-005":  679.09,
    },
}

# 2025 – bekannte Kosten; BKA-1 ausstehend bis Witter-Abrechnung vorliegt
DATA_2025_BASE = {
    "kosten": {
        "ruecklagen":      2400.00,
        "witter":          1097.43,
        "kontogebuehren":   187.62,
        "instandhaltung":  5807.38,
    },
    "vorauszahlungen": {
        "WE-001": 2856.00,
        "WE-002": 2184.00,
        "WE-003": 2136.00,
        "WE-004": 2820.00,
        "WE-005": 1044.00,
    },
}

# ---------------------------------------------------------------------------
# Hilfsfunktion – berechnet Positionen und Ergebnis für einen Eigentümer
# ---------------------------------------------------------------------------

def _build_owner(unit_id: str, kosten: dict, vorauszahlung: float,
                 bka1_ges: Optional[float], bka1_ant: Optional[float],
                 editable: bool, gesamt_override: Optional[float] = None) -> dict:
    meta = OWNERS_META[unit_id]
    mea = meta["mea"]

    def ant(total):
        return round(total * mea / 1000, 2)

    positionen = [
        {
            "kostenkonto":     "Rücklagen",
            "umlageart":       "Miteigentumsanteil",
            "umlage_anteilig": mea,
            "ges_betrag":      kosten["ruecklagen"],
            "betrag_ant":      ant(kosten["ruecklagen"]),
            "editable":        False,
        },
        {
            "kostenkonto":     "Gesamtkosten Betriebskostenabrechnung 1",
            "umlageart":       "Gem. BetrKV",
            "umlage_anteilig": None,
            "ges_betrag":      bka1_ges,
            "betrag_ant":      bka1_ant,
            "editable":        editable,
        },
        {
            "kostenkonto":     "Abrechnung Witter",
            "umlageart":       "Miteigentumsanteil",
            "umlage_anteilig": mea,
            "ges_betrag":      kosten["witter"],
            "betrag_ant":      ant(kosten["witter"]),
            "editable":        False,
        },
        {
            "kostenkonto":     "Kontogebühren",
            "umlageart":       "Miteigentumsanteil",
            "umlage_anteilig": mea,
            "ges_betrag":      kosten["kontogebuehren"],
            "betrag_ant":      ant(kosten["kontogebuehren"]),
            "editable":        False,
        },
        {
            "kostenkonto":     "Instandhaltung Objekt",
            "umlageart":       "Miteigentumsanteil",
            "umlage_anteilig": mea,
            "ges_betrag":      kosten["instandhaltung"],
            "betrag_ant":      ant(kosten["instandhaltung"]),
            "editable":        False,
        },
    ]

    # Teilsumme ohne BKA-1
    fixed_ant = round(
        ant(kosten["ruecklagen"]) +
        ant(kosten["witter"]) +
        ant(kosten["kontogebuehren"]) +
        ant(kosten["instandhaltung"]),
        2,
    )
    gesamt = gesamt_override if gesamt_override is not None else (
        round(fixed_ant + bka1_ant, 2) if bka1_ant is not None else None
    )
    nachzahlung = round(gesamt - vorauszahlung, 2) if gesamt is not None else None

    return {
        "unit_id":       unit_id,
        "name":          meta["name"],
        "address1":      meta["address1"],
        "city":          meta["city"],
        "mea":           mea,
        "vorauszahlung": vorauszahlung,
        "positionen":    positionen,
        "fixed_ant":     fixed_ant,
        "bka1_betrag_ant": bka1_ant,
        "gesamt":        gesamt,
        "nachzahlung":   nachzahlung,
    }


# ---------------------------------------------------------------------------
# Pydantic-Modell für PUT
# ---------------------------------------------------------------------------

class AbrechnungUpdate(BaseModel):
    bka1_ges_betrag: Optional[float] = None
    owner_bka1: Dict[str, Optional[float]] = {}
    witter_override: Optional[float] = None
    instandhaltung_override: Optional[float] = None


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get("/{year}")
async def get_abrechnung(year: int):
    if year == 2024:
        from datetime import date as _date
        d = DATA_2024
        db = get_db()
        owners = []
        for uid in UNIT_ORDER:
            owner_data = _build_owner(
                uid,
                d["kosten"],
                d["vorauszahlungen"][uid],
                d["bka1_ges_betrag"],
                d["owner_bka1"][uid],
                editable=False,
                gesamt_override=d["owner_gesamt"][uid],
            )
            # Look up actual Nachzahlung payment in the transaction DB
            nachzahlung_val = owner_data.get("nachzahlung")
            if nachzahlung_val is not None and nachzahlung_val >= 0.50:
                tolerance = max(abs(nachzahlung_val) * 0.03, 2.0)
                txs = await db.transactions.find(
                    {
                        "owner_unit": uid,
                        "amount": {"$gte": nachzahlung_val - tolerance, "$lte": nachzahlung_val + tolerance},
                        "is_fehlbuchung": {"$ne": True},
                        "booking_date": {"$gte": "2024-07-01"},
                    }
                ).sort("booking_date", 1).limit(1).to_list(1)
                if txs:
                    tx = txs[0]
                    bd = tx["booking_date"]
                    if isinstance(bd, str):
                        bd = _date.fromisoformat(bd)
                    cross_year = bd.year != 2024
                    owner_data["nachzahlung_status"] = {
                        "status": "paid_late" if cross_year else "paid",
                        "date": bd.isoformat(),
                        "cross_year": cross_year,
                    }
                else:
                    owner_data["nachzahlung_status"] = {"status": "pending"}
            elif nachzahlung_val is not None and nachzahlung_val <= -0.50:
                # Rückzahlung – look for outgoing payment to this owner
                tolerance = max(abs(nachzahlung_val) * 0.03, 2.0)
                last_name = OWNERS_META[uid]["name"].split()[-1]
                rtxs = await db.transactions.find(
                    {
                        "amount": {"$gte": nachzahlung_val - tolerance, "$lte": nachzahlung_val + tolerance},
                        "is_fehlbuchung": {"$ne": True},
                        "booking_date": {"$gte": "2024-07-01"},
                        "counterparty_name": {"$regex": last_name, "$options": "i"},
                    }
                ).sort("booking_date", 1).limit(1).to_list(1)
                if rtxs:
                    tx = rtxs[0]
                    bd = tx["booking_date"]
                    if isinstance(bd, str):
                        bd = _date.fromisoformat(bd)
                    cross_year = bd.year != 2024
                    owner_data["nachzahlung_status"] = {
                        "status": "refunded_late" if cross_year else "refunded",
                        "date": bd.isoformat(),
                        "cross_year": cross_year,
                    }
                else:
                    owner_data["nachzahlung_status"] = {"status": "refund_pending"}
            else:
                owner_data["nachzahlung_status"] = None
            owners.append(owner_data)
        return {
            "year": 2024,
            "editable": False,
            "bka1_ges_betrag": d["bka1_ges_betrag"],
            "kosten": d["kosten"],
            "owners": owners,
        }

    if year == 2025:
        db = get_db()
        doc = await db.abrechnungen.find_one({"year": 2025}, {"_id": 0})
        bka1_ges   = doc.get("bka1_ges_betrag") if doc else None
        owner_bka1 = doc.get("owner_bka1", {})  if doc else {}

        # ---------------------------------------------------------------------------
        # Dynamische Kostenberechnung aus kategorisierten Buchungen
        # ---------------------------------------------------------------------------
        year_start, year_end = "2025-01-01", "2025-12-31"
        base_filter = {
            "account_number": "6023543",
            "is_fehlbuchung": {"$ne": True},
            "booking_date": {"$gte": year_start, "$lte": year_end},
        }

        async def _sum_haupttyp(ht: str) -> float:
            txs = await db.transactions.find(
                {**base_filter, "haupttyp": ht}, {"amount": 1}
            ).to_list(None)
            return round(abs(sum(t["amount"] for t in txs)), 2)

        witter_aus_buchungen        = await _sum_haupttyp("Abrechnung Witter")
        instandhaltung_aus_buchungen = await _sum_haupttyp("Instandhaltung Objekt")

        # DB-Überschreibungen haben höchste Priorität, dann Buchungen, dann Fallback
        witter_override        = doc.get("witter_override")        if doc else None
        instandhaltung_override = doc.get("instandhaltung_override") if doc else None

        witter_val        = witter_override        if witter_override is not None \
                            else (witter_aus_buchungen        if witter_aus_buchungen        else DATA_2025_BASE["kosten"]["witter"])
        instandhaltung_val = instandhaltung_override if instandhaltung_override is not None \
                            else (instandhaltung_aus_buchungen if instandhaltung_aus_buchungen else DATA_2025_BASE["kosten"]["instandhaltung"])

        kosten = {
            **DATA_2025_BASE["kosten"],
            "witter":        witter_val,
            "instandhaltung": instandhaltung_val,
        }
        kosten_quellen = {
            "witter":        "manuell" if witter_override is not None else ("buchungen" if witter_aus_buchungen else "fallback"),
            "instandhaltung": "manuell" if instandhaltung_override is not None else ("buchungen" if instandhaltung_aus_buchungen else "fallback"),
        }
        owners = []
        for uid in UNIT_ORDER:
            owners.append(_build_owner(
                uid,
                kosten,
                DATA_2025_BASE["vorauszahlungen"][uid],
                bka1_ges,
                owner_bka1.get(uid),
                editable=True,
            ))
        return {
            "year": 2025,
            "editable": True,
            "bka1_ges_betrag": bka1_ges,
            "kosten": kosten,
            "kosten_quellen": kosten_quellen,
            "owners": owners,
        }

    return {"error": f"Jahrgang {year} nicht vorhanden"}


@router.put("/{year}")
async def update_abrechnung(year: int, body: AbrechnungUpdate):
    if year != 2025:
        return {"error": "Nur 2025 ist bearbeitbar"}

    db = get_db()
    update_fields: dict = {"year": year}
    if body.bka1_ges_betrag is not None:
        update_fields["bka1_ges_betrag"] = body.bka1_ges_betrag
    if body.witter_override is not None:
        update_fields["witter_override"] = body.witter_override
    if body.instandhaltung_override is not None:
        update_fields["instandhaltung_override"] = body.instandhaltung_override
    # Always overwrite owner_bka1 with the submitted values (None-values are dropped)
    cleaned = {k: v for k, v in body.owner_bka1.items() if v is not None}
    if cleaned:
        update_fields["owner_bka1"] = cleaned

    await db.abrechnungen.update_one(
        {"year": year},
        {"$set": update_fields},
        upsert=True,
    )
    return await get_abrechnung(year)
