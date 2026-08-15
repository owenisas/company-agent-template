# Company Page Chat (Chrome, Manifest V3)

Company-internal side panel: snapshot the current tab and ask the Hermes
agent about it. v1 is **read-only Q&A**. The extension never
holds an LLM API key.

## Install

1. Chrome → `chrome://extensions`
2. Enable **Developer mode**
3. **Load unpacked** → this directory:

   `extensions/chrome-page-chat`

4. Pin the toolbar icon. Clicking it opens the side panel (Chrome 116+).

Linux smoke load (separate profile):

```
google-chrome --user-data-dir=/tmp/page-chat-profile \
  --load-extension=/path/to/company-agent-template/extensions/chrome-page-chat
```

## Configure

In the panel:

- **Backend URL** — default `http://127.0.0.1:9120` (`hermes serve`)
- **Hermes profile** — a real profile on the host, e.g. `company-user-a`
- **Login** — company username/password. The panel POSTs
  `{provider:"company",username,password}` to `{BACKEND}/auth/password-login`
  and stores the returned session cookie in `chrome.storage.local`.

Backend URL + profile are synced (`chrome.storage.sync`). The session
cookie is local only.

## Usage

1. Open a normal `http`/`https` tab (not `chrome://`).
2. Open the side panel and log in.
3. Type a question → **Ask about this page**.
4. The service worker injects `src/snapshot.js` into the active tab,
   POSTs `{url,title,snapshot,question,profile}` to `/api/page-chat`,
   and polls `/api/page-chat/jobs/{id}` until the answer is ready.

`chrome://` and other internal pages cannot be injected; the panel will
say so instead of crashing.

## Permissions

| Permission | Why |
|---|---|
| `sidePanel` | Persistent chat UI |
| `storage` | Backend URL, profile, session cookie |
| `scripting` + `activeTab` | Snapshot the tab you asked about |
| host `http://127.0.0.1:9120/*` | Talk to the local Hermes backend |
| host `http://*/*` | Snapshot any **http** site the user has open. Needed because programmatic `executeScript` on a non-gesture path (and some SPA navigations) requires a matching host permission. **https** tabs still work via `activeTab` after you click Ask. This is intentionally not `<all_urls>` / `https://*/*`. |

No `debugger`, no `<all_urls>`, no static always-on content scripts.

## Security

- The snapshot (visible text, headings, links, controls, forms) goes **only**
  to the configured backend. It is not sent to a vendor LLM from the browser.
- Password / secret-looking field values are stripped in the snapshotter.
- The dashboard session cookie is stored locally in the extension, not in
  page JS. Do not paste it into chats or Discord.
- Page text is treated as **untrusted data** by `/api/page-chat` (delimited
  block; the agent is told not to follow instructions found inside).
- Login uses the existing company password provider. No model key in the package.

## v1 / v2 boundary

**v1 (this build):** read-only Q&A about the current tab.

**v2 (not built):** clicking, filling, scrolling, navigating, screenshots via
`chrome.debugger`, multi-tab compare, Auto-approve actions.

If the model *suggests* a selector, ignore it in v1 — the extension will not
act on the page.
