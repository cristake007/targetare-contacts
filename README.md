# Targetare Contacts

Aplicație Flask pentru importul unei liste CSV de firme și interogarea manuală, firmă cu firmă, a adreselor de email și numerelor de telefon din API-ul Targetare.ro.

## Funcții MVP

- import CSV cu separator virgulă, punct și virgulă, tab sau `|`;
- detectare automată a coloanelor pentru denumire, CUI și adresă;
- normalizare CUI (`RO 12.345.678` devine `12345678`);
- eliminarea duplicatelor după CUI;
- tabel paginat și căutare după denumire/CUI;
- buton **Interoghează** pentru fiecare firmă;
- două cereri API per firmă: `/emails` și `/phones`;
- salvarea rezultatelor și a erorilor în SQLite.

Un import nou înlocuiește lista curentă.

## Pornire locală

```bash
python -m venv .venv
```

Windows PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
```

Completează `TARGETARE_API_KEY` în `.env`, apoi rulează:

```powershell
flask --app app run --debug
```

Deschide `http://127.0.0.1:5000`.

## Format CSV

Exemplu:

```csv
Denumire;Cod unic inregistrare;Adresa
EXEMPLU SRL;RO12345678;București
```

Adresa este opțională și este afișată doar ca referință. Interogarea se face exclusiv după CUI.

## Teste

```bash
pip install -r requirements-dev.txt
pytest
```

## Utilizare

Această versiune este destinată rulării locale sau într-o rețea privată. Nu o publica direct pe internet fără autentificare și protecție suplimentară.