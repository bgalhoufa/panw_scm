"""Configure what SCM's API cannot, directly on each firewall over SSH, then commit.

Per firewall (matched to its Firewalls row by serial number):
  - factory cleanup removes the factory-default virtual wire (ethernet1/1 + 1/2, zones trust / untrust,
                    rule1): its local definitions override SCM's layer 3 interfaces and the push fails
                    ("zone ... type and interface ethernet1/1 type mismatch"). Each object is deleted
                    only if it still looks like the factory default. Run the baseline before the first push.
  - hostname        SITE<site_id>, e.g. SITE003
  - SNMPv3          read-only view + user (auth SHA, priv AES), SNMP allowed on the management port
  - superadmins     local administrators nso and drctd (role-based superuser)

Secrets come from .env and are never printed (placeholders, to be changed after the rollout):
  FW_ADMIN_NSO_PASSWORD, FW_ADMIN_DRCTD_PASSWORD, SNMPV3_USER, SNMPV3_AUTH_PASSWORD, SNMPV3_PRIV_PASSWORD
SSH login per firewall (an admin with write rights - not the read-only claude-ro):
  FWn_HOST, FWn_SSH_USER, FWn_SSH_PASSWORD   (or shared FW_SSH_USER / FW_SSH_PASSWORD)

Default is a dry run: shows the commands per Firewalls row, secrets masked, without connecting.
--apply connects to the given firewalls, checks the serial against the workbook, sends the
commands in configure mode and commits.

Usage:
  .venv\\Scripts\\python scripts\\fw_ssh_baseline.py inputs\\rollout.xlsx [--wave N]
  .venv\\Scripts\\python scripts\\fw_ssh_baseline.py inputs\\rollout.xlsx --apply FW1 FW2
"""
import argparse
import os
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from scm_auth_check import load_env_file  # noqa: E402
from template_io import read_sheet  # noqa: E402

PROMPT = re.compile(r"[\r\n][^\r\n]*@[^\r\n]*[>#] ?$")
ADMINS = {"nso": "FW_ADMIN_NSO_PASSWORD", "drctd": "FW_ADMIN_DRCTD_PASSWORD"}
SNMP_VIEW = "ro-all"
SECRET_KEYS = list(ADMINS.values()) + ["SNMPV3_AUTH_PASSWORD", "SNMPV3_PRIV_PASSWORD", "FW_SSH_PASSWORD"]
# Factory-default objects (PA-400 series) that clash with the interfaces SCM pushes, in delete order:
# (configure-mode check, text the check must show for it to still be the factory default, delete command)
FACTORY_DEFAULTS = [
    ("show rulebase security rules rule1", "untrust", "delete rulebase security rules rule1"),
    ("show zone trust", "virtual-wire", "delete zone trust"),
    ("show zone untrust", "virtual-wire", "delete zone untrust"),
    ("show network virtual-wire default-vwire", "ethernet1/", "delete network virtual-wire default-vwire"),
    ("show network interface ethernet ethernet1/1", "virtual-wire", "delete network interface ethernet ethernet1/1"),
    ("show network interface ethernet ethernet1/2", "virtual-wire", "delete network interface ethernet ethernet1/2"),
]
REFUSED = re.compile(r"(?i)invalid syntax|unknown command|server error|error:")


def hostname_for(row: dict) -> str:
    site = row.get("site_id", "")
    if not site:
        sys.exit(f"Firewalls row {row['_row']}: site_id is needed to build the hostname")
    return f"SITE{site.zfill(3) if site.isdigit() else site}"


def config_commands(row: dict, phash: dict[str, str]) -> list[str]:
    """Configure-mode commands for one firewall. phash maps admin -> password hash."""
    user = os.environ["SNMPV3_USER"]
    cmds = [
        f"set deviceconfig system hostname {hostname_for(row)}",
        "set deviceconfig system service disable-snmp no",
        f"set deviceconfig system snmp-setting access-setting version v3 views {SNMP_VIEW} view iso oid 1.3.6.1 option include mask 0xf0",
        f"set deviceconfig system snmp-setting access-setting version v3 users {user} view {SNMP_VIEW} "
        f"authpwd {os.environ['SNMPV3_AUTH_PASSWORD']} privpwd {os.environ['SNMPV3_PRIV_PASSWORD']} authproto SHA privproto AES",
    ]
    for admin in ADMINS:
        cmds += [f"set mgt-config users {admin} permissions role-based superuser yes",
                 f"set mgt-config users {admin} phash {phash.get(admin, '<hash computed on the firewall>')}"]
    return cmds


def mask(text: str) -> str:
    for key in SECRET_KEYS:
        value = os.environ.get(key)
        if value:
            text = text.replace(value, f"<{key}>")
    return re.sub(r"\$\d\$\S+", "<password-hash>", text)


