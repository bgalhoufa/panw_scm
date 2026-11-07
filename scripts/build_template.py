"""Build the SCM bulk-input Excel template (templates/SCM_bulk_template.xlsx).

One sheet per object type. Row 1 holds the field names (Terraform argument names,
or API field names for the Firewalls sheet), row 2 the help text, row 3
Required / Conditional / Optional, row 4 an example, and data starts on row 5.

Usage:  .venv\\Scripts\\python scripts\\build_template.py [output.xlsx]
"""
import sys
from pathlib import Path

from openpyxl import Workbook
from openpyxl.comments import Comment
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.datavalidation import DataValidation

DEFAULT_OUT = Path(__file__).resolve().parent.parent / "templates" / "SCM_bulk_template.xlsx"

R, C, O = "Required", "Conditional", "Optional"
YN = ["yes", "no"]
SEP = "Separate multiple values with ;"
CONTAINER_F = ("folder", C, "SCM folder (PANW or a folder below it). Exactly one of folder / snippet per row.", None)
CONTAINER_S = ("snippet", C, "Snippet name, instead of folder. Exactly one of folder / snippet per row.", None)
TAG = ("tag", O, f"Tags, from the Tags sheet or already in SCM. {SEP}", None)

VAR_TYPES = ["ip-netmask", "ip-range", "ip-wildcard", "fqdn", "zone", "port", "as-number", "router-id",
             "egress-max", "link-tag", "group-id", "rate", "timer", "percent", "count",
             "device-priority", "device-id", "qos-profile"]
TAG_COLORS = ["Red", "Green", "Blue", "Yellow", "Copper", "Orange", "Purple", "Gray", "Light Green", "Cyan",
              "Light Gray", "Blue Gray", "Lime", "Black", "Gold", "Brown", "Olive", "Maroon", "Red-Orange",
              "Yellow-Orange", "Forest Green", "Turquoise Blue", "Azure Blue", "Cerulean Blue", "Midnight Blue",
              "Medium Blue", "Cobalt Blue", "Violet Blue", "Blue Violet", "Medium Violet", "Medium Rose",
              "Lavender", "Orchid", "Thistle", "Peach", "Salmon", "Magenta", "Red Violet", "Mahogany",
              "Burnt Sienna", "Chestnut"]
# Dropdowns longer than Excel's 255-character inline limit are read from the hidden Lists sheet.
LONG_LISTS = {"tag_colors": TAG_COLORS}

