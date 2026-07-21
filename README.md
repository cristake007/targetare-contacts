# Targetare Contacts

Aplicație Flask pentru importul unei liste XLSX sau CSV de firme și interogarea manuală, firmă cu firmă, a adreselor de email și numerelor de telefon din API-ul Targetare.ro.

## Funcții MVP

- import XLSX din prima foaie de calcul;
- import CSV cu separator virgulă, punct și virgulă, tab sau `|`;
- detectare automată a coloanelor pentru denumire, CUI și adresă;
- normalizare CUI (`RO 12.345.678` devine `12345678`);
- tabel cu 100 de firme pe pagină;
- buton **Interoghează** pentru fiecare firmă;
- salvarea automată a contactelor și progresului în XLSX;
- document activ persistent după refresh și restart;
- merge după CUI la reîncărcare, fără ștergerea rezultatelor existente;
- backup automat înainte ca documentul activ să fie înlocuit.

## Documentul activ

Câmpul HTML de upload se golește automat după refresh, deoarece browserul nu permite păstrarea unei selecții locale. Acesta nu mai reprezintă starea aplicației.

După încărcare, interfața afișează separat:

- numele fișierului activ;
- faptul că acesta rămâne activ după refresh;
- butonul de descărcare cu același nume de fișier.

Fișierul activ este păstrat în directorul local `instance`. La repornirea serverului, aplicația îl citește automat și reconstruiește tabelul, fără o încărcare nouă.

Interogarea este blocată dacă documentul activ lipsește sau nu poate fi citit.

## Protecția rezultatelor la reîncărcare

Aplicația folosește trei coloane:

- `Emailuri Targetare`;
- `Telefoane Targetare`;
- `Status interogare`.

Dacă este încărcată din nou o copie mai veche a aceluiași XLSX, aplicația compară firmele după CUI și păstrează contactele și statusurile deja existente în documentul activ sau în baza sesiunii curente. Rezultatele nu mai sunt șterse prin simpla reîncărcare a fișierului.

Înainte de înlocuirea documentului activ se creează și o copie de siguranță:

```text
instance/firme-targetare.backup.xlsx
```

După fiecare interogare, XLSX-ul este scris primul. Baza SQLite este actualizată numai dacă salvarea în XLSX reușește.

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

## Format XLSX

Prima foaie trebuie să conțină un rând de antet cu denumirea firmei și CUI-ul. Adresa este opțională.

| Denumire | Cod unic inregistrare | Adresa | Emailuri Targetare | Telefoane Targetare | Status interogare |
|---|---|---|---|---|---|
| EXEMPLU SRL | RO12345678 | București | office@exemplu.ro | +40700000000 | Interogat |

Aplicația caută antetul în primele 25 de rânduri.

## Teste

```bash
pip install -r requirements-dev.txt
pytest
```

Această versiune este destinată rulării locale sau într-o rețea privată. Nu o publica direct pe internet fără autentificare și protecție suplimentară.
