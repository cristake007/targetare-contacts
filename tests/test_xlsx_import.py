import io

import pytest
from openpyxl import Workbook

from targetare_contacts.xlsx_import import XLSXImportError, parse_companies_xlsx


def build_workbook(rows):
    workbook = Workbook()
    worksheet = workbook.active
    for row in rows:
        worksheet.append(row)

    stream = io.BytesIO()
    workbook.save(stream)
    workbook.close()
    stream.seek(0)
    return stream


def test_parse_xlsx_with_numeric_cui_and_intro_row():
    stream = build_workbook(
        [
            ["Raport firme"],
            ["Denumire", "Cod unic inregistrare", "Adresa"],
            ["ACME SRL", 12345678, "Bucuresti"],
            ["ACME DUP", "RO12345678", "Cluj"],
            ["Invalid SRL", "abc", "Iasi"],
        ]
    )

    rows, report = parse_companies_xlsx(stream)

    assert len(rows) == 1
    assert rows[0].company_name == "ACME SRL"
    assert rows[0].tax_id == "12345678"
    assert rows[0].original_address == "Bucuresti"
    assert rows[0].source_row == 3
    assert report.duplicates == 1
    assert report.invalid_tax_ids == 1


def test_xlsx_without_required_headers_is_rejected():
    stream = build_workbook([["Denumire", "Adresa"], ["ACME SRL", "Bucuresti"]])

    with pytest.raises(XLSXImportError, match="rând de antet"):
        parse_companies_xlsx(stream)
