"""Place firewalls in SCM folders from the Firewalls sheet of the bulk template.

Terraform has no resource for devices, so this uses the SCM API directly:
  GET /config/setup/v1/devices          current state
  PUT /config/setup/v1/devices/{serial}  folder, display_name, description, labels, snippets

Default is a dry run that prints the plan. Nothing is written without --apply.
It never pushes configuration to the firewalls.

Usage:
  .venv\\Scripts\\python scripts\\scm_devices.py <workbook.xlsx>
  .venv\\Scripts\\python scripts\\scm_devices.py <workbook.xlsx> --apply
"""
import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from scm_auth_check import HOST, get_token, load_env_file  # noqa: E402
from template_io import read_sheet, split_list  # noqa: E402

SCOPE_ROOT = "PANW"
PAGE = 50
FIELDS = ("folder", "display_name", "description", "labels", "snippets")


def api(token: str, method: str, path: str, body: dict | None = None) -> dict:
    req = urllib.request.Request(
        f"https://{HOST}{path}",
        method=method,
        data=json.dumps(body).encode() if body is not None else None,
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        raw = resp.read()
        return json.loads(raw) if raw else {}


def list_all(token: str, path: str) -> list[dict]:
    items, offset = [], 0
    while True:
        page = api(token, "GET", f"{path}?limit={PAGE}&offset={offset}")
        data = page.get("data", [])
        items += data
        if len(data) < PAGE:
            return items
        offset += PAGE


def in_scope(folder: str, parents: dict[str, str]) -> bool:
    """True if folder is PANW or below it. parents maps folder -> parent."""
    seen = set()
    while folder and folder not in seen:
        if folder == SCOPE_ROOT:
            return True
        seen.add(folder)
        folder = parents.get(folder, "")
    return False


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("workbook", type=Path)
    ap.add_argument("--apply", action="store_true", help="write the changes to SCM (default: dry run)")
    ap.add_argument("--allow-out-of-scope-source", action="store_true",
                    help="allow moving a firewall that currently sits in a folder outside PANW")
    args = ap.parse_args()

    rows = read_sheet(args.workbook, "Firewalls")
    if not rows:
        print("No firewall rows in the Firewalls sheet.")
        return 0

    load_env_file()
    token = get_token(os.environ["SCM_CLIENT_ID"], os.environ["SCM_CLIENT_SECRET"], os.environ["SCM_SCOPE"])

    scm_folders = {f["name"]: f.get("parent", "") for f in list_all(token, "/config/setup/v1/folders")}
    planned = {r["name"]: r["parent"] for r in read_sheet(args.workbook, "Folders") if r.get("name")}
    parents = {**planned, **scm_folders}
    devices = {d["id"]: d for d in list_all(token, "/config/setup/v1/devices")}

    plan, problems = [], 0
    for r in rows:
        serial, target = r.get("serial_number", ""), r.get("folder", "")
        where = f"row {r['_row']} ({serial or 'no serial'})"
        if not serial or not target:
            print(f"ERROR   {where}: serial_number and folder are required")
            problems += 1
            continue
        if not in_scope(target, parents):
            print(f"ERROR   {where}: folder '{target}' is not PANW or below it")
            problems += 1
            continue
        dev = devices.get(serial)
        if dev is None:
            print(f"SKIP    {where}: not registered to this tenant - register / associate it first")
            problems += 1
            continue
        if target not in scm_folders:
            print(f"WAIT    {where}: folder '{target}' does not exist in SCM yet - run terraform apply first")
            problems += 1
            continue
        current_folder = dev.get("folder") or ""
        if current_folder and not in_scope(current_folder, scm_folders) and not args.allow_out_of_scope_source:
            print(f"BLOCKED {where}: currently in '{current_folder}', outside PANW "
                  f"(re-run with --allow-out-of-scope-source if this move is intended)")
            problems += 1
            continue

        desired = {
            "folder": target,
            "display_name": r.get("display_name") or dev.get("display_name"),
            "description": r.get("description") or dev.get("description"),
            "labels": split_list(r.get("labels")) or dev.get("labels"),
            "snippets": split_list(r.get("snippets")) or dev.get("snippets"),
        }
        body = {k: v for k, v in desired.items() if v not in (None, "", [])}
        changes = [f"{k}: {dev.get(k)!r} -> {body.get(k)!r}" for k in FIELDS if (dev.get(k) or None) != (body.get(k) or None)]
        if not changes:
            print(f"OK      {where}: already as requested")
            continue
        print(f"CHANGE  {where} [{dev.get('display_name')}, {dev.get('model')}]")
        for c in changes:
            print(f"          {c}")
        plan.append((serial, body))

    print(f"\nPlan: {len(plan)} firewall(s) to update, {problems} row(s) with problems.")
    if not args.apply:
        print("Dry run only. Re-run with --apply to write these changes to SCM.")
        return 1 if problems else 0

    for serial, body in plan:
        try:
            api(token, "PUT", f"/config/setup/v1/devices/{serial}", body)
            print(f"updated {serial}")
        except urllib.error.HTTPError as err:
            print(f"FAILED  {serial}: HTTP {err.code} {err.read().decode(errors='replace')}")
            problems += 1
    print("Done. Push the config from SCM so the firewalls receive their new folder's configuration.")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
