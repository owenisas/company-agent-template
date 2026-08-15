# WebUI

Login-protected profile chat for the Hermes host. Employees sign in,
pick a profile they are allowed to use, send a message, and poll the
result. Admins also see per-profile token usage.

The UI is company-neutral. Real usernames, passwords, and profile slugs
come from **runtime config**, not from this tree.

## Layout

```text
webui/
  backend/           FastAPI app
    app.py           HTTP routes
    auth.py          signed session cookie
    scope.py         admin vs own-profile (no automation)
    users.py         pbkdf2 passwords
    profiles.py      `hermes profile list`
    jobs.py          background `hermes -p … -z …`
    usage.py         read-only ~/.hermes/state.db
    passwd.py        hash helper
  frontend/          vanilla HTML/CSS/JS, no build, no CDN
  runtime/           gitignored host state
    USERS.example.json
    webui.env.EXAMPLE
  run.sh
  install-webui-service.sh
```

## Configure users

1. Copy `runtime/USERS.example.json` to `runtime/users.json` (mode 0600).
2. Hash passwords (never store plaintext):

```bash
cd webui
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/python -m backend.passwd '<admin>' \
  --role admin --profile default --password '…' --write
.venv/bin/python -m backend.passwd '<employee-a>' \
  --role viewer --profile employee-a --password '…' --write
```

`users.json` shape:

```json
{
  "users": [
    {
      "username": "<admin>",
      "role": "admin",
      "profile": "default",
      "algo": "pbkdf2_sha256",
      "iterations": 210000,
      "salt": "<hex>",
      "password_hash": "<hex>"
    }
  ]
}
```

- `role`: `admin` sees every host profile, including `automation`.
  Any other role sees only `profile` and never automation.
- `profile`: the employee's own Hermes profile name on this host.
- `WEBUI_ADMINS` (comma-separated usernames) also grants admin.

Do not commit `runtime/users.json`.

## Configure the process

```bash
cp runtime/webui.env.EXAMPLE runtime/webui.env
chmod 600 runtime/webui.env
# set SECRET_KEY to a long random string
# or let install-webui-service.sh write runtime/secret
```

| Env | Default | Purpose |
|---|---|---|
| `SECRET_KEY` | required | signs the session cookie |
| `WEBUI_ADMINS` | (empty) | extra admin usernames |
| `WEBUI_PORT` | `8080` | listen port |
| `WEBUI_BIND` | `0.0.0.0` | listen address |
| `HERMES_BIN` | `hermes` | agent binary |
| `HERMES_PROVIDER` | `xai-oauth` | `--provider` for chat jobs |
| `HERMES_MODEL` | `grok-4.6` | `-m` for chat jobs |
| `HERMES_REASONING_EFFORT` | `extra-high` | `--reasoning` |

## Run

```bash
./run.sh
```

Systemd user unit:

```bash
./install-webui-service.sh
systemctl --user start hermes-webui.service
```

Bind is `0.0.0.0` so a reverse proxy or private network can reach it.
Put a TLS terminator in front before exposing it beyond the host.

## API

| Method | Path | Notes |
|---|---|---|
| POST | `/api/login` | JSON `{username,password}` or form; sets cookie |
| POST | `/api/logout` | clears cookie |
| GET | `/api/whoami` | current user |
| GET | `/api/profiles` | scoped `hermes profile list` |
| POST | `/api/chat` | `{profile,message}` → `{job_id}` |
| GET | `/api/jobs/{id}` | `{status,partial,result,started_at,elapsed}` |
| GET | `/api/usage` | scoped token totals |

Every profile-named route calls `scope.can_access`. The client cannot
widen that set.

## First owner

Create the first admin with `python -m backend.passwd … --write` and
record that username in `governance/user-role-group-registry.md`. Rotate
the password after first login. This template does not ship a working
default password.
