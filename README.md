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
- salvarea automată a contactelor și progresului în XLSX;
- restaurarea automată a stării la reîncărcarea aceluiași XLSX;
- descărcarea fișierului actualizat din interfață.

## XLSX-ul este sursa de adevăr

Aplicația folosește trei coloane pentru a păstra rezultatele și progresul:

- `Emailuri Targetare`;
- `Telefoane Targetare`;
- `Status interogare`.

După fiecare interogare, datele sunt scrise pe rândul firmei, iar statusul devine `Interogat`, `Parțial` sau `Eroare`.

La următoarea sesiune:

1. încarcă XLSX-ul actualizat descărcat anterior;
2. aplicația citește cele trei coloane;
3. contactele reapar în tabel;
4. firmele deja procesate sunt marcate și au butonul **Reinteroghează**;
5. poți continua de unde ai rămas.

Dacă un XLSX mai vechi are deja emailuri sau telefoane, dar nu are coloana `Status interogare`, aplicația adaugă această coloană și marchează automat acele rânduri ca `Interogat`.

Browserul nu poate modifica direct fișierul original aflat pe calculator. Butonul **Descarcă XLSX actualizat** returnează copia care trebuie păstrată și reîncărcată data viitoare.

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

| Denumire | Cod unic inregistrare | Adresa | Emailuri Targetare | Telefoane Targetare | Status interogare |
|---|---|---|---|---|---|
| EXEMPLU SRL | RO12345678 | București | office@exemplu.ro | +40700000000 | Interogat |

Aplicația caută rândul de antet în primele 25 de rânduri, astfel încât fișierul poate conține câteva rânduri introductive înaintea tabelului.

## Format CSV alternativ

```csv
Denumire;Cod unic inregistrare;Adresa;Emailuri Targetare;Telefoane Targetare;Status interogare
EXEMPLU SRL;RO12345678;București;office@exemplu.ro;+40700000000;Interogat
```

Pentru un import CSV, aplicația generează automat o copie XLSX de lucru. Interogarea se face exclusiv după CUI.

## Teste

```bash
pip install -r requirements-dev.txt
pytest
```

## Utilizare

Această versiune este destinată rulării locale sau într-o rețea privată. Nu o publica direct pe internet fără autentificare și protecție suplimentară.
