"""Offline consistency check of a filled-in SCM bulk template.

Checks required fields, containers (exactly one of folder / snippet / device, inside PANW),
and that every reference (labels, tags, folders, snippets, variables, interfaces, zones,
addresses, services, routers) points to something defined in the workbook. References to
objects that may already exist in SCM are reported as warnings, not errors.

Usage:  .venv\\Scripts\\python scripts\\validate_workbook.py <workbook.xlsx>
"""
import re
import sys
from collections import defaultdict
from pathlib import Path

from openpyxl import load_workbook

sys.path.insert(0, str(Path(__file__).resolve().parent))
from template_io import read_sheet, split_list  # noqa: E402

SCOPE_ROOT = "PANW"
ANY = {"any"}
PREDEFINED_SERVICES = {"application-default", "service-http", "service-https"}
VAR = re.compile(r"^\$[A-Za-z0-9_]+$")


class Report:
    def __init__(self):
        self.errors, self.warnings = [], []

    def err(self, where, msg):
        self.errors.append(f"ERROR  {where}: {msg}")

    def warn(self, where, msg):
        self.warnings.append(f"WARN   {where}: {msg}")


def required_fields(path: Path) -> dict[str, list[str]]:
    """Field names marked Required (row 3) per sheet."""
    wb = load_workbook(path, read_only=True)
    out = {}
    for ws in wb.worksheets:
        rows = list(ws.iter_rows(min_row=1, max_row=3, values_only=True))
        if len(rows) == 3:
            out[ws.title] = [h for h, r in zip(rows[0], rows[2]) if h and r == "Required"]
    wb.close()
    return out


