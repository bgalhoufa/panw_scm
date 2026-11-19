"""Move a filled-in workbook to the current template layout (new sheets / columns).

Builds a fresh copy of the template and copies every data row (row 5 and below) of the old
workbook into it, column by column by field name. Renamed fields are mapped (RENAMED); columns
the new template no longer has are reported; extra sheets (not in the template) are kept as they
are. The old file is kept as <name>.bak.xlsx.

Usage:  .venv\\Scripts\\python scripts\\upgrade_workbook.py inputs\\rollout.xlsx
"""
import shutil
import sys
from copy import copy
import tempfile
from pathlib import Path

from openpyxl import load_workbook

sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_template  # noqa: E402

RENAMED = {("Routes", "logical_router"): "router"}  # (sheet, old field) -> new field
FIRST_DATA_ROW = 5


def main() -> int:
    if len(sys.argv) != 2:
        print(__doc__)
        return 2
    path = Path(sys.argv[1])
    with tempfile.TemporaryDirectory() as tmp:
        fresh = Path(tmp) / "template.xlsx"
        build_template.build(fresh)
        new, old = load_workbook(fresh), load_workbook(path)
        for ws in old.worksheets:
            if ws.title in ("README", "Lists"):
                continue
            if ws.title not in new.sheetnames:  # an extra sheet (e.g. design notes): copy it as it is
                extra = new.create_sheet(ws.title, index=len(new.sheetnames) - 1)
                for row in ws.iter_rows():
                    for c in row:
                        if c.value is not None:
                            d = extra.cell(c.row, c.column, c.value)
                            d.font, d.alignment, d.fill = copy(c.font), copy(c.alignment), copy(c.fill)
                for key, dim in ws.column_dimensions.items():
                    extra.column_dimensions[key].width = dim.width
                print(f"kept  extra sheet '{ws.title}'")
                continue
            dst = new[ws.title]
            dst_col = {c.value: c.column for c in dst[1] if c.value}
            moved = 0
            for c in ws[1]:
                if not c.value:
                    continue
                field = RENAMED.get((ws.title, c.value), c.value)
                if field not in dst_col:
                    if any(ws.cell(r, c.column).value not in (None, "") for r in range(FIRST_DATA_ROW, ws.max_row + 1)):
                        print(f"WARN  {ws.title}: column '{c.value}' is not in the template any more - its values were not copied")
                    continue
                for r in range(FIRST_DATA_ROW, ws.max_row + 1):
                    v = ws.cell(r, c.column).value
                    if v not in (None, ""):
                        dst.cell(r, dst_col[field], v)
                        moved += 1
            if moved:
                print(f"copied {ws.title}: {moved} cells")
        backup = path.with_suffix(".bak.xlsx")
        shutil.copyfile(path, backup)
        new.save(path)
    print(f"Upgraded {path} (previous version: {backup.name}). New sheets start empty.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