class Shell:
    """Minimal interactive PAN-OS CLI session over SSH."""

    def __init__(self, host: str, user: str, password: str):
        import paramiko
        self.client = paramiko.SSHClient()
        self.client.set_missing_host_key_policy(paramiko.AutoAddPolicy())  # lab: firewall host keys not pre-loaded
        self.client.connect(host, username=user, password=password, look_for_keys=False, allow_agent=False, timeout=30,
                            banner_timeout=60, auth_timeout=60)
        self.chan = self.client.invoke_shell(width=300, height=1000)
        self.read(60)
        self.run("set cli pager off")
        self.run("set cli confirmation-prompt off")

    def read(self, timeout: float) -> str:
        buf, end = "", time.time() + timeout
        while time.time() < end:
            if self.chan.recv_ready():
                buf += self.chan.recv(65535).decode("utf-8", errors="replace")
                if PROMPT.search(buf):
                    return buf
            else:
                time.sleep(0.2)
        raise TimeoutError(f"no CLI prompt after {timeout}s; last output: {mask(buf[-300:])!r}")

    def run(self, cmd: str, timeout: float = 180) -> str:  # PA-410 management planes can be slow
        self.chan.send(cmd + "\n")
        return self.read(timeout)

    def close(self):
        self.client.close()


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("workbook", type=Path)
    ap.add_argument("--wave", help="dry run: only rows of this wave")
    ap.add_argument("--apply", nargs="+", metavar="FWn", help="connect to these firewalls (.env prefixes) and commit")
    args = ap.parse_args()
    load_env_file()
    missing = [k for k in list(ADMINS.values()) + ["SNMPV3_USER", "SNMPV3_AUTH_PASSWORD", "SNMPV3_PRIV_PASSWORD"]
               if not os.environ.get(k)]
    if missing:
        sys.exit(f"missing in .env: {', '.join(missing)}")
    rows = {r["serial_number"]: r for r in read_sheet(args.workbook, "Firewalls")}

    if not args.apply:
        for r in rows.values():
            if args.wave is None or r.get("wave") == args.wave:
                print(f"== {r['serial_number']} ({r.get('display_name')}, {r['folder']}):")
                for check, marker, delete in FACTORY_DEFAULTS:
                    print(f"    {delete:48} # only if '{check}' still shows {marker}")
                for c in config_commands(r, {}):
                    print("   ", mask(c))
                print("    commit")
        print("\nDry run only. --apply FW1 [FW2 ...] connects over SSH, checks the serial and commits.")
        return 0

    failures = 0
    for prefix in args.apply:
        host = os.environ.get(f"{prefix}_HOST")
        user = os.environ.get(f"{prefix}_SSH_USER") or os.environ.get("FW_SSH_USER")
        password = os.environ.get(f"{prefix}_SSH_PASSWORD") or os.environ.get("FW_SSH_PASSWORD")
        if not (host and user and password):
            print(f"SKIP    {prefix}: needs {prefix}_HOST and {prefix}_SSH_USER/_SSH_PASSWORD (or FW_SSH_*) in .env")
            failures += 1
            continue
        try:
            sh = Shell(host, user, password)
        except Exception as err:  # noqa: BLE001 - report and continue with the next firewall
            print(f"FAILED  {prefix} {host}: SSH login failed: {mask(str(err))}")
            failures += 1
            continue
        try:
            serial = (re.search(r"serial:\s*(\S+)", sh.run("show system info")) or [None, None])[1]
            row = rows.get(serial)
            if row is None:
                print(f"SKIP    {prefix} {host}: serial {serial} is not in the Firewalls sheet")
                failures += 1
                continue
            phash = {}
            for admin, key in ADMINS.items():
                out = sh.run(f"request password-hash password {os.environ[key]}")
                found = re.search(r"\$\d\$\S+", out)
                if not found:
                    raise RuntimeError(f"could not compute the password hash for {admin}")
                phash[admin] = found.group(0)
            sh.run("configure")
            for check, marker, delete in FACTORY_DEFAULTS:
                shown = sh.run(check).split("\n", 1)[-1]  # drop the echoed command
                if marker in shown:
                    out = sh.run(delete)
                    if REFUSED.search(out):
                        raise RuntimeError(f"command refused: {delete}\n{mask(out)[-400:]}")
                    print(f"        {prefix}: factory default removed: {delete}")
            for c in config_commands(row, phash):
                out = sh.run(c)
                if REFUSED.search(out):
                    raise RuntimeError(f"command refused: {mask(c)}\n{mask(out)[-400:]}")
            out = sh.run("commit", timeout=900)
            ok = "Configuration committed successfully" in out
            print(f"{'DONE   ' if ok else 'FAILED '} {prefix} {host} serial {serial} -> {hostname_for(row)}: "
                  f"{'committed' if ok else 'commit failed'}")
            if not ok:
                print(mask(out)[-1500:])
                failures += 1
            sh.run("exit")
        except Exception as err:  # noqa: BLE001
            print(f"FAILED  {prefix} {host}: {mask(str(err))}")
            failures += 1
        finally:
            sh.close()
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
