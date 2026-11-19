"""Read-only check of a firewall against what the rollout workbook says it should run.

Talks to the firewall's PAN-OS XML API with show commands only. Host and API key
come from .env (never printed):  FW1_HOST=192.168.1.11  FW1_API_KEY=...

What is expected is worked out from the workbook for that firewall's serial number:
interface IPs (interface variables mapped to their physical port, variable values
resolved up the firewall's folder chain), default route, rule and NAT names in order,
DHCP reservations.

Usage:  .venv\\Scripts\\python scripts\\fw_check.py inputs\\rollout.xlsx FW1
"""
import os
import re
import ssl
import sys
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from scm_auth_check import load_env_file  # noqa: E402
from template_io import read_sheet, split_list  # noqa: E402

CTX = ssl.create_default_context()
CTX.check_hostname = False
CTX.verify_mode = ssl.CERT_NONE  # firewall management certificates are self-signed in the lab


def op(host: str, key: str, cmd: str) -> str:
    """Run one operational show command; returns the raw XML response text."""
    url = f"https://{host}/api/?" + urllib.parse.urlencode({"type": "op", "cmd": cmd})
    req = urllib.request.Request(url, headers={"X-PAN-KEY": key})
    with urllib.request.urlopen(req, timeout=60, context=CTX) as resp:
        return resp.read().decode("utf-8", errors="replace")


def config(host: str, key: str, xpath: str) -> str:
    """Read the firewall's effective configuration, including what SCM pushed (shown as src="tpl")."""
    url = f"https://{host}/api/?" + urllib.parse.urlencode({"type": "config", "action": "get", "xpath": xpath})
    req = urllib.request.Request(url, headers={"X-PAN-KEY": key})
    with urllib.request.urlopen(req, timeout=60, context=CTX) as resp:
        return resp.read().decode("utf-8", errors="replace")


class Expected:
    """Everything the workbook says this firewall should have."""

    def __init__(self, workbook: Path, serial: str):
        S = {n: read_sheet(workbook, n) for n in ("Folders", "Variables", "Interfaces", "Logical Routers", "Virtual Routers", "Routes",
                                                    "DHCP Servers", "DHCP Reservations", "Security Rules",
                                                    "NAT Rules", "Firewalls")}
        fw = next((r for r in S["Firewalls"] if r["serial_number"] == serial), None)
        if fw is None:
            sys.exit(f"serial {serial} is not in the Firewalls sheet")
        parents = {"PANW": ""} | {r["name"]: r["parent"] for r in S["Folders"]}
        chain, f = [], fw["folder"]
        while f and f not in chain:
            chain.append(f)
            f = parents.get(f, "")
        self.fw, self.chain = fw, chain
        visible = lambda r: r.get("folder") in chain  # noqa: E731  (this design uses folders only)

        def var(name):
            rows = [x for x in S["Variables"] if x["name"] == name]
            own = [x["value"] for x in rows if x.get("device") == serial]
            by_folder = {x["folder"]: x["value"] for x in rows if x.get("folder")}
            return (own or [by_folder[c] for c in chain if c in by_folder] or [name])[0]

        self.var = var
        ifaces = {r["name"]: r for r in S["Interfaces"] if visible(r)}

        def physical(name):
            r = ifaces.get(name, {})
            if r.get("interface_type") == "layer3-subinterface":
                return f"{physical(r['parent_interface'])}.{r['vlan_tag']}"
            return r.get("default_value") or name

        self.physical = physical
        self.interfaces = {physical(n): [var(ip) for ip in split_list(r.get("ip"))] for n, r in ifaces.items()}
        self.routes = [(rt["destination"], var(rt.get("nexthop", ""))) for rt in S["Routes"]
                       if any(lr["name"] == rt["router"] and visible(lr)
                              for lr in S["Logical Routers"] + S["Virtual Routers"])]
        self.security = [r["name"] for r in S["Security Rules"] if visible(r)]
        self.nat = [r["name"] for r in S["NAT Rules"] if visible(r)]
        self.dhcp = [(physical(r["interface"]), [var(r.get("dns_primary", "")), var(r.get("dns_secondary", "")),
                                                 var(r.get("ntp_primary", ""))])
                     for r in S["DHCP Servers"] if visible(r)]
        self.reservations = [(physical(r["interface"]), r["ip"], r["mac"].lower())
                             for r in S["DHCP Reservations"] if visible(r)]


