"""
Witter Heizkosten-Abrechnung Berechnungsgrundlage
API zum Speichern und Abrufen der jährlichen Eingabedaten für das Witter-Formular.
"""
from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional, List
from ..database import get_db

router = APIRouter(prefix="/api/witter", tags=["witter"])

# ---------------------------------------------------------------------------
# Pydantic-Modelle (entsprechen exakt den Spalten im Witter-Formular)
# ---------------------------------------------------------------------------

class NebenkostenRow(BaseModel):
    kategorie: str
    lieferant: Optional[str] = None
    nr: Optional[str] = None
    rechnungsdatum: Optional[str] = None
    betrag_brutto: Optional[float] = None
    gesamtbetrag: Optional[float] = None       # nur bei Mischrechnung
    anteil_arbeitskosten: Optional[float] = None
    whg_nr: Optional[str] = None               # Umlagebereift Whg.Nr.

class Brennstoffeinkauf(BaseModel):
    datum: Optional[str] = None
    menge: Optional[float] = None
    betrag_brutto: Optional[float] = None

class Brennstoffkosten(BaseModel):
    vorjahresbestand_datum: Optional[str] = None
    vorjahresbestand_menge: Optional[float] = None
    vorjahresbestand_betrag: Optional[float] = None
    einkaufe: List[Brennstoffeinkauf] = []
    jahresendbestand_menge: Optional[float] = None

class StammdatenHeizung(BaseModel):
    brennstoffart: str = "Heizöl"              # Heizöl | Erdgas | Pellets | Flüssiggas
    mengeneinheit: str = "Liter"               # Liter | m³ | kWh | kg
    heizwert: Optional[float] = 10             # kWh je Einheit
    emissionsfaktor: Optional[float] = None    # kg CO₂/kWh
    warmwasser_grundkostenanteil: float = 30.0 # %
    heizung_grundkostenanteil: float = 30.0    # %
    warmwasser_temperatur: int = 55            # °C

class HeiznebenRow(BaseModel):
    kategorie: str
    datum: Optional[str] = None
    nr: Optional[str] = None
    betrag_brutto: Optional[float] = None
    gesamtbetrag: Optional[float] = None
    anteil_arbeitskosten: Optional[float] = None

class WohnungsnutzerRow(BaseModel):
    whg_nr: str
    lage: str
    eigentuemer: str
    nutzer: Optional[str] = None
    wohnflaeche: float
    beheizte_wohnflaeche: float
    personen: int = 0
    vorauszahlungen: Optional[float] = None
    einzug: Optional[str] = None               # bei Nutzerwechsel
    auszug: Optional[str] = None

class WitterData(BaseModel):
    year: int
    # Kopfdaten
    kundennummer: str = "25737"
    von: Optional[str] = None
    bis: Optional[str] = None
    # Formular-Seite 3: Wohnungsnutzer
    wohnungsnutzer: List[WohnungsnutzerRow] = []
    # Formular-Seite 1: Nebenkosten (Haushaltsbezogene NK)
    nebenkosten: List[NebenkostenRow] = []
    # Formular-Seite 1: Wasserkosten
    wasserkosten: List[NebenkostenRow] = []
    # Formular-Seite 2: Heizkosten – Stammdaten
    stammdaten_heizung: StammdatenHeizung = StammdatenHeizung()
    # Formular-Seite 2: Brennstoffkosten
    brennstoffkosten: Brennstoffkosten = Brennstoffkosten()
    # Formular-Seite 2: Heiznebenkosten
    heiznebenkosten: List[HeiznebenRow] = []

# ---------------------------------------------------------------------------
# Werte 2024 als Referenz (handschriftlich aus dem gescannten Formular)
# ---------------------------------------------------------------------------

