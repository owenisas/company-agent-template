# Notion public connection setup

A company principal creates one **Notion public connection**. Hermes
stores the OAuth grant on the server (`~/.hermes/notion-tokens.json`,
mode 0600). The browser never receives an access token or refresh
token. The same connect serves:

- human ↔ agent collaboration (webui + `notion_collab` tools)
- future knowledge import (same `packages.notion` client)

## 1. Create the public connection

1. Sign in to Notion as a workspace owner or admin.
2. Open the [Developer portal](https://www.notion.so/my-integrations)
   → **Build** → **Public connections** → **Create new connection**.
3. Name it (for example `<Company> Hermes`).
4. Choose a development workspace.
5. Installation scope: **Selected workspaces only** unless you
   intend a Marketplace listing. This choice is immutable.
6. Capabilities — enable at least:
   - Read content
   - Insert content
   - Update content
   - Comments (Read comments + Insert comments) if agents will
     mention discussion threads
7. User capabilities: **User information without emails** is enough.
8. Redirect URI — must match the running webui exactly, for example:
   - local: `http://127.0.0.1:8080/auth/notion/callback`
   - deployed: `https://<webui-host>/auth/notion/callback`
9. Save. On the **Configuration** tab copy:
   - OAuth client ID
   - OAuth client secret

Do not commit either value. Do not put them in frontend JS.

## 2. Fill env / config

Copy placeholders into a 0600 env file the webui and services load
(webui `runtime/webui.env`, services `.env`, or process environment):

```
NOTION_CLIENT_ID=<from Configuration>
NOTION_CLIENT_SECRET=<from Configuration>
NOTION_REDIRECT_URI=http://127.0.0.1:8080/auth/notion/callback
# optional override; default is ~/.hermes/notion-tokens.json
# NOTION_TOKEN_PATH=~/.hermes/notion-tokens.json
```

`dashboard.notion` / services config keys are the same three names.
Restart the webui after editing.

## 3. First-connect test

1. Sign in to the platform webui.
2. Open **Notion**.
3. Click **Connect Notion**. Notion shows capabilities and a page
   picker — share the parent pages the agent should see.
4. After Allow, the browser returns to
   `/auth/notion/callback?code=…&state=…`. The server exchanges the
   code (`POST /v1/oauth/token` with HTTP Basic) and stores the grant.
5. Status should show the workspace name. Disconnect clears the
   stored tokens; revoke the connection in Notion
   **Settings → Connections** as well if you want the grant dead.

If the callback lands on this host but the webui is elsewhere, the
redirect URI is wrong. If status stays `oauth_app_not_configured`,
the env keys did not load.

## 4. Agent tools

After connect, tools under `packages.connectors.notion_collab`:

| Tool | Risk | Gate |
|---|---|---|
| `notion.read_page` | R0 | allowlisted fields |
| `notion.search` | R0 | allowlisted fields |
| `notion.query_database` | R0 | allowlisted fields |
| `notion.create_page` | R2 | preview + approval |
| `notion.append_blocks` | R2 | preview + approval |
| `notion.update_page_property` | R2 | preview + approval |

Reads return `not_configured` when no token is stored. Writes never
skip preview/approval.

## 5. Dashboard API (same server)

The Hermes dashboard can call these routes with the webui session
cookie. None of them return token values.

| Method | Path | Purpose |
|---|---|---|
| GET | `/api/notion/status` | connected workspace name / not connected |
| GET | `/api/notion/connect` | 302 to Notion authorize URL |
| GET | `/auth/notion/callback` | code → token store |
| POST | `/api/notion/disconnect` | clear stored grant |
| DELETE | `/api/notion` | same as disconnect |

## 6. What this is not

- Not Notion MCP OAuth (different token product, different store).
- Not an internal connection static `ntn_` install token.
- Not a private-page iframe. Private content is API-read, never
  framed.
