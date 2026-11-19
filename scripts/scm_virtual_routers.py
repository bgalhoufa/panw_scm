"""Create / update legacy virtual routers in SCM from the Virtual Routers + Routes sheets.

Terraform has no virtual router resource (the provider only has scm_logical_router), so this
uses the SCM API directly:
  GET  /config/network/v1/virtual-routers?folder=<f>&name=<n>   current state
  POST /config/network/v1/virtual-routers                       create
  PUT  /config/network/v1/virtual-routers/{id}                  update
Fields managed here: interface, ecmp.enable, routing_table.ip.static_route. Anything else set on
an existing router in SCM is kept. A router is never deleted.

Run it after terraform apply (the routers reference interfaces Terraform creates). Default is a dry
run; nothing is written without --apply. The tenant comes from SCM_TENANT (.env.<tenant>).

Usage:
  .venv\\Scripts\\python scripts\\scm_virtual_routers.py <workbook.xlsx> [--apply]
"""
import argparse
import json
import os
import sys
import urllib.error
import urllib.parse
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import validate_workbook  # noqa: E402
from scm_auth_check import get_token, load_env_file  # noqa: E402
from scm_devices import api  # noqa: E402
from scope import in_scope  # noqa: E402
from template_io import read_sheet, split_list  # noqa: E402

EP = "/config/network/v1/virtual-routers"


def static_route(rt: dict) -> dict:
    nh_type, nh = rt["nexthop_type"], rt.get("nexthop")
    route = {"name": rt["name"], "destination": rt["destination"], "metric": int(rt.get("metric") or 10)}
    if nh_type in ("ip_address", "next_vr", "fqdn"):
        route["nexthop"] = {nh_type: nh}
    elif nh_type == "discard":
        route["nexthop"] = {"discard": {}}
    if rt.get("interface"):
        route["interface"] = rt["interface"]
    if rt.get("admin_dist"):
        route["admin_dist"] = int(rt["admin_dist"])
    return route


def desired(workbook: Path) -> list[dict]:
    """One body per Virtual Routers row (container + managed fields)."""
    routes = defaultdict(list)
    for rt in read_sheet(workbook, "Routes"):
        routes[rt["router"]].append(rt)
    out = []
    for r in read_sheet(workbook, "Virtual Routers"):
        body = {"name": r["name"], "interface": split_list(r.get("interfaces")),
                "routing_table": {"ip": {"static_route": [static_route(rt) for rt in routes[r["name"]]]}}}
        if r.get("ecmp_enable"):
            body["ecmp"] = {"enable": r["ecmp_enable"] == "yes"}
        container = ("folder", r["folder"]) if r.get("folder") else ("snippet", r["snippet"])
        out.append({"row": r["_row"], "container": container, "body": body})
    return out


def managed_view(vr: dict) -> dict:
    """The fields this script manages, normalised for comparison."""
    routes = (vr.get("routing_table") or {}).get("ip", {}).get("static_route", []) or []
    keep = ("name", "destination", "interface", "nexthop", "metric", "admin_dist")
    view = {"interface": sorted(vr.get("interface") or []),
            "static_route": sorted(({k: rt[k] for k in keep if k in rt} for rt in routes), key=lambda x: x["name"])}
    if "ecmp" in vr:
        view["ecmp_enable"] = (vr.get("ecmp") or {}).get("enable", False)
    return view


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("workbook", type=Path)
    ap.add_argument("--apply", action="store_true", help="write the changes to SCM (candidate config only)")
    args = ap.parse_args()
    if validate_workbook.main([str(args.workbook)]) != 0:
        print("\nWorkbook has errors - nothing done.")
        return 1
    load_env_file()
    print(f"\nTenant: {os.environ.get('SCM_TENANT') or 'default'} ({os.environ.get('SCM_SCOPE')})")
    token = get_token(os.environ["SCM_CLIENT_ID"], os.environ["SCM_CLIENT_SECRET"], os.environ["SCM_SCOPE"])
    parents = {r["name"]: r["parent"] for r in read_sheet(args.workbook, "Folders")}

    plan, problems = [], 0
    for d in desired(args.workbook):
        kind, where = d["container"]
        name, label = d["body"]["name"], f"row {d['row']} ({d['body']['name']} in {d['container'][1]})"
        if kind == "folder" and not in_scope(where, parents):
            print(f"ERROR   {label}: folder is outside the managed roots (scripts/scope.py)")
            problems += 1
            continue
        q = urllib.parse.urlencode({kind: where, "name": name})
        res = api(token, "GET", f"{EP}?{q}")  # a name filter returns a bare list, otherwise {"data": [...]}
        items = res if isinstance(res, list) else res.get("data", [res] if "id" in res else [])
        found = [v for v in items if v.get(kind) == where and v.get("name") == name]
        want = managed_view(d["body"])
        if not found:
            print(f"CREATE  {label}")
            print(f"          {json.dumps(want)}")
            plan.append(("POST", EP, {**d["body"], kind: where}, label))
            continue
        current = found[0]
        have = managed_view(current)
        if "ecmp_enable" not in want:
            have.pop("ecmp_enable", None)
        if have == want:
            print(f"OK      {label}: already as requested")
            continue
        print(f"UPDATE  {label}")
        for k in want:
            if have.get(k) != want[k]:
                print(f"          {k}: {json.dumps(have.get(k))}\n       -> {json.dumps(want[k])}")
        body = {k: v for k, v in current.items() if k not in ("id", "folder", "snippet", "device")}
        body.update({k: v for k, v in d["body"].items() if k != "routing_table"})
        rt = dict(body.get("routing_table") or {})
        rt["ip"] = {**(rt.get("ip") or {}), "static_route": d["body"]["routing_table"]["ip"]["static_route"]}
        body["routing_table"] = rt
        plan.append(("PUT", f"{EP}/{current['id']}", body, label))

    print(f"\nPlan: {sum(m == 'POST' for m, *_ in plan)} to create, {sum(m == 'PUT' for m, *_ in plan)} to update, "
          f"{problems} row(s) with problems.")
    if not args.apply:
        print("Dry run only. Re-run with --apply to write these changes to SCM.")
        return 1 if problems else 0
    failures = problems
    for method, path, body, label in plan:
        try:
            api(token, method, path, body)
            print(f"done    {label}")
        except urllib.error.HTTPError as err:
            print(f"FAILED  {label}: HTTP {err.code} {err.read().decode(errors='replace')[:600]}")
            failures += 1
    print("Done. The change is in the SCM candidate config: push it from SCM." if not failures else "Finished with errors.")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