REF_2024: dict = {
    "year": 2024,
    "kundennummer": "25737",
    "von": "2024-01-01",
    "bis": "2024-12-31",
    "wohnungsnutzer": [
        {"whg_nr": "01", "lage": "EG II",    "eigentuemer": "Patrignani", "nutzer": "Patrignani", "wohnflaeche": 69.99, "beheizte_wohnflaeche": 69.99, "personen": 0, "vorauszahlungen": 2856.00},
        {"whg_nr": "02", "lage": "EG re",    "eigentuemer": "Lösch",      "nutzer": "Lösch",      "wohnflaeche": 71.60, "beheizte_wohnflaeche": 71.60, "personen": 0, "vorauszahlungen": 2184.00},
        {"whg_nr": "03", "lage": "1. OG II", "eigentuemer": "Horn",       "nutzer": "Müller",     "wohnflaeche": 56.92, "beheizte_wohnflaeche": 56.92, "personen": 0, "vorauszahlungen": 2136.00},
        {"whg_nr": "04", "lage": "1. OG re", "eigentuemer": "Schmach",    "nutzer": "Spielhofen", "wohnflaeche": 78.88, "beheizte_wohnflaeche": 78.88, "personen": 0, "vorauszahlungen": 2820.00},
        {"whg_nr": "05", "lage": "Keller",   "eigentuemer": "Lösch",      "nutzer": "Lösch",      "wohnflaeche": 40.17, "beheizte_wohnflaeche": 40.17, "personen": 0, "vorauszahlungen": 1044.00},
    ],
    "nebenkosten": [
        {"kategorie": "Hausverwaltung",                    "lieferant": "Autopark Systems/Frontgas", "nr": None, "rechnungsdatum": None, "betrag_brutto": 159.20,  "gesamtbetrag": None, "anteil_arbeitskosten": None, "whg_nr": None},
        {"kategorie": "Sach- und Haftpflichtversicherung", "lieferant": None,                        "nr": None, "rechnungsdatum": None, "betrag_brutto": 484.81,  "gesamtbetrag": None, "anteil_arbeitskosten": None, "whg_nr": None},
        {"kategorie": "Grundsteuer",                       "lieferant": None,                        "nr": None, "rechnungsdatum": None, "betrag_brutto": None,    "gesamtbetrag": None, "anteil_arbeitskosten": None, "whg_nr": None},
        {"kategorie": "Gemeinschaftsstrom",                "lieferant": None,                        "nr": None, "rechnungsdatum": None, "betrag_brutto": 75.55,   "gesamtbetrag": None, "anteil_arbeitskosten": None, "whg_nr": None},
        {"kategorie": "Müllentsorgung",                    "lieferant": None,                        "nr": None, "rechnungsdatum": None, "betrag_brutto": None,    "gesamtbetrag": None, "anteil_arbeitskosten": None, "whg_nr": None},
    ],
    "wasserkosten": [
        {"kategorie": "Frischwasserkosten",                              "lieferant": None, "nr": None, "rechnungsdatum": None, "betrag_brutto": 478.88, "gesamtbetrag": None, "anteil_arbeitskosten": None, "whg_nr": None},
        {"kategorie": "Abwassergebühren",                                "lieferant": None, "nr": None, "rechnungsdatum": None, "betrag_brutto": 373.25, "gesamtbetrag": None, "anteil_arbeitskosten": None, "whg_nr": None},
        {"kategorie": "Miet-/Wartungsgebühren für Kaltwasserzähler",    "lieferant": None, "nr": None, "rechnungsdatum": None, "betrag_brutto": 223.09, "gesamtbetrag": None, "anteil_arbeitskosten": None, "whg_nr": None},
    ],
    "stammdaten_heizung": {
        "brennstoffart": "Heizöl",
        "mengeneinheit": "Liter",
        "heizwert": 10,
        "emissionsfaktor": None,
        "warmwasser_grundkostenanteil": 30.0,
        "heizung_grundkostenanteil": 30.0,
        "warmwasser_temperatur": 55,
    },
    "brennstoffkosten": {
        "vorjahresbestand_datum": "2024-05-10",
        "vorjahresbestand_menge": 5250.0,
        "vorjahresbestand_betrag": 6774.02,
        "einkaufe": [
            {"datum": "2024-05-10", "menge": 3503.0, "betrag_brutto": 33258.34},
        ],
        "jahresendbestand_menge": 5000.0,
    },
    "heiznebenkosten": [
        {"kategorie": "Kaminfeger/Schornsteinfeger",            "datum": "2024-05-14", "nr": None, "betrag_brutto": 116.62, "gesamtbetrag": 116.62, "anteil_arbeitskosten": None},
        {"kategorie": "Betriebsstrom (nicht Warmstrom)",        "datum": None,         "nr": None, "betrag_brutto": None,   "gesamtbetrag": None,   "anteil_arbeitskosten": None},
        {"kategorie": "Reinigungskosten der Heizungsanlage",    "datum": None,         "nr": None, "betrag_brutto": None,   "gesamtbetrag": None,   "anteil_arbeitskosten": None},
        {"kategorie": "Wartungskosten (keine Reparaturkosten)", "datum": None,         "nr": None, "betrag_brutto": 22.53,  "gesamtbetrag": None,   "anteil_arbeitskosten": None},
        {"kategorie": "Mietgebühren",                           "datum": None,         "nr": None, "betrag_brutto": 116.62, "gesamtbetrag": None,   "anteil_arbeitskosten": None},
        {"kategorie": "Wartungsgebühren",                       "datum": None,         "nr": None, "betrag_brutto": 63.95,  "gesamtbetrag": None,   "anteil_arbeitskosten": None},
    ],
}

# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get("/ref/2024")
async def get_ref_2024():
    """Referenzwerte aus dem gescannten 2024er Witter-Formular (read-only)."""
    return REF_2024


@router.get("/{year}")
async def get_witter(year: int):
    """
    Gibt die gespeicherten Witter-Eingabedaten für ein Jahr zurück.
    Falls nicht vorhanden, wird ein leeres Template zurückgegeben.
    """
    db = get_db()
    doc = await db.witter_data.find_one({"year": year}, {"_id": 0})
    if doc:
        return doc

    # Leeres Template aus den Strukturdaten aufbauen
    template = WitterData(
        year=year,
        von=f"{year}-01-01",
        bis=f"{year}-12-31",
        wohnungsnutzer=[
            WohnungsnutzerRow(whg_nr="01", lage="EG II",    eigentuemer="Patrignani", nutzer="Patrignani", wohnflaeche=69.99, beheizte_wohnflaeche=69.99, personen=0, vorauszahlungen=None),
            WohnungsnutzerRow(whg_nr="02", lage="EG re",    eigentuemer="Lösch",      nutzer="Lösch",      wohnflaeche=71.60, beheizte_wohnflaeche=71.60, personen=0, vorauszahlungen=None),
            WohnungsnutzerRow(whg_nr="03", lage="1. OG II", eigentuemer="Horn",       nutzer="Müller",     wohnflaeche=56.92, beheizte_wohnflaeche=56.92, personen=0, vorauszahlungen=None),
            WohnungsnutzerRow(whg_nr="04", lage="1. OG re", eigentuemer="Schmach",    nutzer="Spielhofen", wohnflaeche=78.88, beheizte_wohnflaeche=78.88, personen=0, vorauszahlungen=None),
            WohnungsnutzerRow(whg_nr="05", lage="Keller",   eigentuemer="Lösch",      nutzer="Lösch",      wohnflaeche=40.17, beheizte_wohnflaeche=40.17, personen=0, vorauszahlungen=None),
        ],
        nebenkosten=[
            NebenkostenRow(kategorie="Hausverwaltung"),
            NebenkostenRow(kategorie="Sach- und Haftpflichtversicherung"),
            NebenkostenRow(kategorie="Grundsteuer"),
            NebenkostenRow(kategorie="Gemeinschaftsstrom"),
            NebenkostenRow(kategorie="Müllentsorgung"),
        ],
        wasserkosten=[
            NebenkostenRow(kategorie="Frischwasserkosten"),
            NebenkostenRow(kategorie="Abwassergebühren"),
            NebenkostenRow(kategorie="Miet-/Wartungsgebühren für Kaltwasserzähler"),
        ],
        stammdaten_heizung=StammdatenHeizung(),
        brennstoffkosten=Brennstoffkosten(einkaufe=[Brennstoffeinkauf()]),
        heiznebenkosten=[
            HeiznebenRow(kategorie="Kaminfeger/Schornsteinfeger"),
            HeiznebenRow(kategorie="Betriebsstrom (nicht Warmstrom)"),
            HeiznebenRow(kategorie="Reinigungskosten der Heizungsanlage"),
            HeiznebenRow(kategorie="Wartungskosten (keine Reparaturkosten)"),
            HeiznebenRow(kategorie="Mietgebühren"),
            HeiznebenRow(kategorie="Wartungsgebühren"),
        ],
    )
    return template.model_dump()


@router.put("/{year}")
async def save_witter(year: int, data: WitterData):
    """Speichert / überschreibt die Witter-Eingabedaten für ein Jahr."""
    db = get_db()
    payload = data.model_dump()
    payload["year"] = year
    await db.witter_data.update_one(
        {"year": year},
        {"$set": payload},
        upsert=True,
    )
    return payload


# ---------------------------------------------------------------------------
# Prefill from transactions
# ---------------------------------------------------------------------------

