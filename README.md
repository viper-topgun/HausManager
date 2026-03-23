# HausManager – WEG Tulpenstr. 31, Hilgertshausen-Tandern

Web-basierte Hausverwaltungssoftware für kleine Eigentümergemeinschaften.

## Architektur

```
┌─────────────┐   Port 80    ┌──────────────┐   /api/*  ┌──────────────┐
│    Nginx    │ ──────────── │   SvelteKit   │           │    FastAPI   │
│  (Reverse   │              │   Frontend    │           │   Backend    │
│   Proxy)    │              │   Port 3000   │           │   Port 8000  │
└─────────────┘              └──────────────┘           └──────┬───────┘
                                                                │
                                                         ┌──────▼───────┐
                                                         │   MongoDB    │
                                                         │   Port 27017 │
                                                         └──────────────┘
```

### Stack
| Schicht | Technologie |
|---------|-------------|
| Datenbank | MongoDB 4.4 |
| Backend | Python 3.12 + FastAPI + motor (async) |
| Frontend | SvelteKit 1.x + Svelte 4 + Tailwind CSS |
| Webserver | Nginx 1.27 |
| Deployment | Docker Compose |

## Erste Schritte

### 1. Starten
```bash
docker compose up -d
```

### 2. Datenbank befüllen
Öffnen Sie http://localhost → Import → Schritt 1: Stammdaten anlegen

Dann: Schritt 2: Lokale Dateien importieren (liest automatisch aus `./Data/`)

### 3. Anwendung nutzen
http://localhost

## Features

- **Dashboard** – Kontostände, Hausgeld-Übersicht, letzte Buchungen
- **Eigentümer** – Verwaltung der WE-Einheiten mit IBAN und Hausgeld-Betrag
- **Konten** – Betriebskonto (6023543) + Rücklagenkonto (6023550)
- **Buchungen** – Vollständige Buchungshistorie mit Filtern
- **Hausgeld-Kontrolle** – Monatliche Zahlungsmatrix pro Eigentümer, Nachzahlungen
- **Ausgaben** – Kategorisierte Ausgaben-Übersicht nach Kostenträger
- **Import** – StarMoney Deluxe TXT-Import (SEPA CSV-Format)

## Eigentümer (WEG Tulpenstr. 31)

| Einheit | Name | Monatl. Hausgeld |
|---------|------|-----------------|
| WE-001 | Veronika Patrignani | 238,00 € |
| WE-002 + Büro 005 | Siegfried Losch | 269,00 € |
| WE-003 | Horn Enrico und Bianca | 178,00 € |
| WE-004 | Christian Schmach | 235,00 € |

## Neue StarMoney-Dateien importieren

Entweder:
- Datei nach `./Data/` kopieren → Import → „Lokale Dateien importieren"
- Oder: Import → „Neue Datei hochladen" → Konto wählen → TXT-Datei hochladen

## Erweiterung

### Backend (Python/FastAPI)
- Neue Router: `backend/app/routers/`
- Neue Services: `backend/app/services/`
- Neue Modelle: `backend/app/models/`

### Frontend (Svelte)
- Neue Seiten: `frontend/src/routes/`
- Gemeinsame Komponenten: `frontend/src/lib/components/`

### Rebuild nach Änderungen
```bash
docker compose build && docker compose up -d
```

## API-Dokumentation (Swagger)
http://localhost/api/docs
