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


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get("/{year}")
async def get_abrechnung(year: int):
    if year == 2024:
        d = DATA_2024
        owners = []
        for uid in UNIT_ORDER:
            owners.append(_build_owner(
                uid,
                d["kosten"],
                d["vorauszahlungen"][uid],
                d["bka1_ges_betrag"],
                d["owner_bka1"][uid],
                editable=False,
                gesamt_override=d["owner_gesamt"][uid],
            ))
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

        kosten = DATA_2025_BASE["kosten"]
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