# Mapping rules: list of (kategorie, list_name, matcher_fn)
# matcher_fn(counterparty_name: str, purpose: str) -> bool
_NEBENKOSTEN_RULES = [
    ("Hausverwaltung",                    "nebenkosten",   lambda n, p: "witter" in n),
    ("Sach- und Haftpflichtversicherung", "nebenkosten",   lambda n, p: "versicherung" in n or "versicherungs" in n),
    ("Grundsteuer",                       "nebenkosten",   lambda n, p: "finanzamt" in n or "grundsteuer" in p),
    ("Gemeinschaftsstrom",                "nebenkosten",   lambda n, p: "strom" in p and "gemeinschaft" in p),
    ("Müllentsorgung",                    "nebenkosten",   lambda n, p: "müll" in p or "entsorgung" in p or "abfall" in p),
    ("Frischwasserkosten",                "wasserkosten",  lambda n, p: "weilachgruppe" in n or "wasservers" in n or ("frischwasser" in p)),
    ("Abwassergebühren",                  "wasserkosten",  lambda n, p: "abwasser" in p or "kanalbenütz" in p or "abwassergeb" in p),
    ("Miet-/Wartungsgebühren für Kaltwasserzähler", "wasserkosten", lambda n, p: "zähler" in p and ("miete" in p or "wartung" in p)),
]

_HEIZNEBENKOSTEN_RULES = [
    ("Kaminfeger/Schornsteinfeger",       lambda n, p: "kaminfeger" in n or "schornstein" in n or "kamin" in p),
    ("Betriebsstrom (nicht Warmstrom)",   lambda n, p: "betriebsstrom" in p or ("strom" in p and "heiz" in p) or "e.on" in n or "eon energie" in n or "e on energie" in n),
    ("Reinigungskosten der Heizungsanlage", lambda n, p: "reinigung" in p and ("heiz" in p or "anlage" in p)),
    ("Wartungskosten (keine Reparaturkosten)", lambda n, p: "wartung" in p or "wartungsvertrag" in p),
    ("Mietgebühren",                      lambda n, p: ("miete" in p or "mietgebühr" in p) and not "wasser" in p),
    ("Wartungsgebühren",                  lambda n, p: "wartungsgebühr" in p),
]

# Owner unit → form Whg.-Nr. mapping
_UNIT_TO_WHGNR = {"WE-001": "01", "WE-002": "02", "WE-003": "03", "WE-004": "04", "WE-005": "05"}

# For owners whose DB entry covers multiple Witter rows, split amounts by row.
# Format: {unit_id: [(whg_nr, monthly_rate), ...]}
# (Lösch WE-002 covers both the main apartment "02" and the Keller "05")
_UNIT_MULTI_SPLIT: dict[str, list[tuple[str, float]]] = {
    "WE-002": [("02", 182.0), ("05", 87.0)],
}


