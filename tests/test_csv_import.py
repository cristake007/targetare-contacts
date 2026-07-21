import io

import pytest

from targetare_contacts.csv_import import CSVImportError, normalize_tax_id, parse_companies_csv


def test_normalize_tax_id_removes_ro_and_separators():
    assert normalize_tax_id("RO 12.345.678") == "12345678"


def test_parse_semicolon_csv_with_romanian_headers():
    content = (
        "Denumire;Cod unic inregistrare;Adresa\n"
        "ACME SRL;RO 12345678;Bucuresti\n"
        "ACME DUP;12345678;Cluj\n"
        "Invalid SRL;abc;Iasi\n"
    ).encode("utf-8")

    rows, report = parse_companies_csv(io.BytesIO(content))

    assert len(rows) == 1
    assert rows[0].company_name == "ACME SRL"
    assert rows[0].tax_id == "12345678"
    assert report.duplicates == 1
    assert report.invalid_tax_ids == 1


def test_missing_cui_column_is_rejected():
    content = "Denumire;Adresa\nACME SRL;Bucuresti\n".encode("utf-8")
    with pytest.raises(CSVImportError, match="tax_id"):
        parse_companies_csv(io.BytesIO(content))
