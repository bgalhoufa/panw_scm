"""Verify SCM service-account credentials and list configuration folders.

Reads SCM_CLIENT_ID / SCM_CLIENT_SECRET / SCM_SCOPE from the environment,
falling back to the repo-root .env file. Read-only: makes no changes in SCM.
"""
import base64
import json
import os
import sys
import urllib.parse
import urllib.request
from pathlib import Path

AUTH_URL = os.environ.get(
    "SCM_AUTH_URL", "https://auth.apps.paloaltonetworks.com/auth/v1/oauth2/access_token"
)
HOST = os.environ.get("SCM_HOST", "api.sase.paloaltonetworks.com")


def load_env_file() -> None:
    env_file = Path(__file__).resolve().parent.parent / ".env"
    if not env_file.exists():
        return
    for line in env_file.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip())


def get_token(client_id: str, client_secret: str, scope: str) -> str:
    basic = base64.b64encode(f"{client_id}:{client_secret}".encode()).decode()
    body = urllib.parse.urlencode({"grant_type": "client_credentials", "scope": scope}).encode()
    req = urllib.request.Request(
        AUTH_URL,
        data=body,
        headers={
            "Authorization": f"Basic {basic}",
            "Content-Type": "application/x-www-form-urlencoded",
        },
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.load(resp)["access_token"]


def list_folders(token: str) -> list[dict]:
    req = urllib.request.Request(
        f"https://{HOST}/config/setup/v1/folders",
        headers={"Authorization": f"Bearer {token}"},
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.load(resp).get("data", [])


def main() -> int:
    load_env_file()
    try:
        creds = [os.environ[k] for k in ("SCM_CLIENT_ID", "SCM_CLIENT_SECRET", "SCM_SCOPE")]
    except KeyError as missing:
        print(f"Missing environment variable: {missing}", file=sys.stderr)
        return 1

    try:
        token = get_token(*creds)
        print("Authentication OK")
        folders = list_folders(token)
    except urllib.error.HTTPError as err:
        print(f"HTTP {err.code} from {err.url}: {err.read().decode(errors='replace')}", file=sys.stderr)
        return 1

    print(f"{len(folders)} folder(s):")
    for f in folders:
        print(f"  - {f.get('name')}  (parent: {f.get('parent') or '-'})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
