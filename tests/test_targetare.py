from targetare_contacts.targetare import TargetareClient


class FakeResponse:
    def __init__(self, payload, status_code=200):
        self._payload = payload
        self.status_code = status_code
        self.ok = 200 <= status_code < 300

    def json(self):
        return self._payload


class FakeSession:
    def __init__(self, responses):
        self.responses = list(responses)
        self.headers = {}
        self.calls = []

    def get(self, url, timeout):
        self.calls.append((url, timeout))
        return self.responses.pop(0)


def test_interrogate_combines_email_and_phone_results():
    session = FakeSession(
        [
            FakeResponse(
                {
                    "success": True,
                    "remainingRequests": 9,
                    "data": {"primaryEmail": "office@example.ro"},
                }
            ),
            FakeResponse(
                {
                    "success": True,
                    "remainingRequests": 8,
                    "data": {"primaryPhone": "+40700000000"},
                }
            ),
        ]
    )
    client = TargetareClient("secret", session=session)

    result = client.interrogate("12345678")

    assert result.status == "success"
    assert result.emails["primaryEmail"] == "office@example.ro"
    assert result.phones["primaryPhone"] == "+40700000000"
    assert result.remaining_requests == 8
    assert session.headers["Authorization"] == "Bearer secret"


def test_interrogate_keeps_partial_result_when_one_endpoint_fails():
    session = FakeSession(
        [
            FakeResponse(
                {"success": False, "error": {"message": "Not found"}},
                status_code=404,
            ),
            FakeResponse(
                {
                    "success": True,
                    "remainingRequests": 7,
                    "data": {"primaryPhone": "+40700000000"},
                }
            ),
        ]
    )
    client = TargetareClient("secret", session=session)

    result = client.interrogate("12345678")

    assert result.status == "partial"
    assert result.emails is None
    assert result.phones["primaryPhone"] == "+40700000000"
    assert result.errors == ["Email: Not found"]
