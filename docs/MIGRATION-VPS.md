# VPS cutover runbook (generic)
#
# Ordered path: prep → bootstrap → restore → auth re-setup → first-run
# checks → DNS/ports → decommission the old host. Secrets never go through git.
#
# Companion files:
#   infra/vps/bootstrap-vps.sh
#   infra/vps/compose.yaml
#   infra/vps/.env.EXAMPLE
#   scripts/migrate-from-pi.sh

## 0. What moves, what does not

| Item | How |
|---|---|
| Hermes profiles (minus secrets) | `migrate-from-pi.sh` rsync |
| `state.db*`, `cron/`, `gateway-starts.log`, yaml sidecar | rsync |
| `/opt/company-agent/` and `webui/runtime/` (if present) | rsync |
| company auth plugin + `web_dist` | clone/rsync fallback |
| `hermes-desktop-web.service`, `hermes-serve.service` | rsync; dashboard unit is retired |
| `<GITHUB_ORG>/hermes-agent-platform` → `~/.hermes/hermes-agent` | clone preferred |
| `dashboard-users.json` | OUT OF BAND, mode 0600 |
| `notion-pat.env` | OUT OF BAND, mode 0600 |
| `dashboard.company_auth.secret` / `HERMES_DASHBOARD_COMPANY_AUTH_SECRET` | OUT OF BAND |
| per-profile `.env` / `auth.json` | OUT OF BAND, mode 0600 |
| host `~/.hermes/.env`, repo `.env`, `infra/.env` | OUT OF BAND, then rotate |

Not in the migrate script (handle separately or accept loss):

- model-provider OAuth tokens — re-auth on the VPS (do not treat a copied token as durable)
- GitHub App PEMs and install tokens
- `~/.hermes/mcp-tokens/`
- messaging bot tokens (in host `.env`)
- outbound-mail / CRM secrets
- host-local proxy units that should not follow the company VPS
- local wiki, user-local skills, session transcripts
- live DNS pointing at the old host until first-run checks pass

## 1. Prep (before touching the VPS)

1. Two admins on the cloud account. Encrypted disk. Allowlisted SSH (or VPN).
2. VPS size: 4 vCPU / 16 GB RAM minimum (INSTALL.md). No GPU.
3. Create login `<VPS_USER>`. Add that user's SSH public key.
4. Mint deploy keys or a machine identity that can clone:
   - `<GITHUB_ORG>/<COMPANY_PLATFORM_REPO>` (private)
   - `<GITHUB_ORG>/company-agent-template` (public or private)
   - `<GITHUB_ORG>/hermes-agent-platform` (private runtime fork)
5. From a trusted laptop, snapshot the OOB secrets to an encrypted store (not chat, not git):
   - `~/.hermes/dashboard-users.json`
   - `~/.hermes/notion-pat.env`
   - `dashboard.company_auth.secret` (config.yaml) and/or `HERMES_DASHBOARD_COMPANY_AUTH_SECRET`
   - each profile `.env` and `auth.json` you still need
6. Review D050 before mapping legacy profiles onto `employee-*` / `automation`.
7. Freeze non-essential writes on the old host.

## 2. Bootstrap

On the VPS as root, after replacing placeholders:

```bash
VPS_USER=<VPS_USER> DOMAIN=<DOMAIN> \
  PLATFORM_REPO=git@github.com:<GITHUB_ORG>/<COMPANY_PLATFORM_REPO>.git \
  TEMPLATE_REPO=git@github.com:<GITHUB_ORG>/company-agent-template.git \
  RUNTIME_REPO=git@github.com:<GITHUB_ORG>/hermes-agent-platform.git \
  sudo -E bash /opt/company-agent/infra/vps/bootstrap-vps.sh
```

If the platform repo is not on disk yet:

```bash
sudo mkdir -p /opt/company-agent
sudo git clone git@github.com:<GITHUB_ORG>/<COMPANY_PLATFORM_REPO>.git /opt/company-agent
sudo chown -R <VPS_USER>:<VPS_USER> /opt/company-agent
VPS_USER=<VPS_USER> DOMAIN=<DOMAIN> \
  sudo -E bash /opt/company-agent/infra/vps/bootstrap-vps.sh
```

