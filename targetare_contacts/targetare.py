from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import requests


@dataclass(frozen=True)
class InterrogationResult:
    status: str
    emails: dict[str, Any] | None = None
    phones: dict[str, Any] | None = None
    remaining_requests: int | None = None
    errors: list[str] = field(default_factory=list)


class TargetareAPIError(RuntimeError):
    pass


class TargetareClient:
    def __init__(
        self,
        api_key: str,
        base_url: str = "https://api.targetare.ro/v1",
        timeout: float = 15,
        session: requests.Session | None = None,
    ) -> None:
        if not api_key.strip():
            raise ValueError("Targetare API key is required")
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.session = session or requests.Session()
        self.session.headers.update(
            {
                "Authorization": f"Bearer {api_key.strip()}",
                "Accept": "application/json",
                "User-Agent": "targetare-contacts/0.1",
            }
        )

    def _get(self, path: str) -> tuple[dict[str, Any], int | None]:
        try:
            response = self.session.get(
                f"{self.base_url}/{path.lstrip('/')}", timeout=self.timeout
            )
        except requests.RequestException as exc:
            raise TargetareAPIError(f"Eroare de rețea: {exc}") from exc

        try:
            payload = response.json()
        except ValueError as exc:
            raise TargetareAPIError(
                f"API-ul a răspuns cu date invalide (HTTP {response.status_code})."
            ) from exc

        if not response.ok or payload.get("success") is False:
            error = payload.get("error") or {}
            message = error.get("message") or f"HTTP {response.status_code}"
            raise TargetareAPIError(str(message))

        data = payload.get("data")
        if not isinstance(data, dict):
            raise TargetareAPIError("Răspunsul API nu conține obiectul data.")

        remaining = payload.get("remainingRequests")
        return data, remaining if isinstance(remaining, int) else None

    def interrogate(self, tax_id: str) -> InterrogationResult:
        emails: dict[str, Any] | None = None
        phones: dict[str, Any] | None = None
        errors: list[str] = []
        remaining_values: list[int] = []

        try:
            emails, remaining = self._get(f"companies/{tax_id}/emails")
            if remaining is not None:
                remaining_values.append(remaining)
        except TargetareAPIError as exc:
            errors.append(f"Email: {exc}")

        try:
            phones, remaining = self._get(f"companies/{tax_id}/phones")
            if remaining is not None:
                remaining_values.append(remaining)
        except TargetareAPIError as exc:
            errors.append(f"Telefon: {exc}")

        successful_calls = int(emails is not None) + int(phones is not None)
        status = "success" if successful_calls == 2 else "partial" if successful_calls else "error"

        return InterrogationResult(
            status=status,
            emails=emails,
            phones=phones,
            remaining_requests=min(remaining_values) if remaining_values else None,
            errors=errors,
        )
