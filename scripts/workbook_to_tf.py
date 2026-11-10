"""Convert a filled-in SCM bulk template into Terraform code (terraform/gen_*.tf).

One resource block per workbook row, with explicit depends_on so Terraform creates
objects in dependency order and removes them in reverse order (needed for undo).
Security and NAT rules are chained so they are created top to bottom in row order.

The workbook is validated first; nothing is written if it has errors. Every run
replaces all terraform/gen_*.tf files, so rows removed from the workbook become
deletions in the next plan.

Usage:  .venv\\Scripts\\python scripts\\workbook_to_tf.py <workbook.xlsx>
"""
import hashlib
import re
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import validate_workbook  # noqa: E402
from template_io import read_sheet, split_list  # noqa: E402

TF_DIR = Path(__file__).resolve().parent.parent / "terraform"
SCOPE_ROOT = "PANW"
PANW_REF = 'scm_folder.level1["PANW"].name'
YES = {"yes": True, "no": False}


class Expr(str):
    """A raw HCL expression (rendered without quotes)."""


def hcl(value, indent=0) -> str:
    pad, inner = "  " * indent, "  " * (indent + 1)
    if isinstance(value, Expr):
        return str(value)
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int):
        return str(value)
    if isinstance(value, str):
        escaped = value.replace("\\", "\\\\").replace('"', '\\"').replace("${", "$${").replace("%{", "%%{")
        return f'"{escaped}"'
    if isinstance(value, list):
        if not value:
            return "[]"
        if all(not isinstance(v, (dict, list)) for v in value):
            return "[" + ", ".join(hcl(v) for v in value) + "]"
        return "[\n" + ",\n".join(inner + hcl(v, indent + 1) for v in value) + f"\n{pad}]"
    if isinstance(value, dict):
        if not value:
            return "{}"
        width = max(len(k) for k in value)
        lines = [f"{inner}{k.ljust(width)} = {hcl(v, indent + 1)}" for k, v in value.items()]
        return "{\n" + "\n".join(lines) + f"\n{pad}}}"
    raise TypeError(f"cannot render {value!r}")


def clean(d: dict) -> dict:
    """Drop empty values so the provider keeps its defaults."""
    return {k: v for k, v in d.items() if v not in (None, "", [], {}) or isinstance(v, bool)}


def num(v):
    return int(float(v)) if v not in (None, "") else None


def yn(v):
    return YES.get((v or "").lower())


def slug(*parts) -> str:
    s = re.sub(r"[^a-z0-9]+", "_", "__".join(p for p in parts if p).lower()).strip("_")
    return s if s and s[0].isalpha() else f"r_{s}"


