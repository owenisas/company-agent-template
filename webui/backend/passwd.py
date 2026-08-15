"""Mint or update a password hash in runtime/users.json.

    python3 -m backend.passwd '<admin>' --role admin --profile default
    python3 -m backend.passwd '<employee-a>' --role viewer --profile employee-a --write
"""

from __future__ import annotations

import argparse
import getpass
import json
import sys

from .config import USERS_PATH
from .users import hash_password, load_users


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Hash a webui password.")
    parser.add_argument("username")
    parser.add_argument("--role", default="viewer")
    parser.add_argument("--profile", default="")
    parser.add_argument("--password", default="")
    parser.add_argument(
        "--write",
        action="store_true",
        help="merge into runtime/users.json (creates the file if missing)",
    )
    args = parser.parse_args(argv)
    password = args.password or getpass.getpass("password: ")
    if not password:
        print("empty password", file=sys.stderr)
        return 2
    record = {
        "username": args.username,
        "role": args.role,
        "profile": args.profile,
        **hash_password(password),
    }
    if not args.write:
        print(json.dumps(record, indent=2))
        return 0
    users = load_users()
    users = [u for u in users if u.get("username") != args.username]
    users.append(record)
    USERS_PATH.parent.mkdir(parents=True, exist_ok=True)
    USERS_PATH.write_text(
        json.dumps({"users": users}, indent=2) + "\n",
        encoding="utf-8",
    )
    USERS_PATH.chmod(0o600)
    print(f"wrote {USERS_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
