# Targetare Contacts

Aplicație Flask pentru importul unei liste XLSX sau CSV de firme și interogarea manuală, firmă cu firmă, a adreselor de email și numerelor de telefon din API-ul Targetare.ro.

## Funcții MVP

- import XLSX din prima foaie de calcul;
- import CSV cu separator virgulă, punct și virgulă, tab sau `|`;
- detectare automată a coloanelor pentru denumire, CUI și adresă;
- normalizare CUI (`RO 12.345.678` devine `12345678`);
- acceptarea CUI-ului stocat în Excel ca text sau număr;
- eliminarea duplicatelor după CUI;
- tabel cu 100 de firme pe pagină și căutare după denumire/CUI;
- buton **Interoghează** pentru fiecare firmă;
- două cereri API per firmă: `/emails` și `/phones`;
- salvarea rezultatelor și a erorilor în SQLite;
- salvarea automată a contactelor în copia XLSX de lucru;
- descărcarea fișierului actualizat din interfață.

Un import nou înlocuiește lista și fișierul XLSX de lucru curente.

## Salvarea rezultatelor în XLSX

La încărcare, aplicația creează în directorul local `instance` o copie de lucru numită `firme-targetare.xlsx`. Fișierul original de pe calculator nu este modificat direct de browser.

Aplicația adaugă sau reutilizează două coloane:

- `Emailuri Targetare`;
- `Telefoane Targetare`.

După fiecare interogare reușită sau parțială, datele disponibile sunt scrise automat pe rândul firmei. Valorile multiple sunt separate prin `;` și duplicatele sunt eliminate.

Butonul **Descarcă XLSX actualizat** returnează întotdeauna ultima copie salvată.

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

## Format XLSX recomandat

Prima foaie trebuie să conțină un rând de antet cu denumirea firmei și CUI-ul. Adresa este opțională.

| Denumire | Cod unic inregistrare | Adresa |
|---|---|---|
| EXEMPLU SRL | RO12345678 | București |

Aplicația caută rândul de antet în primele 25 de rânduri, astfel încât fișierul poate conține câteva rânduri introductive înaintea tabelului.

## Format CSV alternativ

```csv
Denumire;Cod unic inregistrare;Adresa
EXEMPLU SRL;RO12345678;București
```

Pentru un import CSV, aplicația generează automat o copie XLSX de lucru. Adresa importată este afișată doar ca referință. Interogarea se face exclusiv după CUI.

## Teste

```bash
pip install -r requirements-dev.txt
pytest
```

## Utilizare

Această versiune este destinată rulării locale sau într-o rețea privată. Nu o publica direct pe internet fără autentificare și protecție suplimentară.
