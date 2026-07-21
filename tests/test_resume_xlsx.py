import io

from openpyxl import Workbook

from targetare_contacts import create_app
from targetare_contacts.db import get_db
from targetare_contacts.targetare import InterrogationResult


def make_app(tmp_path, name):
    return create_app(
        {
            "TESTING": True,
            "DATABASE": str(tmp_path / f"{name}.sqlite3"),
            "ACTIVE_WORKBOOK": str(tmp_path / f"{name}.xlsx"),
            "TARGETARE_API_KEY": "secret",
            "SECRET_KEY": "test",
        }
    )


def make_source_xlsx():
    workbook = Workbook()
    worksheet = workbook.active
    worksheet.append(["Denumire", "CUI", "Adresa"])
    worksheet.append(["ACME SRL", "RO12345678", "Bucuresti"])
    stream = io.BytesIO()
    workbook.save(stream)
    workbook.close()
    stream.seek(0)
    return stream


def test_downloaded_xlsx_restores_contacts_in_a_new_session(tmp_path, monkeypatch):
    first_app = make_app(tmp_path, "first")
    first_client = first_app.test_client()
    first_client.post(
        "/upload",
        data={"file": (make_source_xlsx(), "companies.xlsx")},
        content_type="multipart/form-data",
    )

    class FakeClient:
        def __init__(self, **_kwargs):
            pass

        def interrogate(self, tax_id):
            assert tax_id == "12345678"
            return InterrogationResult(
                status="success",
                emails={"primaryEmail": "office@example.ro", "websiteEmails": []},
                phones={"primaryPhone": "+40700000000", "verifiedPhones": []},
                remaining_requests=50,
            )

    monkeypatch.setattr("targetare_contacts.TargetareClient", FakeClient)

    with first_app.app_context():
        company_id = get_db().execute("SELECT id FROM companies").fetchone()["id"]

    first_client.post(f"/companies/{company_id}/interrogate")
    download = first_client.get("/download")
    assert download.status_code == 200

    second_app = make_app(tmp_path, "second")
    second_client = second_app.test_client()
    response = second_client.post(
        "/upload",
        data={"file": (io.BytesIO(download.data), "companies.xlsx")},
        content_type="multipart/form-data",
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert b"office@example.ro" in response.data
    assert b"+40700000000" in response.data
    assert b"success" in response.data
    assert b"Fi\xc8\x99ier activ" in response.data
