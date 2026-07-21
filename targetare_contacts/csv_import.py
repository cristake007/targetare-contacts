from __future__ import annotations

import csv
import io
import re
from dataclasses import dataclass
from typing import BinaryIO


class CSVImportError(ValueError):
    pass


@dataclass(frozen=True)
class CompanyRow:
    company_name: str
    tax_id: str
    original_address: str
    source_row: int


@dataclass(frozen=True)
class ImportReport:
    imported: int
    duplicates: int
    invalid_tax_ids: int


ALIASES = {
    "company_name": {
        "company name",
        "company_name",
        "denumire",
        "denumire firma",
        "denumire societate",
        "nume companie",
        "nume firma",
        "firma",
        "name",
    },
    "tax_id": {
        "cui",
        "cod unic inregistrare",
        "cod unic de inregistrare",
        "cod fiscal",
        "tax id",
        "tax_id",
        "taxid",
    },
    "address": {
        "address",
        "adresa",
        "adresa sediu",
        "adresa sediului social",
        "sediu social",
    },
}


def _normalize_header(value: str) -> str:
    value = value.strip().lower()
    translations = str.maketrans("ăâîșşțţ", "aaisstt")
    value = value.translate(translations)
    value = re.sub(r"[_\-]+", " ", value)
    return re.sub(r"\s+", " ", value)


def normalize_tax_id(value: object) -> str:
    raw = str(value or "").strip().upper()
    raw = re.sub(r"^RO\s*", "", raw)
    return re.sub(r"\D", "", raw)


def _find_column(headers: list[str], alias_group: str, required: bool) -> str | None:
    normalized = {_normalize_header(header): header for header in headers}
    for alias in ALIASES[alias_group]:
        if alias in normalized:
            return normalized[alias]
    if required:
        available = ", ".join(headers)
        raise CSVImportError(
            f"Nu am găsit coloana pentru {alias_group}. Coloane detectate: {available}."
        )
    return None


def parse_companies_csv(stream: BinaryIO) -> tuple[list[CompanyRow], ImportReport]:
    raw = stream.read()
    if not raw:
        raise CSVImportError("Fișierul CSV este gol.")

    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        try:
            text = raw.decode("cp1250")
        except UnicodeDecodeError as exc:
            raise CSVImportError("Fișierul trebuie să fie UTF-8 sau Windows-1250.") from exc

    sample = text[:8192]
    try:
        dialect = csv.Sniffer().sniff(sample, delimiters=",;\t|")
        reader = csv.DictReader(io.StringIO(text), dialect=dialect)
    except csv.Error:
        reader = csv.DictReader(io.StringIO(text), delimiter=";")

    headers = [header for header in (reader.fieldnames or []) if header]
    if not headers:
        raise CSVImportError("Fișierul nu conține un rând de antet valid.")

    name_column = _find_column(headers, "company_name", required=True)
    tax_id_column = _find_column(headers, "tax_id", required=True)
    address_column = _find_column(headers, "address", required=False)

    rows: list[CompanyRow] = []
    seen_tax_ids: set[str] = set()
    duplicates = 0
    invalid_tax_ids = 0

    for source_row, record in enumerate(reader, start=2):
        tax_id = normalize_tax_id(record.get(tax_id_column))
        if not tax_id or len(tax_id) > 10:
            invalid_tax_ids += 1
            continue
        if tax_id in seen_tax_ids:
            duplicates += 1
            continue

        company_name = str(record.get(name_column) or "").strip()
        if not company_name:
            company_name = f"Firmă CUI {tax_id}"

        address = str(record.get(address_column) or "").strip() if address_column else ""
        rows.append(
            CompanyRow(
                company_name=company_name,
                tax_id=tax_id,
                original_address=address,
                source_row=source_row,
            )
        )
        seen_tax_ids.add(tax_id)

    if not rows:
        raise CSVImportError("Nu am găsit nicio firmă cu un CUI valid.")

    return rows, ImportReport(
        imported=len(rows), duplicates=duplicates, invalid_tax_ids=invalid_tax_ids
    )