class Builder:
    def __init__(self, sheets: dict[str, list[dict]]):
        self.s = sheets
        self.blocks = defaultdict(list)        # file -> rendered blocks
        self.by_name = defaultdict(lambda: defaultdict(list))  # kind -> name -> [addresses]
        self.used = set()
        self.gen_folders = {r["name"] for r in sheets["Folders"]}
        self.gen_snippets = {r["name"] for r in sheets["Snippets"]}
        self.gen_labels = {r["name"] for r in sheets["Labels"]}

    # -- helpers ---------------------------------------------------------------
    def address(self, rtype, *parts):
        name, n = slug(*parts), 2
        while f"{rtype}.{name}" in self.used:
            name, n = f"{slug(*parts)}_{n}", n + 1
        self.used.add(f"{rtype}.{name}")
        return f"{rtype}.{name}"

    def folder_expr(self, name):
        if name == SCOPE_ROOT:
            return Expr(PANW_REF)
        if name in self.gen_folders:
            return Expr(f"{self.lookup('folder', name)[0]}.name")
        return name

    def snippet_expr(self, name):
        return Expr(f"{self.lookup('snippet', name)[0]}.name") if name in self.gen_snippets else name

    def label_list(self, names):
        return [Expr(f"{self.lookup('label', n)[0]}.name") if n in self.gen_labels else n for n in names]

    def container(self, r) -> dict:
        if r.get("folder"):
            return {"folder": self.folder_expr(r["folder"])}
        if r.get("snippet"):
            return {"snippet": self.snippet_expr(r["snippet"])}
        return {"device": r["device"]}

    def lookup(self, kind, name):
        return self.by_name[kind].get(name, [])

    def deps(self, *pairs):
        out = []
        for kind, names in pairs:
            for n in names:
                out += self.lookup(kind, n)
        return sorted(set(out))

    def emit(self, file, addr, body: dict, depends_on=(), comment=None):
        rtype, rname = addr.split(".", 1)
        body = clean(body)
        if depends_on:
            body["depends_on"] = [Expr(d) for d in depends_on]
        text = (f"# {comment}\n" if comment else "") + f'resource "{rtype}" "{rname}" ' + hcl(body) + "\n"
        self.blocks[file].append(text)

    def register(self, kind, name, addr):
        self.by_name[kind][name].append(addr)

    # -- sheets ----------------------------------------------------------------
    def build(self):
        S = self.s
        f0, f1, f2, f3 = "gen_00_structure.tf", "gen_10_objects.tf", "gen_20_network.tf", "gen_30_policy.tf"

        for r in S["Labels"]:
            a = self.address("scm_label", r["name"]); self.register("label", r["name"], a)
            self.emit(f0, a, {"name": r["name"], "description": r.get("description")})
        for r in S["Snippets"]:
            a = self.address("scm_snippet", r["name"]); self.register("snippet", r["name"], a)
        for r in S["Folders"]:
            a = self.address("scm_folder", r["name"]); self.register("folder", r["name"], a)

        folder_snippets = defaultdict(list)
        for r in S["Folder Snippets"]:
            folder_snippets[r["folder"]].append(r["snippet"])

        for r in S["Snippets"]:
            self.emit(f0, self.lookup("snippet", r["name"])[0], {
                "name": r["name"], "description": r.get("description"),
                "labels": self.label_list(split_list(r.get("labels")))})
        for r in S["Folders"]:
            self.emit(f0, self.lookup("folder", r["name"])[0], {
                "name": r["name"], "parent": self.folder_expr(r["parent"]), "description": r.get("description"),
                "labels": self.label_list(split_list(r.get("labels"))),
                "snippets": [self.snippet_expr(n) for n in folder_snippets.get(r["name"], [])]})
        panw = [self.snippet_expr(n) for n in folder_snippets.get(SCOPE_ROOT, [])]
        self.blocks[f0].append("# Snippets attached to the PANW folder (used in folders.tf)\n"
                               "locals {\n  panw_folder_snippets = " + hcl(panw, 1) + "\n}\n")

        # Objects
        for r in S["Tags"]:
            a = self.address("scm_tag", r.get("folder") or r.get("snippet"), r["name"]); self.register("tag", r["name"], a)
            self.emit(f1, a, {"name": r["name"], **self.container(r), "color": r.get("color"), "comments": r.get("comments")})
        declared = {}
        for r in S["Variables"]:
            scope = r.get("folder") or r.get("snippet") or f"dev_{r['device']}"
            a = self.address("scm_variable", scope, r["name"].lstrip("$"))
            deps = [] if not r.get("device") else declared.get(r["name"], [])
            if not r.get("device"):
                declared.setdefault(r["name"], []).append(a)
            self.register("variable", r["name"], a)
            self.emit(f1, a, {"name": r["name"], "type": r["type"], "value": r["value"], **self.container(r),
                              "description": r.get("description")}, deps)
        tag_dep = lambda r: ("tag", split_list(r.get("tag")))  # noqa: E731
        for r in S["Addresses"]:
            a = self.address("scm_address", r.get("folder") or r.get("snippet"), r["name"]); self.register("address", r["name"], a)
            attr = {"ip-netmask": "ip_netmask", "ip-range": "ip_range", "ip-wildcard": "ip_wildcard", "fqdn": "fqdn"}[r["type"]]
            self.emit(f1, a, {"name": r["name"], **self.container(r), attr: r["value"], "description": r.get("description"),
                              "tag": split_list(r.get("tag"))}, self.deps(tag_dep(r)))
        for r in S["Address Groups"]:
            a = self.address("scm_address_group", r.get("folder") or r.get("snippet"), r["name"])
            members = split_list(r.get("static"))
            body = {"name": r["name"], **self.container(r), "description": r.get("description"), "tag": split_list(r.get("tag"))}
            body |= {"static": members} if r["group_type"] == "static" else {"dynamic": {"filter": r["filter"]}}
            self.emit(f1, a, body, self.deps(tag_dep(r), ("address", members)))
            self.register("address", r["name"], a)
        for r in S["Services"]:
            a = self.address("scm_service", r.get("folder") or r.get("snippet"), r["name"]); self.register("service", r["name"], a)
            override = clean({"timeout": num(r.get("override_timeout")),
                              "halfclose_timeout": num(r.get("override_halfclose_timeout")) if r["protocol"] == "tcp" else None,
                              "timewait_timeout": num(r.get("override_timewait_timeout")) if r["protocol"] == "tcp" else None})
            proto = clean({"port": r["port"], "source_port": r.get("source_port"), "override": override})
            self.emit(f1, a, {"name": r["name"], **self.container(r), "description": r.get("description"),
                              "protocol": {r["protocol"]: proto}, "tag": split_list(r.get("tag"))}, self.deps(tag_dep(r)))
        for r in S["Service Groups"]:
            a = self.address("scm_service_group", r.get("folder") or r.get("snippet"), r["name"])
            members = split_list(r["members"])
            self.emit(f1, a, {"name": r["name"], **self.container(r), "members": members, "tag": split_list(r.get("tag"))},
                      self.deps(tag_dep(r), ("service", members)))
            self.register("service", r["name"], a)

        # Network
        rtypes = {"ethernet": "scm_ethernet_interface", "layer3-subinterface": "scm_layer3_subinterface",
                  "loopback": "scm_loopback_interface", "tunnel": "scm_tunnel_interface"}
        vars_in = lambda *vals: [v for val in vals for v in split_list(val) if v.startswith("$")]  # noqa: E731
        for r in S["Interfaces"]:
            a = self.address(rtypes[r["interface_type"]], r.get("folder") or r.get("snippet"), r["name"])
            ips = [{"name": ip} for ip in split_list(r.get("ip"))]
            dhcp = {"enable": True, "create_default_route": yn(r.get("dhcp_create_default_route"))} \
                if yn(r.get("dhcp_client")) else None
            l3 = clean({"ip": ips, "dhcp_client": clean(dhcp) if dhcp else None, "mtu": num(r.get("mtu")),
                        "interface_management_profile": r.get("interface_management_profile")})
            body = {"name": r["name"], **self.container(r), "comment": r.get("comment")}
            deps = [("variable", vars_in(r.get("ip"), r.get("name")))]
            t = r["interface_type"]
            if t == "ethernet":
                body |= {"link_speed": r.get("link_speed"), "link_duplex": r.get("link_duplex"), "link_state": r.get("link_state")}
                mode = r["mode"]
                if mode == "layer3":
                    body["layer3"] = Expr("{}") if not l3 else l3
                elif mode == "layer2":
                    body["layer2"] = clean({"vlan_tag": r.get("vlan_tag")}) or Expr("{}")
                elif mode == "tap":
                    body["tap"] = Expr("{}")
                else:
                    body["aggregate_group"] = r.get("aggregate_group")
            elif t == "layer3-subinterface":
                body |= {"parent_interface": r["parent_interface"], "tag": num(r["vlan_tag"])} | l3
                deps.append(("interface", [r["parent_interface"]]))
            else:
                body |= l3
            self.emit(f2, a, body, self.deps(*deps))
            self.register("interface", r["name"], a)
        for r in S["Zones"]:
            a = self.address("scm_zone", r.get("folder") or r.get("snippet"), r["name"]); self.register("zone", r["name"], a)
            ifaces = split_list(r.get("interfaces"))
            network = clean({r["zone_type"]: ifaces or Expr("[]"), "zone_protection_profile": r.get("zone_protection_profile"),
                             "log_setting": r.get("log_setting")})
            self.emit(f2, a, {"name": r["name"], **self.container(r), "network": network,
                              "enable_user_identification": yn(r.get("enable_user_identification")),
                              "enable_device_identification": yn(r.get("enable_device_identification"))},
                      self.deps(("interface", ifaces)))
        routes = defaultdict(list)
        for r in S["Routes"]:
            routes[(r["logical_router"], r["vrf_name"])].append(r)
        routers = defaultdict(list)
        for r in S["Logical Routers"]:
            routers[(r.get("folder") or r.get("snippet"), r["name"])].append(r)
        for (scope, name), vrf_rows in routers.items():
            a = self.address("scm_logical_router", scope, name); self.register("router", name, a)
            vrfs, iface_deps, var_deps = [], [], []
            for v in vrf_rows:
                ifaces = split_list(v.get("interfaces"))
                iface_deps += ifaces
                static = []
                for rt in routes.get((name, v["vrf_name"]), []):
                    nh_type, nh = rt["nexthop_type"], rt.get("nexthop")
                    nexthop = {nh_type: nh} if nh_type in ("ip_address", "next_lr", "fqdn") else \
                        {"discard": Expr("{}")} if nh_type == "discard" else None
                    var_deps += vars_in(nh, rt.get("interface"))
                    static.append(clean({"name": rt["name"], "destination": rt["destination"], "interface": rt.get("interface"),
                                         "metric": num(rt.get("metric")), "admin_dist": num(rt.get("admin_dist")),
                                         "nexthop": nexthop}))
                ecmp = yn(v.get("ecmp_enable"))
                vrfs.append(clean({"name": v["vrf_name"], "interface": ifaces,
                                   "ecmp": {"enable": ecmp} if ecmp is not None else None,
                                   "routing_table": {"ip": {"static_route": static}} if static else None}))
            self.emit(f2, a, {"name": name, **self.container(vrf_rows[0]), "vrf": vrfs},
                      self.deps(("interface", iface_deps), ("variable", var_deps)))

        # Policy - each rule depends on the previous one in the same container + rulebase (row order)
        last = {}
        for r in S["Security Rules"]:
            a = self.address("scm_security_rule", r.get("folder") or r.get("snippet"), r["name"])
            key = ("sec", r.get("folder") or r.get("snippet"), r.get("position") or "pre")
            group = split_list(r.get("profile_group"))
            body = {"name": r["name"], **self.container(r), "position": r.get("position") or "pre",
                    "description": r.get("description"), "from": split_list(r["from"]), "to": split_list(r["to"]),
                    "source": split_list(r["source"]), "negate_source": yn(r.get("negate_source")),
                    "source_user": split_list(r["source_user"]), "destination": split_list(r["destination"]),
                    "negate_destination": yn(r.get("negate_destination")), "application": split_list(r["application"]),
                    "service": split_list(r["service"]), "category": split_list(r.get("category")) or ["any"],
                    "action": r["action"], "profile_setting": {"group": group} if group else None,
                    "log_start": yn(r.get("log_start")), "log_end": yn(r.get("log_end")),
                    "log_setting": r.get("log_setting"), "schedule": r.get("schedule"), "disabled": yn(r.get("disabled")),
                    "tag": split_list(r.get("tag"))}
            deps = self.deps(("zone", body["from"] + body["to"]), ("address", body["source"] + body["destination"]),
                             ("service", body["service"]), tag_dep(r)) + ([last[key]] if key in last else [])
            self.emit(f3, a, body, sorted(set(deps)), comment=f"security rule, row {r['_row']}")
            last[key] = a
        for r in S["NAT Rules"]:
            a = self.address("scm_nat_rule", r.get("folder") or r.get("snippet"), r["name"])
            key = ("nat", r.get("folder") or r.get("snippet"), r.get("position") or "pre")
            st = r["source_translation"]
            translated = split_list(r.get("src_translated_address"))
            if st == "dynamic_ip_and_port":
                src = {st: {"interface_address": clean({"interface": r["src_interface"], "ip": r.get("src_interface_ip")})}
                       if r.get("src_interface") else {"translated_address": translated}}
            elif st == "dynamic_ip":
                src = {st: {"translated_address": translated}}
            elif st == "static_ip":
                src = {st: clean({"translated_address": translated[0] if translated else None,
                                  "bi_directional": r.get("static_bi_directional")})}
            else:
                src = None
            dst = clean({"translated_address": r.get("dst_translated_address"), "translated_port": num(r.get("dst_translated_port"))})
            body = {"name": r["name"], **self.container(r), "position": r.get("position") or "pre",
                    "nat_type": r.get("nat_type") or "ipv4", "description": r.get("description"),
                    "from": split_list(r["from"]), "to": split_list(r["to"]), "to_interface": r.get("to_interface"),
                    "source": split_list(r["source"]), "destination": split_list(r["destination"]), "service": r["service"],
                    "source_translation": src, "destination_translation": dst or None,
                    "disabled": yn(r.get("disabled")), "tag": split_list(r.get("tag"))}
            deps = self.deps(("zone", body["from"] + body["to"]), ("address", body["source"] + body["destination"]),
                             ("service", [r["service"]]), ("interface", [r.get("to_interface"), r.get("src_interface")]),
                             tag_dep(r)) + ([last[key]] if key in last else [])
            self.emit(f3, a, body, sorted(set(deps)), comment=f"NAT rule, row {r['_row']}")
            last[key] = a
        return self.blocks