@router.get("/{year}/prefill")
async def prefill_witter(year: int):
    """
    Leitet Formularfelder automatisch aus den Buchungen ab.
    Gibt ein partielles WitterData-Objekt zurück (nur die Felder die ermittelt wurden).
    Der Client merged diese Daten in das bestehende Formular.
    """
    db = get_db()
    year_start = f"{year}-01-01"
    year_end = f"{year}-12-31"

    # ── Fetch all expense transactions (outgoing) for the year from operating account ──
    expense_txs = await db.transactions.find({
        "account_number": "6023543",
        "booking_date": {"$gte": year_start, "$lte": year_end},
        "amount": {"$lt": 0},
        "is_fehlbuchung": {"$ne": True},
    }).sort("booking_date", 1).to_list(None)

    # ── Load owner monthly_hausgeld for Vorauszahlungen (× 12 = expected annual) ──
    owners_list = await db.owners.find(
        {}, {"unit_id": 1, "monthly_hausgeld": 1, "last_name": 1}
    ).sort("unit_id", 1).to_list(None)

    # ── Build Nebenkosten + Wasserkosten from expense transactions ──
    # Strategy: prefer stored haupttyp/untertyp fields (from expense_classifier);
    # fall back to keyword rules for uncategorised transactions.
    nk_map: dict[str, dict] = {}  # kategorie → {betrag, lieferant, rechnungsdatum, nr, list_name}
    hk_map: dict[str, dict] = {}  # kategorie → {betrag, datum, nr}
    brennstoff_txs: list[dict] = []  # individual Brennstoffeinkauf transactions

    # Untertyp → Witter-Formular Kategoriename mapping (stored subcategory → form label)
    _UNTERTYP_TO_WITTER_NK: dict[str, tuple[str, str]] = {
        "Gemeinschaftsstrom":             ("Gemeinschaftsstrom", "nebenkosten"),
        "Müllentsorgung":                 ("Müllentsorgung", "nebenkosten"),
        "Grundsteuer":                    ("Grundsteuer", "nebenkosten"),
        "Sach- und Haftpflichtversicherung": ("Sach- und Haftpflichtversicherung", "nebenkosten"),
        "Brennstoffeinkauf":              ("Brennstoffeinkauf", "brennstoffkosten"),
        "Miet- oder Wartungsgebühren":    ("Miet-/Wartungsgebühren für Kaltwasserzähler", "wasserkosten"),
        "Hausverwalterhonorar":           ("Hausverwaltung", "nebenkosten"),
        "Frischwasserkosten":             ("Frischwasserkosten", "wasserkosten"),
        "Abwasserkosten":                 ("Abwassergebühren", "wasserkosten"),
    }
    _UNTERTYP_TO_WITTER_HK: dict[str, str] = {
        "Kaminfeger/Schornsteinfeger":    "Kaminfeger/Schornsteinfeger",
        "Betriebsstrom":                  "Betriebsstrom (nicht Warmstrom)",
        "Reinigungskosten":               "Reinigungskosten der Heizungsanlage",
        "Wartungskosten":                 "Wartungskosten (keine Reparaturkosten)",
        "Mietgebühren":                   "Mietgebühren",
        "Wartungsgebühren":               "Wartungsgebühren",
    }

    for tx in expense_txs:
        name = (tx.get("counterparty_name") or "").lower().strip()
        purp = (tx.get("purpose") or "").lower().strip()
        amt = abs(tx["amount"])
        bd = tx["booking_date"] if isinstance(tx["booking_date"], str) else tx["booking_date"].isoformat()

        # Prefer stored untertyp from expense_classifier
        stored_cat = tx.get("haupttyp") or ""
        stored_sub = tx.get("untertyp") or ""

        matched = False

        # Try stored category first
        if stored_sub:
            if stored_sub in _UNTERTYP_TO_WITTER_NK:
                witter_label, list_name = _UNTERTYP_TO_WITTER_NK[stored_sub]
                if witter_label not in nk_map:
                    nk_map[witter_label] = {
                        "kategorie": witter_label,
                        "list_name": list_name,
                        "betrag_brutto": 0.0,
                        "lieferant": tx.get("counterparty_name"),
                        "rechnungsdatum": None,
                        "nr": None,
                        "_count": 0,
                        "_last_date": bd,
                        "_last_purpose": tx.get("purpose", ""),
                    }
                row = nk_map[witter_label]
                row["betrag_brutto"] = round(row["betrag_brutto"] + amt, 2)
                row["_count"] += 1
                row["_last_date"] = bd
                row["_last_purpose"] = tx.get("purpose", "")
                # Track individual Brennstoffeinkauf entries for the Berechnungsgrundlage
                if list_name == "brennstoffkosten":
                    brennstoff_txs.append({"datum": bd, "betrag_brutto": amt})
                matched = True
            elif stored_sub in _UNTERTYP_TO_WITTER_HK:
                witter_label = _UNTERTYP_TO_WITTER_HK[stored_sub]
                if witter_label not in hk_map:
                    hk_map[witter_label] = {"kategorie": witter_label, "betrag_brutto": 0.0, "datum": bd, "_count": 0}
                row = hk_map[witter_label]
                row["betrag_brutto"] = round(row["betrag_brutto"] + amt, 2)
                row["datum"] = bd
                row["_count"] += 1
                matched = True

        if not matched:
            # Fallback to keyword rules
            for kategorie, list_name, fn in _NEBENKOSTEN_RULES:
                if fn(name, purp):
                    if kategorie not in nk_map:
                        nk_map[kategorie] = {
                            "kategorie": kategorie,
                            "list_name": list_name,
                            "betrag_brutto": 0.0,
                            "lieferant": tx.get("counterparty_name"),
                            "rechnungsdatum": None,
                            "nr": None,
                            "_count": 0,
                            "_last_date": bd,
                            "_last_purpose": tx.get("purpose", ""),
                        }
                    row = nk_map[kategorie]
                    row["betrag_brutto"] = round(row["betrag_brutto"] + amt, 2)
                    row["_count"] += 1
                    row["_last_date"] = bd
                    row["_last_purpose"] = tx.get("purpose", "")
                    matched = True
                    break

        if not matched:
            for kategorie, fn in _HEIZNEBENKOSTEN_RULES:
                if fn(name, purp):
                    if kategorie not in hk_map:
                        hk_map[kategorie] = {
                            "kategorie": kategorie,
                            "betrag_brutto": 0.0,
                            "datum": bd,
                            "_count": 0,
                        }
                    row = hk_map[kategorie]
                    row["betrag_brutto"] = round(row["betrag_brutto"] + amt, 2)
                    row["datum"] = bd
                    row["_count"] += 1
                    break

    # Always populate rechnungsdatum from last booking date; extract Nr. for single invoices
    for row in nk_map.values():
        row["rechnungsdatum"] = row["_last_date"]
        if row["_count"] == 1:
            # Extract invoice reference from purpose (first token that looks like a ref)
            purpose = row["_last_purpose"]
            import re as _re
            ref_m = _re.search(r"(r[aemn][-_]?\d{3,}[-\w]*|\d{4,}[-/]\d{2,}|\b[A-Z]{2,}-\d{4,}\b)", purpose, _re.IGNORECASE)
            if ref_m:
                row["nr"] = ref_m.group(1)

    # ── Vorauszahlungen per owner: monthly_hausgeld × 12 (expected annual amount) ──
    vorausz: dict[str, float] = {}
    for owner in owners_list:
        unit = owner.get("unit_id")
        monthly = owner.get("monthly_hausgeld") or 0.0
        if not unit or not monthly:
            continue
        if unit in _UNIT_MULTI_SPLIT:
            # Owner covers multiple Witter rows – use per-row monthly rates
            for whg_nr, monthly_rate in _UNIT_MULTI_SPLIT[unit]:
                vorausz[whg_nr] = round(monthly_rate * 12, 2)
        else:
            whg_nr = _UNIT_TO_WHGNR.get(unit)
            if whg_nr:
                vorausz[whg_nr] = round(monthly * 12, 2)

    # ── Assemble result ──
    result: dict = {
        "year": year,
        "nebenkosten": [],
        "wasserkosten": [],
        "heiznebenkosten": [],
        "wohnungsnutzer_vorauszahlungen": {},
        "_sources": {},   # debug info: which counterparty/sum matched each row
    }

    for kategorie in ["Hausverwaltung", "Sach- und Haftpflichtversicherung", "Grundsteuer", "Gemeinschaftsstrom", "Müllentsorgung"]:
        row = nk_map.get(kategorie)
        result["nebenkosten"].append({
            "kategorie": kategorie,
            "betrag_brutto": row["betrag_brutto"] if row else None,
            "lieferant": row["lieferant"] if row else None,
            "rechnungsdatum": row["rechnungsdatum"] if row else None,
            "nr": row["nr"] if row else None,
            "_matched": bool(row),
            "_count": row["_count"] if row else 0,
        })

    for kategorie in ["Frischwasserkosten", "Abwassergebühren", "Miet-/Wartungsgebühren für Kaltwasserzähler"]:
        row = nk_map.get(kategorie)
        result["wasserkosten"].append({
            "kategorie": kategorie,
            "betrag_brutto": row["betrag_brutto"] if row else None,
            "lieferant": row["lieferant"] if row else None,
            "rechnungsdatum": row["rechnungsdatum"] if row else None,
            "nr": row["nr"] if row else None,
            "_matched": bool(row),
            "_count": row["_count"] if row else 0,
        })

    for kategorie in ["Kaminfeger/Schornsteinfeger", "Betriebsstrom (nicht Warmstrom)", "Reinigungskosten der Heizungsanlage", "Wartungskosten (keine Reparaturkosten)", "Mietgebühren", "Wartungsgebühren"]:
        row = hk_map.get(kategorie)
        result["heiznebenkosten"].append({
            "kategorie": kategorie,
            "betrag_brutto": row["betrag_brutto"] if row else None,
            "datum": row["datum"] if row else None,
            "nr": None,
            "_matched": bool(row),
            "_count": row["_count"] if row else 0,
        })

    # vorausz is already keyed by whg_nr
    result["wohnungsnutzer_vorauszahlungen"] = vorausz

    # Brennstoffkosten: individual Einkäufe from categorised transactions (Berechnungsgrundlage Seite 2)
    if brennstoff_txs:
        result["brennstoffkosten"] = {
            "einkaufe": [{"datum": t["datum"], "menge": None, "betrag_brutto": t["betrag_brutto"]} for t in brennstoff_txs],
            "_matched": True,
            "_count": len(brennstoff_txs),
            "_total": round(sum(t["betrag_brutto"] for t in brennstoff_txs), 2),
        }

    return result
