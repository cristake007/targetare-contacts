from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from io import BytesIO
from pathlib import Path

from flask import Flask, flash, redirect, render_template, request, send_file, url_for

from .csv_import import CSVImportError, parse_companies_csv
from .db import close_db, get_db, init_db
from .targetare import TargetareClient
from .xlsx_file import (
    WorkbookUpdateError,
    create_xlsx_from_rows,
    prepare_uploaded_xlsx,
    write_company_contacts,
)
from .xlsx_import import XLSXImportError, parse_companies_xlsx


def _decode_list(value: str | None) -> list[str]:
    if not value:
        return []
    try:
        parsed = json.loads(value)
    except (TypeError, json.JSONDecodeError):
        return []
    return [str(item) for item in parsed if item]


def _unique_values(*values: object) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for value in values:
        if not value:
            continue
        item = str(value).strip()
        key = item.casefold()
        if item and key not in seen:
            result.append(item)
            seen.add(key)
    return result


def _result_emails(payload: dict | None) -> list[str] | None:
    if payload is None:
        return None
    return _unique_values(
        payload.get("primaryEmail"),
        payload.get("secondaryEmail"),
        payload.get("contactEmail"),
        *(payload.get("websiteEmails") or []),
    )


def _result_phones(payload: dict | None) -> list[str] | None:
    if payload is None:
        return None
    return _unique_values(
        payload.get("primaryPhone"),
        payload.get("secondaryPhone"),
        *(payload.get("contactPhones") or []),
        *(payload.get("websitePhones") or []),
        *(payload.get("verifiedPhones") or []),
    )


