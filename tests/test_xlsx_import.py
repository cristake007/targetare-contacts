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
    assert rows[0].imported_status == "not_queried"
    assert report.duplicates == 1
    assert report.invalid_tax_ids == 1


def test_parse_xlsx_restores_contacts_and_interrogation_status():
    stream = build_workbook(
        [
            [
                "Denumire",
                "CUI",
                "Adresa",
                "Emailuri Targetare",
                "Telefoane Targetare",
                "Status interogare",
            ],
            [
                "ACME SRL",
                "RO12345678",
                "Bucuresti",
                "office@example.ro; sales@example.ro",
                "+40700000000; +40210000000",
                "Interogat",
            ],
        ]
    )

    rows, report = parse_companies_xlsx(stream)

    assert report.imported == 1
    assert rows[0].imported_emails == (
        "office@example.ro",
        "sales@example.ro",
    )
    assert rows[0].imported_phones == (
        "+40700000000",
        "+40210000000",
    )
    assert rows[0].imported_status == "success"


def test_contacts_imply_interrogated_when_old_file_has_no_status_column():
    stream = build_workbook(
        [
            ["Denumire", "CUI", "Emailuri Targetare"],
            ["ACME SRL", "12345678", "office@example.ro"],
        ]
    )

    rows, _report = parse_companies_xlsx(stream)

    assert rows[0].imported_emails == ("office@example.ro",)
    assert rows[0].imported_status == "success"


def test_xlsx_without_required_headers_is_rejected():
    stream = build_workbook([["Denumire", "Adresa"], ["ACME SRL", "Bucuresti"]])

    with pytest.raises(XLSXImportError, match="rând de antet"):
        parse_companies_xlsx(stream)
