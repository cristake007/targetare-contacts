from __future__ import annotations

import json
import os
from pathlib import Path


def normalized_xlsx_filename(uploaded_filename: str) -> str:
    safe_name = Path(uploaded_filename).name.strip() or "firme.xlsx"
    suffix = Path(safe_name).suffix.lower()
    if suffix == ".xlsx":
        return safe_name
    return f"{Path(safe_name).stem or 'firme'}.xlsx"


def save_active_filename(metadata_path: str | Path, filename: str) -> None:
    path = Path(metadata_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp")
    temporary.write_text(
        json.dumps({"filename": normalized_xlsx_filename(filename)}, ensure_ascii=False),
        encoding="utf-8",
    )
    os.replace(temporary, path)


def load_active_filename(
    metadata_path: str | Path,
    workbook_path: str | Path,
) -> str | None:
    workbook = Path(workbook_path)
    if not workbook.is_file():
        return None

    path = Path(metadata_path)
    if path.is_file():
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            filename = str(payload.get("filename") or "").strip()
            if filename:
                return normalized_xlsx_filename(filename)
        except (OSError, ValueError, TypeError):
            pass
    return workbook.name
