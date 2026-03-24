"""
Automatic expense sub-categorization for outgoing transactions.

Taxonomy:
  Haupttyp (category)    →  Untertyp (subcategory)
  ─────────────────────────────────────────────────
  Wasserkosten           →  Frischwasserkosten
                         →  Abwasserkosten
  Nebenkosten            →  Gemeinschaftsstrom
                         →  Müllentsorgung
                         →  Grundsteuer
                         →  Sach- und Haftpflichtversicherung
                         →  Miet- oder Wartungsgebühren
                         →  Wartungskosten
  Brennstoffkosten       →  Brennstoffeinkauf
  Instandhaltung Objekt  →  Reparatur
                         →  Handwerkerkosten
                         →  Sonstige Instandhaltung
  Abrechnung Witter      →  Hausverwalterhonorar
  Heiznebenkosten        →  Kaminfeger/Schornsteinfeger
                         →  Betriebsstrom
                         →  Reinigungskosten
                         →  Wartungskosten
                         →  Mietgebühren
                         →  Wartungsgebühren
"""

from typing import Optional

# ---------------------------------------------------------------------------
# Taxonomy: Haupttyp → list of valid Untertypen
# ---------------------------------------------------------------------------

EXPENSE_TAXONOMY: dict[str, list[str]] = {
    "Wasserkosten": [
        "Frischwasserkosten",
        "Abwasserkosten",
    ],
    "Nebenkosten": [
        "Gemeinschaftsstrom",
        "Müllentsorgung",
        "Grundsteuer",
        "Sach- und Haftpflichtversicherung",
        "Miet- oder Wartungsgebühren",
        "Wartungskosten",
    ],
    "Brennstoffkosten": [
        "Brennstoffeinkauf",
    ],
    "Instandhaltung Objekt": [
        "Reparatur",
        "Handwerkerkosten",
        "Sonstige Instandhaltung",
    ],
    "Abrechnung Witter": [
        "Hausverwalterhonorar",
    ],
    "Heiznebenkosten": [
        "Kaminfeger/Schornsteinfeger",
        "Betriebsstrom",
        "Reinigungskosten",
        "Wartungskosten",
        "Mietgebühren",
        "Wartungsgebühren",
    ],
}


# ---------------------------------------------------------------------------
# Classification rules as plain functions (serializable / importable)
# ---------------------------------------------------------------------------

def _rule_frischwasser(n: str, p: str) -> bool:
    return (
        "weilachgruppe" in n
        or "wasserversorgung" in n
        or "zweckverband weil" in n
        or "frischwasser" in p
    )


def _rule_abwasser(n: str, p: str) -> bool:
    return (
        "abwasser" in p
        or "kanalbenütz" in p
        or "abwassergeb" in p
        or ("gemeinde" in n and ("kanal" in p or "abwasser" in p))
    )


def _rule_gemeinschaftsstrom(n: str, p: str) -> bool:
    # E.ON is the building's heating system electricity (Betriebsstrom), not common-area lighting
    return "strom" in p and "gemeinschaft" in p


def _rule_muell(n: str, p: str) -> bool:
    return (
        "müll" in p
        or "entsorgung" in p
        or "abfallgebühr" in p
        or "abfall" in p
        or ("landkreis" in n and "müll" in p)
    )


def _rule_grundsteuer(n: str, p: str) -> bool:
    return "finanzamt" in n or "grundsteuer" in p or "grundst." in p


def _rule_versicherung(n: str, p: str) -> bool:
    return (
        "versicherung" in n
        or "versicherungs" in n
        or "haftpflicht" in p
        or "vkb" in n
        or "allianz" in n
    )


def _rule_brennstoff(n: str, p: str) -> bool:
    return (
        "heizöl" in p
        or "brennstoff" in p
        or "biomasse" in n
        or ("wärme" in n and "verbund" in n)
        or "brennstoff" in n
    )


def _rule_miet_wartung_wasser(n: str, p: str) -> bool:
    return (
        ("zähler" in p and ("miete" in p or "wartung" in p))
        or "messdienstleistung" in p
        or "mietgebühr" in p and "zähler" in p
    )


def _rule_kaminfeger(n: str, p: str) -> bool:
    return (
        "kaminfeger" in n
        or "schornstein" in n
        or "bezirksschornstein" in n
        or ("kamin" in p and ("feger" in p or "kehrer" in p))
    )


def _rule_betriebsstrom(n: str, p: str) -> bool:
    # E.ON is the heating system electricity supplier for this building
    return (
        "betriebsstrom" in p
        or ("strom" in p and "heiz" in p)
        or "e.on" in n
        or "eon energie" in n
        or "e on energie" in n
    )


def _rule_reinigungskosten(n: str, p: str) -> bool:
    return "reinigung" in p and (
        "heiz" in p or "anlage" in p or "kessel" in p or "brenner" in p
    )


def _rule_wartungskosten(n: str, p: str) -> bool:
    return (
        ("wartung" in p or "heizungswartung" in p)
        and "zähler" not in p
        and "mietgebühr" not in p
    )


