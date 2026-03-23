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