# (sheet name, how it is deployed, purpose, columns, example row)
SHEETS = [
    ("Folders", "scm_folder", "SCM folders. Parent of top-level folders is PANW.",
     [("name", R, "Folder name. Letters, numbers, space, - _ . (max 64).", None),
      ("parent", R, "Parent folder: PANW or another folder in this sheet (listed above it).", None),
      ("description", O, "Free text.", None),
      ("labels", O, f"Labels (must already exist). {SEP}", None)],
     ["EXAMPLE-SITES", "PANW", "All branch sites", ""]),

    ("Snippets", "scm_snippet", "Reusable configuration snippets.",
     [("name", R, "Snippet name.", None),
      ("description", O, "Free text.", None),
      ("labels", O, f"Labels (must already exist). {SEP}", None)],
     ["EXAMPLE-baseline", "Common objects for all PANW sites", ""]),

    ("Folder Snippets", "scm_folder.snippets", "Which snippets are attached to which folder. One row per folder + snippet pair.",
     [("folder", R, "PANW or a folder from the Folders sheet.", None),
      ("snippet", R, "Snippet from the Snippets sheet or already in SCM.", None)],
     ["EXAMPLE-SITES", "EXAMPLE-baseline"]),

    ("Tags", "scm_tag", "Tags used by addresses, groups, services and rules.",
     [("name", R, "Tag name (max 127).", None),
      CONTAINER_F, CONTAINER_S,
      ("color", O, "Tag colour.", "tag_colors"),
      ("comments", O, "Description.", None)],
     ["EXAMPLE-prod", "PANW", "", "Red", "Production systems"]),

    ("Variables", "scm_variable", "Variables, used as $name in other sheets.",
     [("name", R, "Variable name, must start with $ (e.g. $wan_ip).", None),
      ("type", R, "Variable type.", VAR_TYPES),
      ("value", R, "Default value, matching the type (e.g. 203.0.113.10/30).", None),
      CONTAINER_F, CONTAINER_S,
      ("description", O, "Free text.", None)],
     ["$EXAMPLE_wan_ip", "ip-netmask", "203.0.113.10/30", "EXAMPLE-SITES", "", "WAN IP per site"]),

    ("Addresses", "scm_address", "Address objects.",
     [("name", R, "Object name (max 63).", None),
      CONTAINER_F, CONTAINER_S,
      ("type", R, "Address type.", ["ip-netmask", "ip-range", "ip-wildcard", "fqdn"]),
      ("value", R, "ip-netmask: 10.1.1.0/24 · ip-range: 10.1.1.10-10.1.1.20 · ip-wildcard: 10.0.0.1/0.255.0.255 · fqdn: www.example.com", None),
      ("description", O, "Free text.", None),
      TAG],
     ["EXAMPLE-net-users", "PANW", "", "ip-netmask", "10.10.0.0/16", "User LAN", "EXAMPLE-prod"]),

    ("Address Groups", "scm_address_group", "Address groups (static or dynamic).",
     [("name", R, "Group name.", None),
      CONTAINER_F, CONTAINER_S,
      ("group_type", R, "static = list of members · dynamic = tag filter.", ["static", "dynamic"]),
      ("static", C, f"Required if static: member address / group names. {SEP}", None),
      ("filter", C, "Required if dynamic: tag filter, e.g. 'web' and 'prod'.", None),
      ("description", O, "Free text.", None),
      TAG],
     ["EXAMPLE-grp-servers", "PANW", "", "static", "EXAMPLE-net-users;EXAMPLE-srv-web", "", "Internal servers", ""]),

    ("Services", "scm_service", "Service objects (TCP / UDP ports).",
     [("name", R, "Service name.", None),
      CONTAINER_F, CONTAINER_S,
      ("protocol", R, "Protocol.", ["tcp", "udp"]),
      ("port", R, "Destination port(s): 443 · 8000-8080 · 80,443,8443", None),
      ("source_port", O, "Source port(s), same format. Usually empty.", None),
      ("override_timeout", O, "Session timeout in seconds (overrides the app default).", None),
      ("override_halfclose_timeout", O, "TCP only: half-close timeout in seconds.", None),
      ("override_timewait_timeout", O, "TCP only: time-wait timeout in seconds.", None),
      ("description", O, "Free text.", None),
      TAG],
     ["EXAMPLE-tcp-8443", "PANW", "", "tcp", "8443", "", "", "", "", "Alt HTTPS", ""]),

    ("Service Groups", "scm_service_group", "Service groups.",
     [("name", R, "Group name.", None),
      CONTAINER_F, CONTAINER_S,
      ("members", R, f"Service / service group names. {SEP}", None),
      TAG],
     ["EXAMPLE-svc-web", "PANW", "", "service-http;service-https;EXAMPLE-tcp-8443", ""]),

    ("Interfaces", "scm_ethernet_interface · scm_layer3_subinterface · scm_loopback_interface · scm_tunnel_interface",
     "Interfaces. Assign them to zones in the Zones sheet and to routers in Logical Routers.",
     [("interface_type", R, "Which kind of interface.", ["ethernet", "layer3-subinterface", "loopback", "tunnel"]),
      ("name", R, "ethernet: ethernet1/1 (or $variable) · subinterface: ethernet1/1.100 · loopback: loopback.1 · tunnel: tunnel.1", None),
      CONTAINER_F, CONTAINER_S,
      ("mode", C, "ethernet only. layer3 (routed), layer2, tap, or aggregate (member of an AE group).", ["layer3", "layer2", "tap", "aggregate"]),
      ("aggregate_group", C, "ethernet + mode aggregate: AE group, e.g. ae1.", None),
      ("parent_interface", C, "layer3-subinterface only: parent, e.g. ethernet1/1.", None),
      ("vlan_tag", C, "layer3-subinterface: VLAN tag (1-4094). ethernet layer2: VLAN tag.", None),
      ("ip", C, f"Layer 3 IPs with mask, e.g. 10.1.1.1/24 or $variable. {SEP} Leave empty if dhcp_client = yes.", None),
      ("dhcp_client", O, "ethernet layer3 / subinterface: get the IP by DHCP.", YN),
      ("dhcp_create_default_route", O, "With DHCP: install the default route from the server.", YN),
      ("interface_management_profile", O, "Existing interface management profile (ping, SSH, ...).", None),
      ("mtu", O, "MTU (576-9216). Empty = default 1500.", None),
      ("link_speed", O, "ethernet only.", ["auto", "10", "100", "1000", "10000", "40000", "100000"]),
      ("link_duplex", O, "ethernet only.", ["auto", "half", "full"]),
      ("link_state", O, "ethernet only.", ["auto", "up", "down"]),
      ("comment", O, "Interface description.", None)],
     ["ethernet", "ethernet1/1", "EXAMPLE-SITES", "", "layer3", "", "", "", "$EXAMPLE_wan_ip", "no", "",
      "", "", "auto", "auto", "auto", "WAN uplink"]),

    ("Zones", "scm_zone", "Security zones and their interfaces.",
     [("name", R, "Zone name: letters, numbers, . _ - (begins with a letter).", None),
      CONTAINER_F, CONTAINER_S,
      ("zone_type", R, "Zone type; must match the interfaces' mode.", ["layer3", "layer2", "virtual_wire", "tap", "external"]),
      ("interfaces", O, f"Interfaces in this zone (from the Interfaces sheet). {SEP}", None),
      ("zone_protection_profile", O, "Existing zone protection profile.", None),
      ("log_setting", O, "Existing log forwarding profile.", None),
      ("enable_user_identification", O, "Enable User-ID.", YN),
      ("enable_device_identification", O, "Enable Device-ID.", YN)],
     ["EXAMPLE-untrust", "EXAMPLE-SITES", "", "layer3", "ethernet1/1", "", "", "no", "no"]),

    ("Logical Routers", "scm_logical_router", "One row per router + VRF. Static routes go in the Routes sheet.",
     [("name", R, "Logical router name.", None),
      CONTAINER_F, CONTAINER_S,
      ("vrf_name", R, "VRF name. Use 'default' unless you need several VRFs.", None),
      ("interfaces", O, f"Layer 3 interfaces in this VRF. {SEP}", None),
      ("ecmp_enable", O, "Enable ECMP in this VRF.", YN)],
     ["EXAMPLE-lr", "EXAMPLE-SITES", "", "default", "ethernet1/1;loopback.1", "no"]),

    ("Routes", "scm_logical_router (vrf.routing_table.ip.static_route)", "IPv4 static routes, added to the router + VRF from the Logical Routers sheet.",
     [("logical_router", R, "Router name from the Logical Routers sheet.", None),
      ("vrf_name", R, "VRF of that router (e.g. default).", None),
      ("name", R, "Route name (unique inside the VRF).", None),
      ("destination", R, "Destination prefix, e.g. 0.0.0.0/0 or 10.20.0.0/16.", None),
      ("nexthop_type", R, "ip_address = gateway IP · next_lr = another logical router · fqdn · discard = blackhole · none = interface only.",
       ["ip_address", "next_lr", "fqdn", "discard", "none"]),
      ("nexthop", C, "Value for ip_address / next_lr / fqdn (IP or $variable, router name, FQDN). Empty for discard / none.", None),
      ("interface", O, "Egress interface (required when nexthop_type = none).", None),
      ("metric", O, "Metric (1-65535). Empty = 10.", None),
      ("admin_dist", O, "Administrative distance (10-240). Empty = default.", None)],
     ["EXAMPLE-lr", "default", "default-route", "0.0.0.0/0", "ip_address", "203.0.113.9", "ethernet1/1", "10", ""]),

    ("Security Rules", "scm_security_rule", "Security policy. Rules are created in the order of the rows (top = first).",
     [("name", R, "Rule name (max 63).", None),
      CONTAINER_F, CONTAINER_S,
      ("position", O, "pre (default) or post rulebase.", ["pre", "post"]),
      ("from", R, f"Source zone(s) or any. {SEP}", None),
      ("to", R, f"Destination zone(s) or any. {SEP}", None),
      ("source", R, f"Source addresses / groups / any. {SEP}", None),
      ("negate_source", O, "Negate the source.", YN),
      ("source_user", R, f"Users / groups, or any. {SEP}", None),
      ("destination", R, f"Destination addresses / groups / any. {SEP}", None),
      ("negate_destination", O, "Negate the destination.", YN),
      ("application", R, f"Applications or any. {SEP}", None),
      ("service", R, f"application-default, any, or service / group names. {SEP}", None),
      ("category", O, f"URL categories. Empty = any. {SEP}", None),
      ("action", R, "Action.", ["allow", "deny", "drop", "reset-client", "reset-server", "reset-both"]),
      ("profile_group", O, "Security profile group (e.g. best-practice).", None),
      ("log_start", O, "Log at session start.", YN),
      ("log_end", O, "Log at session end (default yes).", YN),
      ("log_setting", O, "Log forwarding profile.", None),
      ("schedule", O, "Existing schedule object.", None),
      ("disabled", O, "Create the rule disabled.", YN),
      ("description", O, "Free text.", None),
      TAG],
     ["EXAMPLE-allow-web", "PANW", "", "pre", "EXAMPLE-trust", "EXAMPLE-untrust", "EXAMPLE-net-users", "no", "any",
      "any", "no", "web-browsing;ssl", "application-default", "", "allow", "best-practice", "no", "yes", "", "", "no",
      "Users to Internet", ""]),

    ("NAT Rules", "scm_nat_rule", "NAT policy. Rules are created in the order of the rows (top = first).",
     [("name", R, "Rule name.", None),
      CONTAINER_F, CONTAINER_S,
      ("position", O, "pre (default) or post rulebase.", ["pre", "post"]),
      ("nat_type", O, "Default ipv4.", ["ipv4", "nat64", "nptv6"]),
      ("from", R, f"Source zone(s) of the original packet. {SEP}", None),
      ("to", R, "Destination zone of the original packet (one zone).", None),
      ("to_interface", O, "Destination interface of the original packet. Empty = any.", None),
      ("source", R, f"Original source addresses or any. {SEP}", None),
      ("destination", R, f"Original destination addresses or any. {SEP}", None),
      ("service", R, "Original service: any or one service name.", None),
      ("source_translation", R, "Source NAT type. none = no source NAT.", ["none", "dynamic_ip_and_port", "dynamic_ip", "static_ip"]),
      ("src_translated_address", C, f"dynamic_ip_and_port / dynamic_ip: translated IPs or objects ({SEP}). static_ip: one IP / object.", None),
      ("src_interface", C, "dynamic_ip_and_port: use this interface's IP instead of an address (e.g. ethernet1/1).", None),
      ("src_interface_ip", O, "With src_interface: which interface IP to use (if it has several).", None),
      ("static_bi_directional", O, "static_ip only: also create the reverse NAT.", YN),
      ("dst_translated_address", O, "Destination NAT: translated IP / object. Empty = no destination NAT.", None),
      ("dst_translated_port", O, "Destination NAT: translated port.", None),
      ("disabled", O, "Create the rule disabled.", YN),
      ("description", O, "Free text.", None),
      TAG],
     ["EXAMPLE-snat-internet", "PANW", "", "pre", "ipv4", "EXAMPLE-trust", "EXAMPLE-untrust", "ethernet1/1",
      "EXAMPLE-net-users", "any", "any", "dynamic_ip_and_port", "", "ethernet1/1", "", "", "", "", "no",
      "Users hide-NAT to WAN", ""]),

    ("Firewalls", "SCM API PUT /config/setup/v1/devices/{serial} (scripts/scm_devices.py)",
     "Firewalls already registered to the tenant: put each one in its folder and set labels / snippets.",
     [("serial_number", R, "Firewall serial number, e.g. 021201119434. It must already appear in SCM (registered to this tenant).", None),
      ("folder", R, "Target folder: PANW or a folder below it.", None),
      ("display_name", O, "Name shown in SCM. Empty = keep the current one.", None),
      ("description", O, "Free text. Empty = keep the current one.", None),
      ("labels", O, f"Device labels (must already exist). {SEP} Empty = keep the current ones.", None),
      ("snippets", O, f"Snippets applied to this firewall only. {SEP} Empty = keep the current ones.", None)],
     ["EXAMPLE-0123456789", "EXAMPLE-SITES", "FW-BRANCH-01", "Branch 01 PA-440", "BRANCH", ""]),
]