def main() -> int:
    path = Path(sys.argv[1])
    rep = Report()
    s = {name: read_sheet(path, name) for name in (
        "Labels", "Folders", "Snippets", "Folder Snippets", "Tags", "Variables", "Addresses", "Address Groups",
        "Services", "Service Groups", "Interfaces", "Zones", "Logical Routers", "Routes", "Security Rules",
        "NAT Rules", "Firewalls")}
    at = lambda sheet, r: f"{sheet} row {r['_row']}"  # noqa: E731

    # Required fields
    for sheet, fields in required_fields(path).items():
        for r in s.get(sheet, []):
            for f in fields:
                if not r.get(f):
                    rep.err(at(sheet, r), f"'{f}' is required")

    labels = {r["name"] for r in s["Labels"]}
    folders = {SCOPE_ROOT: ""} | {r["name"]: r["parent"] for r in s["Folders"]}
    snippets = {r["name"] for r in s["Snippets"]}
    serials = {r["serial_number"] for r in s["Firewalls"]}

    def in_scope(folder):
        seen = set()
        while folder and folder not in seen:
            if folder == SCOPE_ROOT:
                return True
            seen.add(folder)
            folder = folders.get(folder, "")
        return False

    def check_labels(sheet, r, field="labels"):
        for lb in split_list(r.get(field)):
            if lb not in labels:
                rep.warn(at(sheet, r), f"label '{lb}' is not in the Labels sheet - it must already exist in SCM")

    # Folders, snippets, folder snippets
    for r in s["Folders"]:
        if r["parent"] not in folders:
            rep.err(at("Folders", r), f"parent '{r['parent']}' is not PANW or a folder in this sheet")
        check_labels("Folders", r)
    for r in s["Snippets"]:
        check_labels("Snippets", r)
    for r in s["Folder Snippets"]:
        if r["folder"] not in folders:
            rep.err(at("Folder Snippets", r), f"folder '{r['folder']}' is not defined")
        if r["snippet"] not in snippets:
            rep.warn(at("Folder Snippets", r), f"snippet '{r['snippet']}' is not in the Snippets sheet - it must already exist")

    # Containers: exactly one of folder / snippet / device, all inside scope
    def container(sheet, r):
        options = {k: r.get(k) for k in ("folder", "snippet", "device") if r.get(k)}
        if len(options) != 1:
            rep.err(at(sheet, r), f"set exactly one of folder / snippet{' / device' if sheet == 'Variables' else ''}")
            return None
        kind, name = next(iter(options.items()))
        if kind == "folder" and not in_scope(name):
            rep.err(at(sheet, r), f"folder '{name}' is not PANW or below it")
        if kind == "snippet" and name not in snippets:
            rep.warn(at(sheet, r), f"snippet '{name}' is not in the Snippets sheet - it must already exist")
        if kind == "device" and name not in serials:
            rep.err(at(sheet, r), f"device '{name}' is not a serial number in the Firewalls sheet")
        return f"{kind}:{name}"

    CONTAINER_SHEETS = ("Tags", "Variables", "Addresses", "Address Groups", "Services", "Service Groups",
                        "Interfaces", "Zones", "Logical Routers", "Security Rules", "NAT Rules")
    seen = defaultdict(set)
    for sheet in CONTAINER_SHEETS:
        for r in s[sheet]:
            c = container(sheet, r)
            if c and r.get("name") in seen[(sheet, c)]:
                rep.err(at(sheet, r), f"duplicate name '{r['name']}' in {c}")
            seen[(sheet, c)].add(r.get("name"))
            r["_container"] = c

    tags = {r["name"] for r in s["Tags"]}
    for sheet in ("Addresses", "Address Groups", "Services", "Service Groups", "Security Rules", "NAT Rules"):
        for r in s[sheet]:
            for t in split_list(r.get("tag")):
                if t not in tags:
                    rep.warn(at(sheet, r), f"tag '{t}' is not in the Tags sheet - it must already exist in SCM")

    # Variables: names, consistent types, every override has a declaration
    var_types, declared = defaultdict(set), set()
    for r in s["Variables"]:
        if not VAR.match(r["name"]):
            rep.err(at("Variables", r), f"variable name '{r['name']}' must start with $ (letters, digits, _)")
        var_types[r["name"]].add(r["type"])
        if not r.get("device"):
            declared.add(r["name"])
    for name, types in var_types.items():
        if len(types) > 1:
            rep.err("Variables", f"{name} has different types: {', '.join(sorted(types))}")
    for r in s["Variables"]:
        if r.get("device") and r["name"] not in declared:
            rep.warn(at("Variables", r), f"{r['name']} is only set per firewall; add a folder or snippet row with a default")
    variables = set(var_types)

    def check_var(sheet, r, field):
        for v in split_list(r.get(field)):
            if v.startswith("$") and v not in variables:
                rep.err(at(sheet, r), f"variable {v} used in '{field}' is not defined in Variables")

    # Interfaces
    interfaces = {r["name"]: r for r in s["Interfaces"]}
    for r in s["Interfaces"]:
        check_var("Interfaces", r, "ip")
        check_var("Interfaces", r, "name")
        t = r["interface_type"]
        if t == "ethernet" and not r.get("mode"):
            rep.err(at("Interfaces", r), "ethernet needs a mode")
        if t == "layer3-subinterface":
            if r.get("parent_interface") not in interfaces:
                rep.err(at("Interfaces", r), f"parent '{r.get('parent_interface')}' is not in the Interfaces sheet")
            if not r.get("vlan_tag"):
                rep.err(at("Interfaces", r), "layer3-subinterface needs a vlan_tag")
            elif not r["name"].endswith(f".{r['vlan_tag']}"):
                rep.warn(at("Interfaces", r), f"name '{r['name']}' does not end with .{r['vlan_tag']} (the VLAN tag)")

    # Zones and logical routers reference interfaces; an interface sits in one zone only
    zone_of = {}
    for r in s["Zones"]:
        for i in split_list(r.get("interfaces")):
            if i not in interfaces:
                rep.err(at("Zones", r), f"interface '{i}' is not in the Interfaces sheet")
            if i in zone_of:
                rep.err(at("Zones", r), f"interface '{i}' is already in zone '{zone_of[i]}'")
            zone_of[i] = r["name"]
    routers = {}
    for r in s["Logical Routers"]:
        routers[(r["name"], r["vrf_name"])] = r
        for i in split_list(r.get("interfaces")):
            if i not in interfaces:
                rep.err(at("Logical Routers", r), f"interface '{i}' is not in the Interfaces sheet")
    for r in s["Routes"]:
        if (r["logical_router"], r["vrf_name"]) not in routers:
            rep.err(at("Routes", r), f"router '{r['logical_router']}' / VRF '{r['vrf_name']}' is not in Logical Routers")
        elif r.get("interface") and r["interface"] not in split_list(routers[(r["logical_router"], r["vrf_name"])].get("interfaces")):
            rep.err(at("Routes", r), f"interface '{r['interface']}' is not part of that router / VRF")
        if r["nexthop_type"] in ("ip_address", "next_lr", "fqdn") and not r.get("nexthop"):
            rep.err(at("Routes", r), f"nexthop is required for {r['nexthop_type']}")
        check_var("Routes", r, "nexthop")

    # Policy references
    zones = {r["name"] for r in s["Zones"]}
    addresses = {r["name"] for r in s["Addresses"]} | {r["name"] for r in s["Address Groups"]}
    services = {r["name"] for r in s["Services"]} | {r["name"] for r in s["Service Groups"]}
    for r in s["Address Groups"]:
        for m in split_list(r.get("static")):
            if m not in addresses:
                rep.warn(at("Address Groups", r), f"member '{m}' is not defined here - it must already exist")
    for r in s["Service Groups"]:
        for m in split_list(r.get("members")):
            if m not in services | PREDEFINED_SERVICES:
                rep.warn(at("Service Groups", r), f"member '{m}' is not defined here - it must already exist")
    for sheet in ("Security Rules", "NAT Rules"):
        for r in s[sheet]:
            for f in ("from", "to"):
                for z in split_list(r.get(f)):
                    if z not in zones | ANY:
                        rep.err(at(sheet, r), f"zone '{z}' in '{f}' is not in the Zones sheet")
            for f in ("source", "destination"):
                for a in split_list(r.get(f)):
                    if a not in addresses | ANY and not re.match(r"^[\d.:/-]+$", a):
                        rep.warn(at(sheet, r), f"address '{a}' in '{f}' is not defined here - it must already exist")
            for sv in split_list(r.get("service")):
                if sv not in services | PREDEFINED_SERVICES | ANY:
                    rep.warn(at(sheet, r), f"service '{sv}' is not defined here - it must already exist")
            if sheet == "NAT Rules":
                if r.get("src_interface") and r["src_interface"] not in interfaces:
                    rep.err(at(sheet, r), f"src_interface '{r['src_interface']}' is not in the Interfaces sheet")
                if r.get("source_translation") in ("dynamic_ip_and_port", "dynamic_ip", "static_ip") \
                        and not (r.get("src_translated_address") or r.get("src_interface")):
                    rep.err(at(sheet, r), "source translation needs src_translated_address or src_interface")

    # Firewalls
    for r in s["Firewalls"]:
        if not in_scope(r["folder"]):
            rep.err(at("Firewalls", r), f"folder '{r['folder']}' is not PANW or below it")
        check_labels("Firewalls", r)
        if not r.get("wave"):
            rep.warn(at("Firewalls", r), "no wave set")

    counts = ", ".join(f"{k}: {len(v)}" for k, v in s.items() if v)
    print(f"Rows - {counts}\n")
    for line in rep.errors + rep.warnings:
        print(line)
    print(f"\n{len(rep.errors)} error(s), {len(rep.warnings)} warning(s).")
    return 1 if rep.errors else 0


if __name__ == "__main__":
    sys.exit(main())