def main() -> int:
    if len(sys.argv) != 2:
        print(__doc__)
        return 2
    path = Path(sys.argv[1])
    if validate_workbook.main([str(path)]) != 0:
        print("\nWorkbook has errors - no Terraform files were written.")
        return 1
    sheets = {n: read_sheet(path, n) for n in (
        "Labels", "Folders", "Snippets", "Folder Snippets", "Tags", "Variables", "Addresses", "Address Groups",
        "Services", "Service Groups", "Interfaces", "Zones", "Logical Routers", "Routes", "Security Rules", "NAT Rules")}
    blocks = Builder(sheets).build()

    digest = hashlib.sha256(path.read_bytes()).hexdigest()[:12]
    header = (f"# GENERATED by scripts/workbook_to_tf.py from {path.name} (sha256 {digest}).\n"
              "# Do not edit by hand: change the workbook and re-run the converter.\n\n")
    for old in TF_DIR.glob("gen_*.tf"):
        old.unlink()
    for file in ("gen_00_structure.tf", "gen_10_objects.tf", "gen_20_network.tf", "gen_30_policy.tf"):
        (TF_DIR / file).write_text(header + "\n".join(blocks.get(file, [])), encoding="utf-8")
    total = sum(1 for bl in blocks.values() for b in bl if 'resource "' in b)
    print(f"\nWrote {', '.join(f for f in sorted(blocks))} in {TF_DIR} ({total} resource blocks).")
    print("Next: terraform -chdir=terraform fmt; terraform -chdir=terraform plan")
    return 0


if __name__ == "__main__":
    sys.exit(main())