def _rule_heiz_mietgebuehren(n: str, p: str) -> bool:
    # Heat meter rental companies (Brunata, Techem, ista, Minol, KWD, Qundis)
    heat_meter_company = (
        "brunata" in n or "techem" in n or "minol" in n
        or "kwd" in n or "qundis" in n or "ista gmbh" in n
    )
    keyword_match = (
        ("miete" in p or "mietgebühr" in p)
        and ("heiz" in p or "heizkessel" in p or "brenner" in p or "zähler" in p)
    )
    return heat_meter_company or keyword_match


def _rule_heiz_wartungsgebuehren(n: str, p: str) -> bool:
    heat_meter_company = (
        "brunata" in n or "techem" in n or "minol" in n
        or "kwd" in n or "qundis" in n or "ista gmbh" in n
    )
    return (
        (heat_meter_company and "wartung" in p)
        or ("wartungsgebühr" in p and ("heiz" in p or "brenner" in p))
    )


def _rule_witter_verwaltung(n: str, p: str) -> bool:
    return "witter" in n


def _rule_instandhaltung_reparatur(n: str, p: str) -> bool:
    return (
        "reparatur" in p
        or "instandsetz" in p
        or "sanierung" in p
        or "reparatur" in n
    )


def _rule_handwerker(n: str, p: str) -> bool:
    return (
        "handwerk" in n
        or "installat" in n
        or "klempner" in n
        or "tischler" in n
        or "maler" in n
        or "dachdeck" in n
        or "elektriker" in n
        or "sanitär" in n
        or "montage" in p
        or "einbau" in p
        or ("austausch" in p and any(k in p for k in ("rohr", "fenster", "tür", "pump")))
    )


def _rule_sonstige_instandhaltung(n: str, p: str) -> bool:
    return (
        "instandhalt" in p
        or "instandhalt" in n
        or "dach" in p and "reparatur" in p
        or "fassade" in p
    )


# ---------------------------------------------------------------------------
# Ordered rules: (haupttyp, untertyp, rule_fn)
# First matching rule wins.
# ---------------------------------------------------------------------------

_RULES: list[tuple[str, str, object]] = [
    # ── Wasserkosten ──────────────────────────────────────────────────────────
    ("Wasserkosten",   "Frischwasserkosten",              _rule_frischwasser),
    ("Wasserkosten",   "Abwasserkosten",                  _rule_abwasser),
    # ── Nebenkosten ───────────────────────────────────────────────────────────
    ("Nebenkosten",       "Gemeinschaftsstrom",               _rule_gemeinschaftsstrom),
    ("Nebenkosten",       "Müllentsorgung",                   _rule_muell),
    ("Nebenkosten",       "Grundsteuer",                      _rule_grundsteuer),
    ("Nebenkosten",       "Sach- und Haftpflichtversicherung", _rule_versicherung),
    ("Nebenkosten",       "Miet- oder Wartungsgebühren",      _rule_miet_wartung_wasser),
    ("Brennstoffkosten",  "Brennstoffeinkauf",                _rule_brennstoff),
    # ── Heiznebenkosten ───────────────────────────────────────────────────────
    ("Heiznebenkosten", "Kaminfeger/Schornsteinfeger",     _rule_kaminfeger),
    ("Heiznebenkosten", "Betriebsstrom",                   _rule_betriebsstrom),
    ("Heiznebenkosten", "Reinigungskosten",                _rule_reinigungskosten),
    ("Heiznebenkosten", "Wartungskosten",                  _rule_wartungskosten),
    ("Heiznebenkosten", "Mietgebühren",                    _rule_heiz_mietgebuehren),
    ("Heiznebenkosten", "Wartungsgebühren",                _rule_heiz_wartungsgebuehren),
    # ── Abrechnung Witter ───────────────────────────────────────────────────────────────────────
    ("Abrechnung Witter",    "Hausverwalterhonorar",         _rule_witter_verwaltung),
    # ── Instandhaltung Objekt ────────────────────────────────────────────────────────────────
    ("Instandhaltung Objekt", "Reparatur",                  _rule_instandhaltung_reparatur),
    ("Instandhaltung Objekt", "Handwerkerkosten",            _rule_handwerker),
    ("Instandhaltung Objekt", "Sonstige Instandhaltung",     _rule_sonstige_instandhaltung),
]


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def classify_expense(
    counterparty_name: str,
    purpose: str,
) -> tuple[Optional[str], Optional[str]]:
    """
    Return (haupttyp, untertyp) for an expense transaction, or (None, None).
    Only makes sense to call for ausgabe-type transactions (amount < 0).
    """
    n = (counterparty_name or "").lower().strip()
    p = (purpose or "").lower().strip()

    for haupttyp, untertyp, fn in _RULES:
        try:
            if fn(n, p):  # type: ignore[operator]
                return haupttyp, untertyp
        except Exception:
            continue

    return None, None


def is_valid_kategorie(haupttyp: str, untertyp: str) -> bool:
    """Check that the given (Haupttyp, Untertyp) combination is in the taxonomy."""
    return untertyp in EXPENSE_TAXONOMY.get(haupttyp, [])
