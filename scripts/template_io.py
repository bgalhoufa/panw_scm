"""Read data rows from a filled-in SCM bulk template (see scripts/build_template.py)."""
from pathlib import Path

from openpyxl import load_workbook

HEADER_ROW = 1
FIRST_DATA_ROW = 5


def split_list(value) -> list[str]:
    """Split a ';'-separated cell into a clean list."""
    if value is None:
        return []
    return [v.strip() for v in str(value).split(";") if v.strip()]


def cell_str(value) -> str:
    if value is None:
        return ""
    if isinstance(value, float) and value.is_integer():
        value = int(value)  # Excel stores 443 as 443.0
    return str(value).strip()


def read_sheet(path: Path, sheet: str) -> list[dict]:
    """Return one dict per data row, keyed by the row-1 field names.

    Empty rows and rows whose first cell starts with EXAMPLE are skipped.
    Each dict also carries "_row" (the Excel row number) for error messages.
    """
    wb = load_workbook(path, read_only=True, data_only=True)
    if sheet not in wb.sheetnames:
        return []
    ws = wb[sheet]
    rows = ws.iter_rows(values_only=True)
    header = [cell_str(h) for h in next(rows)]
    out = []
    for number, values in enumerate(rows, start=HEADER_ROW + 1):
        if number < FIRST_DATA_ROW:
            continue
        record = {h: cell_str(v) for h, v in zip(header, values) if h}
        if not any(record.values()) or record.get(header[0], "").upper().startswith("EXAMPLE"):
            continue
        record["_row"] = number
        out.append(record)
    wb.close()
    return out
