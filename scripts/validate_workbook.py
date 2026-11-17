"""Offline consistency check of a filled-in SCM bulk template.

Checks required fields, containers (exactly one of folder / snippet / device, inside PANW),
and that every reference (labels, tags, folders, snippets, variables, interfaces, zones,
addresses, services, routers) points to something defined in the workbook. References to
objects that may already exist in SCM are reported as warnings, not errors.

Usage:  .venv\\Scripts\\python scripts\\validate_workbook.py <workbook.xlsx>
"""
import ipaddress
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
MAC = re.compile(r"^[0-9a-f]{2}([:-][0-9a-f]{2}){5}$", re.I)


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


def main(argv: list[str] | None = None) -> int:
    path = Path((argv if argv is not None else sys.argv[1:])[0])
    rep = Report()
    s = {name: read_sheet(path, name) for name in (
        "Labels", "Folders", "Snippets", "Folder Snippets", "Tags", "Variables", "Addresses", "Address Groups",
        "Services", "Service Groups", "Interfaces", "Zones", "Logical Routers", "Routes", "DHCP Servers",
        "DHCP Reservations", "Security Rules", "NAT Rules", "Firewalls")}
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
                        "Interfaces", "Zones", "Logical Routers", "DHCP Servers", "DHCP Reservations",
                        "Security Rules", "NAT Rules")
    seen = defaultdict(set)
    for sheet in CONTAINER_SHEETS:
        for r in s[sheet]:
            c = container(sheet, r)
            key = r.get("name") or (r.get("interface") if sheet == "DHCP Servers" else None)
            if c and key and key in seen[(sheet, c)]:
                rep.err(at(sheet, r), f"duplicate '{key}' in {c}")
            seen[(sheet, c)].add(key)
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
        t = r["interface_type"]
        if t == "ethernet" and not r.get("mode"):
            rep.err(at("Interfaces", r), "ethernet needs a mode")
        if (r.get("folder") or r.get("snippet")) and not r["name"].startswith("$"):
            rep.err(at("Interfaces", r), f"'{r['name']}': in a folder or snippet SCM only accepts interface variables "
                                         "(names starting with $, e.g. $wan); put the physical port in default_value")
        if t != "layer3-subinterface" and r["name"].startswith("$") and not r.get("default_value"):
            rep.warn(at("Interfaces", r), f"{r['name']} has no default_value - map it to a physical port per firewall in SCM")
        if t == "layer3-subinterface" and r.get("parent_interface") and not r["name"].startswith(r["parent_interface"] + "."):
            rep.err(at("Interfaces", r), f"subinterface '{r['name']}' must be named {r['parent_interface']}.<VLAN>")
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

    # DHCP: one server per interface + container; reservations attach to a server row
    servers = {}
    for r in s["DHCP Servers"]:
        servers[(r.get("_container"), r["interface"])] = r
        if r["interface"] not in interfaces:
            rep.err(at("DHCP Servers", r), f"interface '{r['interface']}' is not in the Interfaces sheet")
        if r["dhcp_type"] == "relay" and not r.get("relay_servers"):
            rep.err(at("DHCP Servers", r), "a DHCP relay needs relay_servers")
    def folder_chain(folder):
        """The folder and all its ancestors up to PANW."""
        chain = []
        while folder and folder not in chain:
            chain.append(folder)
            folder = folders.get(folder, "")
        return chain

    def firewalls_receiving(container):
        """Serial numbers of the firewalls that get config from this container."""
        kind, _, name = (container or "").partition(":")
        out = []
        for fw in s["Firewalls"]:
            chain = folder_chain(fw.get("folder"))
            if (kind == "device" and fw["serial_number"] == name
                    or kind == "folder" and name in chain
                    or kind == "snippet" and (name in split_list(fw.get("snippets"))
                                              or any(fs["snippet"] == name and fs["folder"] in chain
                                                     for fs in s["Folder Snippets"]))):
                out.append(fw)
        return out

    def subnets_on(iface, serial):
        """Networks of an interface on one firewall: literal IP, or that firewall's value of the $variable,
        resolved like SCM does - the firewall's own value, else the closest folder up its folder chain,
        else any other default (e.g. a snippet)."""
        chain = folder_chain(next((f.get("folder") for f in s["Firewalls"] if f["serial_number"] == serial), None))
        nets = []
        for ip in split_list(interfaces.get(iface, {}).get("ip")):
            if ip.startswith("$"):
                rows = [x for x in s["Variables"] if x["name"] == ip]
                own = [x["value"] for x in rows if x.get("device") == serial]
                by_folder = {x["folder"]: x["value"] for x in rows if x.get("folder")}
                nearest = [by_folder[f] for f in chain if f in by_folder]
                ip = (own or nearest or [x["value"] for x in rows if not x.get("device")] or [None])[0]
            try:
                nets.append(ipaddress.ip_interface(ip).network)
            except (ValueError, TypeError):
                pass
        return nets

    def in_pool(ip, pools):
        for pool in pools:
            try:
                if "-" in pool:
                    lo, hi = (ipaddress.ip_address(x.strip()) for x in pool.split("-", 1))
                    if lo <= ip <= hi:
                        return True
                elif ip in ipaddress.ip_network(pool, strict=False):
                    return True
            except ValueError:
                return True  # unparsable pool (e.g. a variable): don't flag
        return False

    used = defaultdict(set)
    for r in s["DHCP Reservations"]:
        key = (r.get("_container"), r["interface"])
        srv = servers.get(key)
        if srv is None:
            rep.err(at("DHCP Reservations", r), f"no DHCP Servers row for {r['interface']} in {key[0]}")
        elif srv["dhcp_type"] != "server":
            rep.err(at("DHCP Reservations", r), f"{r['interface']} in {key[0]} is a relay, not a server")
        try:
            ip = ipaddress.ip_address(r["ip"])
        except ValueError:
            rep.err(at("DHCP Reservations", r), f"'{r['ip']}' is not an IP address")
            ip = None
        receivers = firewalls_receiving(r.get("_container"))
        if not receivers:
            rep.warn(at("DHCP Reservations", r), f"{r.get('_container')} is not attached to any firewall in the "
                                                 "Firewalls sheet, so the subnet could not be checked")
        for fw in receivers if ip else []:
            nets = subnets_on(r["interface"], fw["serial_number"])
            if nets and not any(ip in n for n in nets):
                name = fw.get("display_name") or fw["serial_number"]
                rep.err(at("DHCP Reservations", r), f"{ip} is outside {r['interface']} on {name} "
                                                    f"({', '.join(str(n) for n in nets)})")
        if ip and srv and split_list(srv.get("ip_pool")) and not in_pool(ip, split_list(srv["ip_pool"])):
            rep.warn(at("DHCP Reservations", r), f"{ip} is outside the server's ip_pool - PAN-OS expects reserved "
                                                 "addresses inside the pool when a pool is set")
        if not MAC.match(r["mac"]):
            rep.err(at("DHCP Reservations", r), f"MAC '{r['mac']}' is not like 00:11:22:33:44:55")
        for field in ("ip", "mac"):
            v = r[field].lower()
            if v in used[(key, field)]:
                rep.err(at("DHCP Reservations", r), f"{field} {r[field]} is reserved twice on {r['interface']}")
            used[(key, field)].add(v)

    for key, r in servers.items():
        if r["dhcp_type"] == "server" and not r.get("ip_pool") and not used[(key, "ip")]:
            rep.err(at("DHCP Servers", r), "a DHCP server needs ip_pool or at least one DHCP Reservations row")

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
        for sn in split_list(r.get("snippets")):
            if sn not in snippets:
                rep.warn(at("Firewalls", r), f"snippet '{sn}' is not in the Snippets sheet - it must already exist")
        if not r.get("wave"):
            rep.warn(at("Firewalls", r), "no wave set")

    # Scope: SCM only resolves a reference inside the same snippet, or in the same folder and the
    # folders above it (a firewall sees its folder chain). Anything else fails at apply time.
    defined = defaultdict(list)          # (kind, name) -> containers that define it
    kinds = {"Interfaces": "interface", "Zones": "zone", "Addresses": "address", "Address Groups": "address",
             "Services": "service", "Service Groups": "service", "Tags": "tag", "Variables": "variable"}
    for sheet, kind in kinds.items():
        for r in s[sheet]:
            if r.get("_container") and not (sheet == "Variables" and r.get("device")):
                defined[(kind, r["name"])].append(r["_container"])
    fw_folder = {r["serial_number"]: r.get("folder") for r in s["Firewalls"]}

    def visible_from(container):
        kind, _, name = (container or "").partition(":")
        if kind == "snippet":
            return {container}
        if kind == "folder":
            return {f"folder:{f}" for f in folder_chain(name)}
        if kind == "device":
            return {container} | {f"folder:{f}" for f in folder_chain(fw_folder.get(name))}
        return set()

    def check_scope(sheet, r, kind, names):
        where = r.get("_container")
        if not where:
            return
        seen_here = visible_from(where)
        for n in names:
            if not n or n.lower() == "any" or (kind == "service" and n in PREDEFINED_SERVICES):
                continue
            homes = defined.get((kind, n))
            if homes and not seen_here & set(homes):
                rep.err(at(sheet, r), f"{kind} '{n}' is defined in {', '.join(sorted(set(homes)))}, which {where} "
                                      "cannot see - SCM only resolves references in the same snippet or up the folder chain")

    vrs = lambda *vals: [v for val in vals for v in split_list(val) if v.startswith("$")]  # noqa: E731
    for r in s["Interfaces"]:
        check_scope("Interfaces", r, "interface", [r.get("parent_interface")])
        check_scope("Interfaces", r, "variable", vrs(r.get("ip")))
    for r in s["Zones"]:
        check_scope("Zones", r, "interface", split_list(r.get("interfaces")))
    routes_of = defaultdict(list)
    for rt in s["Routes"]:
        routes_of[(rt["logical_router"], rt["vrf_name"])].append(rt)
    for r in s["Logical Routers"]:
        check_scope("Logical Routers", r, "interface", split_list(r.get("interfaces")))
        for rt in routes_of[(r["name"], r["vrf_name"])]:
            check_scope("Logical Routers", r, "interface", [rt.get("interface")])
            check_scope("Logical Routers", r, "variable", vrs(rt.get("nexthop")))
    for r in s["DHCP Servers"]:
        check_scope("DHCP Servers", r, "interface", [r["interface"]])
        check_scope("DHCP Servers", r, "variable", vrs(r.get("gateway"), r.get("dns_primary"), r.get("dns_secondary"),
                                                       r.get("ntp_primary"), r.get("ip_pool")))
        for f in ("gateway", "dns_primary", "dns_secondary", "ntp_primary"):
            check_var("DHCP Servers", r, f)
    for sheet in ("Addresses", "Address Groups", "Services", "Service Groups"):
        for r in s[sheet]:
            check_scope(sheet, r, "tag", split_list(r.get("tag")))
    for r in s["Address Groups"]:
        check_scope("Address Groups", r, "address", split_list(r.get("static")))
    for r in s["Service Groups"]:
        check_scope("Service Groups", r, "service", split_list(r.get("members")))
    for sheet in ("Security Rules", "NAT Rules"):
        for r in s[sheet]:
            check_scope(sheet, r, "zone", split_list(r.get("from")) + split_list(r.get("to")))
            check_scope(sheet, r, "address", split_list(r.get("source")) + split_list(r.get("destination")))
            check_scope(sheet, r, "service", split_list(r.get("service")))
            check_scope(sheet, r, "tag", split_list(r.get("tag")))
            if sheet == "NAT Rules":
                check_scope(sheet, r, "interface", [r.get("to_interface"), r.get("src_interface")])

    counts =", ".join(f"{k}: {len(v)}" for k, v in s.items() if v)
    print(f"Rows - {counts}\n")
    for line in rep.errors + rep.warnings:
        print(line)
    print(f"\n{len(rep.errors)} error(s), {len(rep.warnings)} warning(s).")
    return 1 if rep.errors else 0


if __name__ == "__main__":
    sys.exit(main())