Bootstrap is idempotent. It:

- `apt-get update` and installs git, python3.12, uv, rsync, Docker + Compose plugin
- does **not** install host apt PostgreSQL — pgvector is Docker-based
- clones the three repos (skips any URL that still contains a `<placeholder>`)
- creates a venv and editable-installs the runtime fork into `~/.hermes/hermes-agent`
- writes `hermes-serve` + `hermes-desktop-web` user units and enables linger
- copies `infra/vps/.env.EXAMPLE` → `infra/vps/.env` (0600) if missing
- runs `migrate-from-pi.sh --apply` only when `PI_HOST` is set

Optional: `PI_HOST=<pi-ip> PI_REMOTE_USER=<remote-user>` on the same command.

## 3. Restore

From `<VPS_USER>` on the VPS:

```bash
HERMES_HOME=/home/<service-user>/.hermes \
  bash /opt/company-agent/scripts/migrate-from-pi.sh --dry-run <pi-host> <remote-user>
# review the file list, then
HERMES_HOME=/home/<service-user>/.hermes \
  bash /opt/company-agent/scripts/migrate-from-pi.sh --apply <pi-host> <remote-user>
```

Then OUT OF BAND (laptop → VPS, or VPS `scp` from the old host):

```bash
scp <remote-user>@<pi-host>:<hermes-home>/dashboard-users.json \
    ~/.hermes/dashboard-users.json
scp <remote-user>@<pi-host>:<hermes-home>/notion-pat.env \
    ~/.hermes/notion-pat.env
chmod 0600 ~/.hermes/dashboard-users.json ~/.hermes/notion-pat.env

for p in default employee-a employee-b employee-c automation; do
  scp <remote-user>@<pi-host>:<hermes-home>/profiles/$p/.env \
      ~/.hermes/profiles/$p/.env 2>/dev/null || true
  scp <remote-user>@<pi-host>:<hermes-home>/profiles/$p/auth.json \
      ~/.hermes/profiles/$p/auth.json 2>/dev/null || true
  chmod 0600 ~/.hermes/profiles/$p/.env ~/.hermes/profiles/$p/auth.json 2>/dev/null || true
done
```

Merge `dashboard.company_auth.*` from `~/.hermes/config.yaml.from-pi` into the live `config.yaml`. Set:

```text
dashboard.company_auth.users_file: /home/<VPS_USER>/.hermes/dashboard-users.json
dashboard.company_auth.secret:     <same value as the old host, then rotate>
```

Rewrite unit `ExecStart` / `HOME` / `EnvironmentFile` if bootstrap did not already generate them for `<VPS_USER>`.

```bash
systemctl --user daemon-reload
systemctl --user disable --now hermes-dashboard.service 2>/dev/null || true
systemctl --user enable --now hermes-serve.service hermes-desktop-web.service
```

## 4. Auth re-setup

### Model provider

Do not treat a copied OAuth token as the long-term credential.

```bash
hermes setup
hermes config get model.provider
```

### Notion

1. Put the PAT in `~/.hermes/notion-pat.env` (`NOTION_API_TOKEN=...`, mode 0600).
2. Copy the same token into `/opt/company-agent/infra/vps/.env` as `NOTION_API_TOKEN`.
3. Confirm the integration is shared with the workspace pages the agent needs.
4. See `docs/notion-setup.md`. Prefer PAT over headless OAuth on a VPS.

### Dashboard secret

Keep the old secret for the first start so existing cookies still verify, then rotate:

```bash
hermes config set dashboard.company_auth.secret "$(openssl rand -hex 32)"
# update HERMES_DASHBOARD_COMPANY_AUTH_SECRET in ~/.hermes/.env and infra/vps/.env
systemctl --user restart hermes-serve
```

Everyone signs in again after rotation.

## 5. Knowledge stack + embeddings

Default embedding (Phase 2 VPS):

| Variable | Default |
|---|---|
| `EMBEDDING_PROVIDER` | `openai` |
| `EMBEDDING_MODEL` | `text-embedding-3-small` |
| `EMBEDDING_DIMENSIONS` | `1536` |