def create_app(test_config: dict | None = None) -> Flask:
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_mapping(
        SECRET_KEY=os.getenv("FLASK_SECRET_KEY", "dev-change-me"),
        DATABASE=str(Path(app.instance_path) / "targetare_contacts.sqlite3"),
        ACTIVE_WORKBOOK=str(Path(app.instance_path) / "firme-targetare.xlsx"),
        MAX_CONTENT_LENGTH=10 * 1024 * 1024,
        TARGETARE_API_KEY=os.getenv("TARGETARE_API_KEY", ""),
        TARGETARE_API_BASE_URL=os.getenv(
            "TARGETARE_API_BASE_URL", "https://api.targetare.ro/v1"
        ),
        TARGETARE_TIMEOUT_SECONDS=float(
            os.getenv("TARGETARE_TIMEOUT_SECONDS", "15")
        ),
        COMPANIES_PER_PAGE=100,
    )

    if test_config:
        app.config.update(test_config)

    Path(app.instance_path).mkdir(parents=True, exist_ok=True)
    app.teardown_appcontext(close_db)

    with app.app_context():
        init_db()

    @app.get("/")
    def index():
        page = max(request.args.get("page", 1, type=int), 1)
        query = request.args.get("q", "").strip()
        per_page = app.config["COMPANIES_PER_PAGE"]
        offset = (page - 1) * per_page

        db = get_db()
        params: list[object] = []
        where = ""
        if query:
            where = "WHERE company_name LIKE ? OR tax_id LIKE ?"
            like = f"%{query}%"
            params.extend([like, like])

        total = db.execute(
            f"SELECT COUNT(*) AS count FROM companies {where}", params
        ).fetchone()["count"]
        company_rows = db.execute(
            f"""
            SELECT * FROM companies
            {where}
            ORDER BY source_row ASC, id ASC
            LIMIT ? OFFSET ?
            """,
            [*params, per_page, offset],
        ).fetchall()

        companies = []
        for row in company_rows:
            company = dict(row)
            company["all_emails"] = _unique_values(
                company.get("primary_email"),
                company.get("secondary_email"),
                company.get("contact_email"),
                *_decode_list(company.get("website_emails")),
            )
            company["all_phones"] = _unique_values(
                company.get("primary_phone"),
                company.get("secondary_phone"),
                *_decode_list(company.get("contact_phones")),
                *_decode_list(company.get("website_phones")),
                *_decode_list(company.get("verified_phones")),
            )
            companies.append(company)

        total_pages = max((total + per_page - 1) // per_page, 1)
        if page > total_pages and total:
            return redirect(url_for("index", page=total_pages, q=query))

        return render_template(
            "index.html",
            companies=companies,
            page=page,
            total_pages=total_pages,
            total=total,
            query=query,
            api_configured=bool(app.config["TARGETARE_API_KEY"]),
            workbook_available=Path(app.config["ACTIVE_WORKBOOK"]).is_file(),
        )

    @app.post("/upload")
    def upload_companies():
        uploaded = request.files.get("file")
        if not uploaded or not uploaded.filename:
            flash("Selectează un fișier XLSX sau CSV.", "error")
            return redirect(url_for("index"))

        extension = Path(uploaded.filename).suffix.lower()
        if extension not in {".xlsx", ".csv"}:
            flash("Fișierul trebuie să aibă extensia .xlsx sau .csv.", "error")
            return redirect(url_for("index"))

        raw = uploaded.read()
        if not raw:
            flash("Fișierul încărcat este gol.", "error")
            return redirect(url_for("index"))

        try:
            if extension == ".xlsx":
                rows, report = parse_companies_xlsx(BytesIO(raw))
                prepare_uploaded_xlsx(raw, app.config["ACTIVE_WORKBOOK"])
            else:
                rows, report = parse_companies_csv(BytesIO(raw))
                create_xlsx_from_rows(rows, app.config["ACTIVE_WORKBOOK"])
        except (CSVImportError, XLSXImportError, WorkbookUpdateError) as exc:
            flash(str(exc), "error")
            return redirect(url_for("index"))

        db = get_db()
        with db:
            db.execute("DELETE FROM companies")
            db.executemany(
                """
                INSERT INTO companies (company_name, tax_id, original_address, source_row)
                VALUES (?, ?, ?, ?)
                """,
                [
                    (row.company_name, row.tax_id, row.original_address, row.source_row)
                    for row in rows
                ],
            )

        message = (
            f"Au fost importate {report.imported} firme. "
            "Fișierul XLSX de lucru a fost pregătit pentru salvarea contactelor."
        )
        if report.duplicates or report.invalid_tax_ids:
            message += (
                f" Omise: {report.duplicates} duplicate și "
                f"{report.invalid_tax_ids} CUI-uri invalide."
            )
        flash(message, "success")
        return redirect(url_for("index"))

    @app.get("/download")
    def download_xlsx():
        workbook_path = Path(app.config["ACTIVE_WORKBOOK"])
        if not workbook_path.is_file():
            flash("Nu există încă un fișier XLSX actualizat.", "error")
            return redirect(url_for("index"))

        return send_file(
            workbook_path,
            as_attachment=True,
            download_name="firme-targetare.xlsx",
            mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )

    @app.post("/companies/<int:company_id>/interrogate")
    def interrogate_company(company_id: int):
        page = max(request.args.get("page", 1, type=int), 1)
        query = request.args.get("q", "").strip()
        db = get_db()
        company = db.execute(
            "SELECT * FROM companies WHERE id = ?", (company_id,)
        ).fetchone()

        if company is None:
            flash("Firma nu mai există în lista curentă.", "error")
            return redirect(url_for("index", page=page, q=query))

        if not app.config["TARGETARE_API_KEY"]:
            flash("Configurează TARGETARE_API_KEY înainte de interogare.", "error")
            return redirect(url_for("index", page=page, q=query))

        client = TargetareClient(
            api_key=app.config["TARGETARE_API_KEY"],
            base_url=app.config["TARGETARE_API_BASE_URL"],
            timeout=app.config["TARGETARE_TIMEOUT_SECONDS"],
        )
        result = client.interrogate(company["tax_id"])
        email_values = _result_emails(result.emails)
        phone_values = _result_phones(result.phones)

        updates: dict[str, object] = {
            "lookup_status": result.status,
            "error_message": " | ".join(result.errors) if result.errors else None,
            "remaining_requests": result.remaining_requests,
            "queried_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        }

        if result.emails is not None:
            updates.update(
                primary_email=result.emails.get("primaryEmail"),
                secondary_email=result.emails.get("secondaryEmail"),
                contact_email=result.emails.get("contactEmail"),
                website_emails=json.dumps(result.emails.get("websiteEmails") or []),
            )

        if result.phones is not None:
            updates.update(
                primary_phone=result.phones.get("primaryPhone"),
                secondary_phone=result.phones.get("secondaryPhone"),
                contact_phones=json.dumps(result.phones.get("contactPhones") or []),
                website_phones=json.dumps(result.phones.get("websitePhones") or []),
                verified_phones=json.dumps(result.phones.get("verifiedPhones") or []),
            )

        assignments = ", ".join(f"{column} = ?" for column in updates)
        with db:
            db.execute(
                f"UPDATE companies SET {assignments} WHERE id = ?",
                [*updates.values(), company_id],
            )

        workbook_error: str | None = None
        if email_values is not None or phone_values is not None:
            try:
                write_company_contacts(
                    app.config["ACTIVE_WORKBOOK"],
                    company["source_row"],
                    email_values,
                    phone_values,
                )
            except WorkbookUpdateError as exc:
                workbook_error = str(exc)

        if workbook_error:
            flash(
                f"Contactele au fost salvate în aplicație, dar nu și în XLSX: {workbook_error}",
                "warning",
            )
        elif result.status == "success":
            flash(
                f"{company['company_name']} a fost interogată și salvată automat în XLSX.",
                "success",
            )
        elif result.status == "partial":
            flash(
                "Interogare parțială. Datele disponibile au fost salvate automat în XLSX.",
                "warning",
            )
        else:
            flash("Interogarea a eșuat. Vezi mesajul din tabel.", "error")

        return redirect(
            url_for(
                "index", page=page, q=query, _anchor=f"company-{company_id}"
            )
        )

    @app.get("/health")
    def health():
        return {"status": "ok"}

    return app
