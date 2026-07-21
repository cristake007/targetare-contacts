from __future__ import annotations

import os
from io import BytesIO
from pathlib import Path
from typing import Iterable

from openpyxl import Workbook, load_workbook

from .csv_import import CompanyRow
from .xlsx_import import _find_header_row

EMAIL_HEADER = "Emailuri Targetare"
PHONE_HEADER = "Telefoane Targetare"


class WorkbookUpdateError(RuntimeError):
    pass


def _unique_text(values: Iterable[object]) -> str:
    result: list[str] = []
    seen: set[str] = set()
    for value in values:
        item = str(value or "").strip()
        key = item.casefold()
        if item and key not in seen:
            result.append(item)
            seen.add(key)
    return "; ".join(result)


def _ensure_contact_columns(worksheet, header_row: int) -> tuple[int, int]:
    email_column: int | None = None
    phone_column: int | None = None
    last_header_column = 0

    for cell in worksheet[header_row]:
        value = str(cell.value or "").strip()
        if value:
            last_header_column = max(last_header_column, cell.column)
        normalized = value.casefold()
        if normalized == EMAIL_HEADER.casefold():
            email_column = cell.column
        elif normalized == PHONE_HEADER.casefold():
            phone_column = cell.column

    next_column = last_header_column + 1
    if email_column is None:
        email_column = next_column
        worksheet.cell(row=header_row, column=email_column, value=EMAIL_HEADER)
        next_column += 1
    if phone_column is None:
        phone_column = next_column
        worksheet.cell(row=header_row, column=phone_column, value=PHONE_HEADER)

    return email_column, phone_column


def _save_atomic(workbook, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_name(f".{destination.name}.tmp.xlsx")
    try:
        workbook.save(temporary)
        os.replace(temporary, destination)
    except Exception as exc:
        raise WorkbookUpdateError(f"Nu am putut salva fișierul XLSX: {exc}") from exc
    finally:
        if temporary.exists():
            temporary.unlink(missing_ok=True)


def prepare_uploaded_xlsx(raw: bytes, destination: str | Path) -> None:
    try:
        workbook = load_workbook(BytesIO(raw))
    except Exception as exc:
        raise WorkbookUpdateError(
            "Fișierul XLSX nu a putut fi pregătit pentru salvare."
        ) from exc

    try:
        worksheet = workbook[workbook.sheetnames[0]]
        header_row, _headers = _find_header_row(worksheet)
        _ensure_contact_columns(worksheet, header_row)
        _save_atomic(workbook, Path(destination))
    finally:
        workbook.close()


def create_xlsx_from_rows(rows: list[CompanyRow], destination: str | Path) -> None:
    workbook = Workbook()
    try:
        worksheet = workbook.active
        worksheet.title = "Companii"
        worksheet.append(["Denumire", "Cod unic inregistrare", "Adresa"])
        for row in rows:
            worksheet.cell(row=row.source_row, column=1, value=row.company_name)
            worksheet.cell(row=row.source_row, column=2, value=row.tax_id)
            worksheet.cell(row=row.source_row, column=3, value=row.original_address)
        _ensure_contact_columns(worksheet, 1)
        _save_atomic(workbook, Path(destination))
    finally:
        workbook.close()


def write_company_contacts(
    workbook_path: str | Path,
    source_row: int,
    emails: list[str] | None,
    phones: list[str] | None,
) -> None:
    path = Path(workbook_path)
    if not path.is_file():
        raise WorkbookUpdateError("Fișierul XLSX activ nu mai există.")

    try:
        workbook = load_workbook(BytesIO(path.read_bytes()))
    except Exception as exc:
        raise WorkbookUpdateError("Fișierul XLSX activ nu poate fi deschis.") from exc

    try:
        worksheet = workbook[workbook.sheetnames[0]]
        header_row, _headers = _find_header_row(worksheet)
        email_column, phone_column = _ensure_contact_columns(worksheet, header_row)

        if emails is not None:
            worksheet.cell(
                row=source_row,
                column=email_column,
                value=_unique_text(emails),
            )
        if phones is not None:
            worksheet.cell(
                row=source_row,
                column=phone_column,
                value=_unique_text(phones),
            )

        _save_atomic(workbook, path)
    finally:
        workbook.close()
