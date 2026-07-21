from __future__ import annotations

from .csv_import import CompanyRow, normalize_import_status

_STATUS_RANK = {
    "not_queried": 0,
    "error": 1,
    "partial": 2,
    "success": 3,
}


def _unique_tuple(*groups: tuple[str, ...]) -> tuple[str, ...]:
    result: list[str] = []
    seen: set[str] = set()
    for group in groups:
        for value in group:
            item = str(value or "").strip()
            key = item.casefold()
            if item and key not in seen:
                result.append(item)
                seen.add(key)
    return tuple(result)


def _best_status(*statuses: str, emails: tuple[str, ...], phones: tuple[str, ...]) -> str:
    best = max(
        statuses,
        key=lambda value: _STATUS_RANK.get(value, 0),
        default="not_queried",
    )
    return normalize_import_status(best, emails, phones)


def merge_company_rows(
    incoming_rows: list[CompanyRow],
    preserved_rows: list[CompanyRow],
) -> tuple[list[CompanyRow], int]:
    preserved_by_cui = {row.tax_id: row for row in preserved_rows}
    merged: list[CompanyRow] = []
    restored = 0

    for incoming in incoming_rows:
        previous = preserved_by_cui.get(incoming.tax_id)
        if previous is None:
            merged.append(incoming)
            continue

        emails = _unique_tuple(incoming.imported_emails, previous.imported_emails)
        phones = _unique_tuple(incoming.imported_phones, previous.imported_phones)
        status = _best_status(
            incoming.imported_status,
            previous.imported_status,
            emails=emails,
            phones=phones,
        )

        if (
            emails != incoming.imported_emails
            or phones != incoming.imported_phones
            or status != incoming.imported_status
        ):
            restored += 1

        merged.append(
            CompanyRow(
                company_name=incoming.company_name,
                tax_id=incoming.tax_id,
                original_address=incoming.original_address,
                source_row=incoming.source_row,
                imported_emails=emails,
                imported_phones=phones,
                imported_status=status,
            )
        )

    return merged, restored