README_ROWS = [
    ("SCM bulk input template", None),
    ("Purpose", "Fill this workbook offline and send it back. Each row becomes one object in Strata Cloud Manager; Claude turns the sheets into Terraform code (and, for firewalls, a device update) and shows you a plan before anything is applied."),
    ("Scope", "Everything must live in the PANW folder or a folder below it, or in a snippet. Other folders are read-only for this project."),
    ("", None),
    ("How each sheet is laid out", None),
    ("Row 1", "Field name. It is the Terraform / API field name, so do not rename, move or delete columns."),
    ("Row 2", "What to enter and the accepted format (hover the field name for the same text)."),
    ("Row 3", "Required / Conditional / Optional (colours below)."),
    ("Row 4", "Grey example row. Rows whose first cell starts with EXAMPLE are ignored, so you can keep or delete it."),
    ("Row 5 and below", "Your data, one object per row. Leave optional cells empty to use the SCM default."),
    ("", None),
    ("Colour legend", None),
    (R, "Must be filled in on every row."),
    (C, "Required only in some cases (explained in row 2), e.g. exactly one of folder / snippet."),
    (O, "Leave empty for the default."),
    ("", None),
    ("Conventions", None),
    ("Lists", "Several values in one cell are separated by ;  e.g.  web-browsing;ssl"),
    ("Yes / no", "Use the dropdown (yes / no)."),
    ("any", "Type any where a rule should match everything (zones, addresses, users, applications, services)."),
    ("Variables", "Names start with $. Define them in the Variables sheet and use them in IP / interface fields, e.g. $wan_ip."),
    ("Existing objects", "Labels, security profiles, log profiles, schedules and management profiles must already exist in SCM; they are not created from this file."),
    ("Rule order", "Security and NAT rules are created in row order; the first row is the top of the rulebase."),
    ("", None),
    ("Folders and snippets", "Folder Snippets attaches snippets to folders (applies to every firewall in that folder and below). The snippets column of the Firewalls sheet attaches snippets to one firewall only."),
    ("Firewalls", "The firewall must already be registered to this SCM tenant (it appears in the device list), e.g. through the Customer Support Portal or by connecting it with its device certificate. The SCM API cannot register a new serial number; it can only place an existing firewall in a folder and set its name, labels and snippets. Unknown serial numbers are reported and skipped."),
    ("", None),
    ("Deployment order", "Folders → Snippets → Folder Snippets → Tags → Variables → Addresses → Address Groups → Services → Service Groups → Interfaces → Zones → Logical Routers → Routes → Security Rules → NAT Rules → Firewalls. Sheets are in that order; references only need to point to objects on an earlier sheet or already in SCM. Firewalls are moved last, once their folder and its configuration exist."),
    ("After the plan", "Applying writes to the SCM candidate config only. Pushing it to the firewalls is done manually in SCM by the repo owner."),
    ("", None),
    ("Sheet → how it is deployed", None),
]