def in_order(text: str, names: list[str]) -> tuple[bool, list[str]]:
    positions = [(n, text.find(n)) for n in names]
    missing = [n for n, p in positions if p < 0]
    found = [p for _, p in positions if p >= 0]
    return (not missing and found == sorted(found)), missing


def main() -> int:
    if len(sys.argv) != 3:
        print(__doc__)
        return 2
    workbook, prefix = Path(sys.argv[1]), sys.argv[2].upper()
    load_env_file()
    host, key = os.environ.get(f"{prefix}_HOST"), os.environ.get(f"{prefix}_API_KEY")
    if not host or not key:
        sys.exit(f"{prefix}_HOST and {prefix}_API_KEY must be set in .env")

    info = ET.fromstring(op(host, key, "<show><system><info></info></system></show>"))
    serial = info.findtext(".//serial")
    exp = Expected(workbook, serial)
    print(f"{prefix} {host}: serial {serial}, {info.findtext('.//hostname')}, PAN-OS {info.findtext('.//sw-version')}, "
          f"advanced routing: {info.findtext('.//advanced-routing') or '?'} -> expected folder {exp.fw['folder']}\n")

    results = []

    def check(name, ok, detail=""):
        results.append(ok)
        print(f"{'PASS' if ok else 'FAIL'}  {name}" + (f"  - {detail}" if detail and not ok else ""))

    cm = op(host, key, "<show><cloud-management-status></cloud-management-status></show>")
    check("connected to Strata Cloud Manager", bool(re.search(r"(?i)connected\W*(yes|true)", cm)), "see show cloud-management-status")

    ifx = ET.fromstring(op(host, key, "<show><interface>all</interface></show>"))
    actual = {}
    for e in ifx.iter("entry"):
        if e.findtext("name"):
            actual.setdefault(e.findtext("name"), set()).add((e.findtext("ip") or "").strip())
    for name, ips in sorted(exp.interfaces.items()):
        for ip in ips:
            check(f"interface {name} = {ip}", ip in actual.get(name, set()),
                  f"firewall has {sorted(actual.get(name, {'(missing)'}))}")

    try:  # advanced routing (logical routers); legacy routing (virtual routers) refuses this command
        rt = op(host, key, "<show><advanced-routing><route></route></advanced-routing></show>")
    except Exception:  # noqa: BLE001
        rt = ""
    if "<entry>" not in rt:
        rt = op(host, key, "<show><routing><route></route></routing></show>")
    for dest, nh in exp.routes:
        check(f"route {dest} via {nh}", dest in rt and nh in rt, "not in the firewall's routing table")

    sec = op(host, key, "<show><running><security-policy></security-policy></running></show>")
    ok, missing = in_order(sec, exp.security)
    check(f"security rules in order: {', '.join(exp.security)}", ok, f"missing {missing}" if missing else "order differs")

    nat = op(host, key, "<show><running><nat-policy></nat-policy></running></show>")
    ok, missing = in_order(nat, exp.nat)
    check(f"NAT rules in order: {', '.join(exp.nat)}", ok, f"missing {missing}" if missing else "order differs")

    for iface, values in exp.dhcp:
        d = op(host, key, f"<show><dhcp><server><settings>{iface}</settings></server></dhcp></show>")
        for v in values:
            if v and not v.startswith("$"):
                check(f"DHCP {iface} hands out {v}", v in d, "not in show dhcp server settings")
        cfg = config(host, key, f"/config/devices/entry/network/dhcp/interface/entry[@name='{iface}']/server/reserved")
        for r_iface, ip, mac in exp.reservations:
            if r_iface == iface:
                entry = re.search(rf'<entry name="{re.escape(ip)}"[^>]*>(.*?)</entry>', cfg, re.S)
                check(f"DHCP {iface} reservation {ip} -> {mac}", bool(entry) and mac in entry.group(1).lower(),
                      "reservation not found" if not entry else "different MAC")

    print(f"\n{sum(results)}/{len(results)} checks passed.")
    return 0 if all(results) else 1


if __name__ == "__main__":
    sys.exit(main())
