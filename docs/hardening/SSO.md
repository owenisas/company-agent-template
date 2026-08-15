# SSO / authenticated reverse proxy

Phase 5 §4509. Identity product still open (**D035**). This is the
design scaffold for the VPS. Do not expose `hermes serve` or
`desktop-web` on a public interface without this layer.

## What is being fronted

From `INSTALL.md` (appliance / planned VPS units):

| Unit | Bind today | Role |
|---|---|---|
| `hermes-serve.service` | `127.0.0.1:9120` (VPS MUST stay loopback) | Headless backend |
| `hermes-desktop-web.service` | `127.0.0.1:9121` | Browser UI |

Knowledge API / MCP / approval-api in `infra/vps/compose.yaml` already
bind `127.0.0.1` only. They stay off the public internet. SSO fronts
**human HTTPS**, not the database.

## Recommended stack

Pick one. Do not run both.

| Option | Reverse proxy | IdP | When |
|---|---|---|---|
| **A (recommended start)** | Caddy | Authentik (OIDC) | Small team, automatic HTTPS, one extra compose project |
| B | Traefik | Company IdP via OIDC (Authentik, Google Workspace, or Microsoft Entra) | Already standardized on Traefik |

Caddy (or Traefik) terminates TLS on `:443`, requires an OIDC login,
then reverse-proxies to `127.0.0.1:9121` (UI) and optionally a
narrow path to `127.0.0.1:9120` if the UI needs the backend on the
same host. The backend MUST NOT be reachable without the proxy
session.

## Domain placeholders

| Placeholder | Meaning |
|---|---|
| `<VPS_DOMAIN>` | Public hostname, e.g. `agent.<company-domain>` |
| `<OIDC_ISSUER>` | Authentik/Entra/Google issuer URL |
| `<OIDC_CLIENT_ID>` | Confidential client for the proxy |
| `<OIDC_CLIENT_SECRET_REF>` | Secret-manager reference (see `SECRET-MANAGER.md`) |

Do not commit real hostnames that are not already in git. D019
(company email domain) and D035 remain open.

## Auth-provider wiring

```text
Browser
  -> Caddy/Traefik :443  (TLS)
    -> OIDC authorization code + PKCE
      -> company IdP (Authentik / Workspace / Entra)
        MFA enforced at the IdP
    -> identity headers to desktop-web
      X-Forwarded-User: <idp-subject>
      X-Forwarded-Email: <company-email>
    -> desktop-web (9121) + serve (9120) on loopback
```

Hermes dashboard auth today is the `company` DashboardAuthProvider
with `~/.hermes/dashboard-users.json`. Phase 5 plan:

1. Keep the file as a **break-glass local** store (0600).
2. Prefer IdP subject → `employee-a` / `employee-b` / `employee-c`
   mapping once D004 emails exist.
3. Do not put IdP client secrets in `config.yaml`. Use the secret
   manager.
4. Service-to-service (knowledge MCP, approval-api) stays
   token/mTLS on loopback or the private network — not browser SSO.

## MFA

- MFA is mandatory on the IdP for every human who can reach
  `<VPS_DOMAIN>`.
- Recovery codes held by two platform admins (D008 / D015), not in
  git.
- Disable password-only IdP apps.

## Network rules

- UFW / security group: 22 (admin allowlist), 443 (public or VPN).
- No public 5432, 8081–8083, 9120, 9121.
- Prefer VPN or identity-aware tunnel in addition to SSO when the
  VPS has a public IP (spec 6.2).

## Out of scope until D035 closes

- Concrete Caddyfile / Traefik dynamic config
- Authentik blueprint
- Mapping of IdP groups to `agent-platform-admins` / `agent-builders`