ARIAL = "Arial"
FILL = {R: PatternFill("solid", fgColor="FFC7CE"), C: PatternFill("solid", fgColor="FFE699"),
        O: PatternFill("solid", fgColor="DDEBF7")}
HEAD_FILL = PatternFill("solid", fgColor="1F3864")
EX_FILL = PatternFill("solid", fgColor="F2F2F2")
_thin = Side(style="thin", color="BFBFBF")
BORDER = Border(left=_thin, right=_thin, top=_thin, bottom=_thin)
DATA_ROWS = 500  # rows 5..504 get dropdowns and fonts


def build(out: Path) -> None:
    wb = Workbook()
    ws = wb.active
    ws.title = "README"
    ws.sheet_view.showGridLines = False
    ws.column_dimensions["A"].width = 26
    ws.column_dimensions["B"].width = 100
    rows = README_ROWS + [(name, how) for name, how, *_ in SHEETS]
    for i, (a, b) in enumerate(rows, start=1):
        ca, cb = ws.cell(i, 1, a), ws.cell(i, 2, b)
        ca.font = Font(name=ARIAL, bold=True, size=10)
        cb.font = Font(name=ARIAL, size=10)
        cb.alignment = Alignment(wrap_text=True, vertical="top")
        ca.alignment = Alignment(vertical="top")
        if b is None and a:
            ca.font = Font(name=ARIAL, bold=True, size=11, color="1F3864")
        if a in FILL:
            ca.fill = FILL[a]
    ws["A1"].font = Font(name=ARIAL, bold=True, size=14, color="1F3864")

    lists = wb.create_sheet("Lists")
    list_ranges = {}
    for col, (key, values) in enumerate(LONG_LISTS.items(), start=1):
        lists.cell(1, col, key).font = Font(name=ARIAL, bold=True)
        for r, v in enumerate(values, start=2):
            lists.cell(r, col, v).font = Font(name=ARIAL)
        letter = get_column_letter(col)
        list_ranges[key] = f"Lists!${letter}$2:${letter}${len(values) + 1}"
    lists.sheet_state = "hidden"

    for name, _how, _purpose, cols, example in SHEETS:
        assert len(cols) == len(example), name
        s = wb.create_sheet(name, index=len(wb.sheetnames) - 1)  # keep Lists last
        s.freeze_panes = "B5"
        for j, (field, req, desc, choices) in enumerate(cols, start=1):
            letter = get_column_letter(j)
            values = LONG_LISTS.get(choices) if isinstance(choices, str) else choices
            h = s.cell(1, j, field)
            h.font = Font(name=ARIAL, bold=True, color="FFFFFF", size=10)
            h.fill = HEAD_FILL
            allowed = f"\nAllowed: {', '.join(values)}" if values else ""
            h.comment = Comment(desc + allowed, "template")
            shown = f"  [{' | '.join(values)}]" if values and not isinstance(choices, str) else ""
            d = s.cell(2, j, desc + shown + ("  [see dropdown]" if isinstance(choices, str) else ""))
            d.font = Font(name=ARIAL, size=8, italic=True, color="404040")
            d.alignment = Alignment(wrap_text=True, vertical="top")
            r = s.cell(3, j, req)
            r.font = Font(name=ARIAL, size=9, bold=True)
            r.fill = FILL[req]
            r.alignment = Alignment(horizontal="center")
            e = s.cell(4, j, example[j - 1] if example[j - 1] != "" else None)
            e.font = Font(name=ARIAL, size=10, italic=True, color="808080")
            e.fill = EX_FILL
            for row in range(1, 5):
                s.cell(row, j).border = BORDER
            s.column_dimensions[letter].width = max(len(field) + 4, min(len(str(example[j - 1])) + 4, 40), 14)
            if values:
                formula = list_ranges[choices] if isinstance(choices, str) else '"' + ",".join(values) + '"'
                dv = DataValidation(type="list", formula1=formula, allow_blank=True, showErrorMessage=True,
                                    errorTitle="Invalid value", error="Pick a value from the list.")
                dv.add(f"{letter}5:{letter}{DATA_ROWS + 4}")
                s.add_data_validation(dv)
            for row in range(5, 5 + DATA_ROWS):
                s.cell(row, j).font = Font(name=ARIAL, size=10)
        s.row_dimensions[2].height = 60
        s.sheet_properties.tabColor = "C55A11" if name == "Firewalls" else "1F3864"

    out.parent.mkdir(parents=True, exist_ok=True)
    wb.save(out)
    print(f"saved {out}: {', '.join(wb.sheetnames)}")


if __name__ == "__main__":
    build(Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_OUT)
