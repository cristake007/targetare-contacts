import io

from targetare_contacts import create_app
from targetare_contacts.db import get_db
from targetare_contacts.targetare import InterrogationResult


def make_app(tmp_path):
    database = tmp_path / "test.sqlite3"
    return create_app(
        {
            "TESTING": True,
            "DATABASE": str(database),
            "TARGETARE_API_KEY": "secret",
            "SECRET_KEY": "test",
        }
    )


def test_upload_and_list_csv(tmp_path):
    app = make_app(tmp_path)
    client = app.test_client()
    csv_data = "Denumire;CUI;Adresa\nACME SRL;RO12345678;Bucuresti\n"

    response = client.post(
        "/upload",
        data={"file": (io.BytesIO(csv_data.encode()), "companies.csv")},
        content_type="multipart/form-data",
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert b"ACME SRL" in response.data
    assert b"12345678" in response.data


def test_interrogate_company_saves_results(tmp_path, monkeypatch):
    app = make_app(tmp_path)

    class FakeClient:
        def __init__(self, **_kwargs):
            pass

        def interrogate(self, tax_id):
            assert tax_id == "12345678"
            return InterrogationResult(
                status="success",
                emails={"primaryEmail": "office@example.ro", "websiteEmails": []},
                phones={"primaryPhone": "+40700000000", "verifiedPhones": []},
                remaining_requests=98,
            )

    monkeypatch.setattr("targetare_contacts.TargetareClient", FakeClient)

    with app.app_context():
        db = get_db()
        db.execute(
            "INSERT INTO companies (company_name, tax_id, original_address, source_row) VALUES (?, ?, ?, ?)",
            ("ACME SRL", "12345678", "Bucuresti", 2),
        )
        db.commit()
        company_id = db.execute("SELECT id FROM companies").fetchone()["id"]

    response = app.test_client().post(
        f"/companies/{company_id}/interrogate", follow_redirects=True
    )

    assert response.status_code == 200
    assert b"office@example.ro" in response.data
    assert b"+40700000000" in response.data
    assert b"98 cereri" in response.data
