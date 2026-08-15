/* Service worker: open the side panel, snapshot the active tab, talk to Hermes. */

const DEFAULT_BACKEND = "http://127.0.0.1:9120";
const POLL_MS = 1500;
const POLL_MAX_MS = 10 * 60 * 1000;

chrome.runtime.onInstalled.addListener(function () {
  chrome.sidePanel.setPanelBehavior({ openPanelOnActionClick: true }).catch(function () {});
});

chrome.runtime.onStartup.addListener(function () {
  chrome.sidePanel.setPanelBehavior({ openPanelOnActionClick: true }).catch(function () {});
});

chrome.action.onClicked.addListener(function (tab) {
  if (tab && tab.windowId != null) {
    chrome.sidePanel.open({ windowId: tab.windowId }).catch(function () {});
  }
});

function sendToPanel(payload) {
  chrome.runtime.sendMessage(payload).catch(function () {});
}

function storageGet(keys) {
  return new Promise(function (resolve) {
    chrome.storage.local.get(keys, function (local) {
      chrome.storage.sync.get(keys, function (sync) {
        resolve(Object.assign({}, sync, local));
      });
    });
  });
}

function backendOrigin(url) {
  try {
    return new URL(url || DEFAULT_BACKEND).origin;
  } catch (e) {
    return DEFAULT_BACKEND;
  }
}

function restrictedUrl(url) {
  if (!url) return true;
  return /^(chrome|chrome-extension|edge|about|devtools|view-source):/i.test(url);
}

async function snapshotActiveTab() {
  var tabs = await chrome.tabs.query({ active: true, currentWindow: true });
  var tab = tabs && tabs[0];
  if (!tab || tab.id == null) {
    throw new Error("No active tab.");
  }
  if (restrictedUrl(tab.url)) {
    throw new Error("Cannot read this page (browser-internal URL). Switch to a normal http/https tab.");
  }
  var results;
  try {
    results = await chrome.scripting.executeScript({
      target: { tabId: tab.id },
      files: ["src/snapshot.js"]
    });
  } catch (err) {
    throw new Error("Could not snapshot this tab: " + (err && err.message ? err.message : String(err)));
  }
  var shot = results && results[0] && results[0].result;
  if (!shot || typeof shot !== "object") {
    throw new Error("Snapshotter returned nothing.");
  }
  if (!shot.url) shot.url = tab.url || "";
  if (!shot.title) shot.title = tab.title || "";
  return { tab: tab, snapshot: shot };
}

function authHeaders(cookie) {
  var headers = { "Content-Type": "application/json" };
  if (cookie) headers.Cookie = cookie;
  headers["X-Company-Page-Chat"] = "1";
  return headers;
}

async function postPageChat(backend, cookie, body) {
  var res = await fetch(backend.replace(/\/$/, "") + "/api/page-chat", {
    method: "POST",
    headers: authHeaders(cookie),
    body: JSON.stringify(body)
  });
  var data = {};
  try { data = await res.json(); } catch (e) { data = {}; }
  if (res.status === 401) {
    throw new Error("Not logged in (401). Use Login in the panel.");
  }
  if (!res.ok) {
    throw new Error(data.detail || data.error || ("page-chat failed (" + res.status + ")"));
  }
  if (!data.job_id) {
    throw new Error("Backend did not return a job id.");
  }
  return data.job_id;
}

async function pollJob(backend, cookie, jobId) {
  var started = Date.now();
  while (Date.now() - started < POLL_MAX_MS) {
    var res = await fetch(
      backend.replace(/\/$/, "") + "/api/page-chat/jobs/" + encodeURIComponent(jobId),
      { method: "GET", headers: authHeaders(cookie) }
    );
    var data = {};
    try { data = await res.json(); } catch (e) { data = {}; }
    if (res.status === 401) {
      throw new Error("Session expired (401). Log in again.");
    }
    if (!res.ok) {
      throw new Error(data.detail || data.error || ("job poll failed (" + res.status + ")"));
    }
    sendToPanel({
      type: "ask-progress",
      jobId: jobId,
      status: data.status,
      partial: data.partial || data.answer || ""
    });
    if (data.status === "done") {
      return data.answer || data.result || data.partial || "";
    }
    if (data.status === "error") {
      throw new Error(data.error || "page-chat job failed");
    }
    await new Promise(function (r) { setTimeout(r, POLL_MS); });
  }
  throw new Error("Timed out waiting for the agent.");
}

async function handleAsk(message) {
  var stored = await storageGet(["backendUrl", "profile", "sessionCookie"]);
  var backend = backendOrigin(message.backendUrl || stored.backendUrl || DEFAULT_BACKEND);
  var profile = (message.profile || stored.profile || "").trim();
  var question = (message.question || "").trim();
  var cookie = stored.sessionCookie || "";
  if (!question) throw new Error("Ask a question first.");
  if (!profile) throw new Error("Set a Hermes profile.");
  if (!cookie) throw new Error("Log in first.");

  sendToPanel({ type: "ask-progress", status: "snapshot", partial: "" });
  var packed = await snapshotActiveTab();
  var snapshot = packed.snapshot;
  sendToPanel({
    type: "ask-progress",
    status: "queued",
    url: snapshot.url,
    title: snapshot.title,
    partial: ""
  });

  var jobId = await postPageChat(backend, cookie, {
    url: snapshot.url,
    title: snapshot.title,
    snapshot: snapshot,
    question: question,
    profile: profile
  });
  sendToPanel({ type: "ask-progress", status: "running", jobId: jobId, partial: "" });
  var answer = await pollJob(backend, cookie, jobId);
  return { answer: answer, url: snapshot.url, title: snapshot.title, jobId: jobId };
}

chrome.runtime.onMessage.addListener(function (message, _sender, sendResponse) {
  if (!message || !message.type) return;
  if (message.type === "ask") {
    handleAsk(message)
      .then(function (result) {
        sendResponse({ ok: true, result: result });
      })
      .catch(function (err) {
        sendResponse({ ok: false, error: err && err.message ? err.message : String(err) });
      });
    return true;
  }
});
