"""Create one SCM device onboarding rule per firewall from the Firewalls sheet.

Each rule matches one serial number and places the firewall in its folder (the
`folder` column) when it first connects to SCM. Terraform has no resource for
onboarding rules, so this uses the SCM API:
  GET  /config/setup/device-onboarding/v1/onboarding-rules
  POST /config/setup/device-onboarding/v1/onboarding-rules        new rule
  PUT  /config/setup/device-onboarding/v1/onboarding-rules/{id}   folder changed

Existing rules are matched by serial number, whatever their name, so rules made by
hand in SCM are recognised. Default is a dry run; nothing is written without --apply.
Rules are never deleted.

Usage:
  .venv\\Scripts\\python scripts\\scm_onboarding_rules.py <workbook.xlsx> [--wave N]
  .venv\\Scripts\\python scripts\\scm_onboarding_rules.py <workbook.xlsx> [--wave N] --apply
"""
import argparse
import os
import re
import sys
import urllib.error
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from scm_auth_check import get_token, load_env_file  # noqa: E402
from scm_devices import api, in_scope, list_all  # noqa: E402
from template_io import read_sheet  # noqa: E402

RULES = "/config/setup/device-onboarding/v1/onboarding-rules"


def rule_name(row: dict) -> str:
    base = row.get("display_name") or row["serial_number"]
    return "Onboard_" + re.sub(r"[^A-Za-z0-9_]", "_", base)


def rule_body(name: str, serial: str, folder: str) -> dict:
    """Same shape as a rule created in the SCM UI (read back through the API)."""
    return {
        "name": name,
        "enable": True,
        "rule_type": "label",
        "match_criteria": {"models": {}, "serial": {"pattern": serial}, "labels": ""},
        "actions": {"folder_association": {"folder": folder}},
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("workbook", type=Path)
    ap.add_argument("--wave", help="only rows whose wave column equals this value")
    ap.add_argument("--apply", action="store_true", help="create / update the rules in SCM (default: dry run)")
    args = ap.parse_args()

    rows = read_sheet(args.workbook, "Firewalls")
    if args.wave is not None:
        rows = [r for r in rows if r.get("wave") == args.wave]
    if not rows:
        print("No firewall rows to process" + (f" in wave {args.wave}." if args.wave else "."))
        return 0

    load_env_file()
    token = get_token(os.environ["SCM_CLIENT_ID"], os.environ["SCM_CLIENT_SECRET"], os.environ["SCM_SCOPE"])
    folders = {f["name"]: f.get("parent", "") for f in list_all(token, "/config/setup/v1/folders")}
    existing = api(token, "GET", RULES)
    existing = existing.get("data", existing) if isinstance(existing, dict) else existing
    by_serial = {}
    for rule in existing:
        pattern = ((rule.get("match_criteria") or {}).get("serial") or {}).get("pattern", "")
        by_serial.setdefault(pattern.strip("^$"), rule)

    plan, problems = [], 0
    for r in rows:
        serial, folder = r.get("serial_number", ""), r.get("folder", "")
        where = f"row {r['_row']} ({serial or 'no serial'})"
        if not serial or not folder:
            print(f"ERROR   {where}: serial_number and folder are required")
            problems += 1
            continue
        if folder not in folders:
            print(f"WAIT    {where}: folder '{folder}' does not exist in SCM yet - run terraform apply first")
            problems += 1
            continue
        if not in_scope(folder, folders):
            print(f"ERROR   {where}: folder '{folder}' is not PANW or below it")
            problems += 1
            continue
        rule = by_serial.get(serial)
        if rule is None:
            name = rule_name(r)
            print(f"CREATE  {where}: rule {name}: serial {serial} -> folder {folder}")
            plan.append(("POST", RULES, rule_body(name, serial, folder)))
            continue
        current = ((rule.get("actions") or {}).get("folder_association") or {}).get("folder")
        if current == folder and rule.get("enable"):
            print(f"OK      {where}: rule {rule['name']} already sends it to {folder}")
            continue
        print(f"UPDATE  {where}: rule {rule['name']}: folder {current!r} -> {folder!r}"
              + ("" if rule.get("enable") else ", enable it"))
        plan.append(("PUT", f"{RULES}/{rule['id']}", rule_body(rule["name"], serial, folder)))

    print(f"\nPlan: {sum(1 for p in plan if p[0] == 'POST')} to create, "
          f"{sum(1 for p in plan if p[0] == 'PUT')} to update, {problems} row(s) with problems.")
    if not args.apply:
        print("Dry run only. Re-run with --apply to write these rules to SCM.")
        return 1 if problems else 0

    for method, path, body in plan:
        try:
            api(token, method, path, body)
            print(f"{'created' if method == 'POST' else 'updated'} {body['name']}")
        except urllib.error.HTTPError as err:
            print(f"FAILED  {body['name']}: HTTP {err.code} {err.read().decode(errors='replace')}")
            problems += 1
    print("Rules apply when each firewall first connects to SCM.")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