This matches `services/migrations/0006_chunks_embeddings.sql` (`vector(1536)`). Fill `EMBEDDING_API_KEY`. Alternatives are commented in `infra/vps/.env.EXAMPLE`. Changing width later requires a parallel table (D056).

```bash
cp /opt/company-agent/infra/vps/.env.EXAMPLE /opt/company-agent/infra/vps/.env
chmod 600 /opt/company-agent/infra/vps/.env
# edit placeholders: postgres creds, embedding key, Notion token, auth secret
cd /opt/company-agent/infra/vps
docker compose --env-file .env up -d
docker compose ps
curl -fsS http://127.0.0.1:8081/health
curl -fsS http://127.0.0.1:8082/health
curl -fsS http://127.0.0.1:8083/health
```

Migrations in `services/migrations/` run on first Postgres init only. They are still a scaffold — knowledge-api will report `embeddings_configured` / `database_configured` honestly.

## 6. First-run checks

- [ ] `systemctl --user is-active hermes-serve hermes-desktop-web` is `active`
- [ ] `curl -fsS http://127.0.0.1:9120/health` (or `/api/health`) succeeds
- [ ] browser UI on `http://127.0.0.1:9121` shows company login (not basic-auth)
- [ ] a known user from `dashboard-users.json` can sign in
- [ ] `hermes -p automation config get` points at that profile
- [ ] `cd /opt/company-agent/services && python3 -m pytest tests/ -q` is green
- [ ] `docker compose -f infra/vps/compose.yaml ps` is healthy
- [ ] `git grep` / committed files contain no live tokens
- [ ] knowledge-api `/health` returns `database_configured` / `embeddings_configured` as expected
- [ ] messaging / outbound mail still pointed at the old host until you explicitly cut over those tokens

## 7. DNS and ports

Bootstrap units bind **localhost only**. Publish via Caddy or nginx on `<DOMAIN>`:

| Public | Upstream |
|---|---|
| `https://<DOMAIN>/` | `127.0.0.1:9121` (desktop-web) |
| `https://<DOMAIN>/api/` | `127.0.0.1:9120` (hermes serve) — desktop-web already proxies `/api` `/auth` `/login` `/logout` |
| do not publish | `5432`, `8081`, `8082`, `8083` |

Open 22 (allowlisted), 80, 443. Do not open 9120/9121 on the public interface unless you accept that risk.

Point DNS A/AAAA at the VPS only after section 6 is green. Keep the old host serving until you have watched one successful login + one agent turn on the VPS.

## 8. Decommission the old host

1. Flip DNS. Watch logs for 24 hours.
2. Stop old-host units: `systemctl --user disable --now hermes-serve hermes-desktop-web hermes-dashboard`.
3. Rotate every secret the old host still holds.
4. Leave the old host powered but isolated for a week as rollback hardware.
5. Then wipe credentials on the old host (`chmod 000` or delete the files listed in section 0).

## Rollback

Keep the old host unchanged until DNS flips.

| Failure | Action |
|---|---|
| VPS Hermes will not start | `systemctl --user status hermes-serve`; confirm `hermes` on PATH and runtime venv; fall back to the old host |
| Company login broken | restore `dashboard-users.json` + original `dashboard.company_auth.secret`; do not rotate until login works |
| Compose / Postgres unhealthy | `docker compose logs postgres`; the volume is empty on first boot — wipe only if you accept losing VPS-only data (`docker compose down -v`) |
| DNS already flipped | lower TTL beforehand; point A/AAAA back at the old host; re-enable its units |
| Runtime clone failed | rsync fallback in `migrate-from-pi.sh`; or copy `~/.hermes/hermes-agent` excluding `.venv` and `node_modules`, then recreate the venv |

Do not `rsync --delete` the old Hermes home onto a VPS that already has a working config.

## Embedding default (D040 working choice)

Until governance closes D040 formally, the VPS stack uses:

```text
EMBEDDING_PROVIDER=openai
EMBEDDING_MODEL=text-embedding-3-small
EMBEDDING_DIMENSIONS=1536
```

Reason: hosted, cheap, widely supported, width already baked into `0006_chunks_embeddings.sql`. Swap only with a parallel embedding table.
