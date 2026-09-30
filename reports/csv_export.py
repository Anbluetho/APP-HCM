"""CSV serialization for the shared report payload."""

from __future__ import annotations

import csv
from io import StringIO
from typing import Any


CSV_COLUMNS = ("Sección", "Dato", "Valor", "Unidad", "Fuente")


def report_to_csv(payload: dict[str, Any]) -> str:
    """Serialize report metadata and records as UTF-8-compatible CSV text."""
    output = StringIO(newline="")
    writer = csv.DictWriter(output, fieldnames=CSV_COLUMNS, extrasaction="ignore")
    writer.writeheader()
    for key, value in payload.get("metadata", {}).items():
        writer.writerow({
            "Sección": "Identificación del informe",
            "Dato": key,
            "Valor": "" if value is None else str(value),
        })
    for section in payload.get("sections", []):
        for record in section.get("records", []):
            writer.writerow(record)
    return "\ufeff" + output.getvalue()
