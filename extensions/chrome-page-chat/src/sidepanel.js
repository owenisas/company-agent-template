/* Side panel: config, company login, ask-about-this-page. */

const DEFAULT_BACKEND = "http://127.0.0.1:9120";

const els = {
  backendUrl: document.getElementById("backendUrl"),
  profile: document.getElementById("profile"),
  username: document.getElementById("username"),
  password: document.getElementById("password"),
  loginBtn: document.getElementById("loginBtn"),
  logoutBtn: document.getElementById("logoutBtn"),
  authStatus: document.getElementById("authStatus"),
  question: document.getElementById("question"),
  askBtn: document.getElementById("askBtn"),
  askStatus: document.getElementById("askStatus"),
  answer: document.getElementById("answer"),
  answerBody: document.getElementById("answerBody"),
  pageMeta: document.getElementById("pageMeta")
};

function setStatus(node, text, kind) {
  node.textContent = text || "";
  node.classList.remove("is-bad", "is-ok");
  if (kind) node.classList.add(kind === "bad" ? "is-bad" : "is-ok");
}

function escapeHtml(s) {
  return String(s)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

function renderMarkdown(text) {
  var safe = escapeHtml(text || "");
  safe = safe.replace(/`([^`]+)`/g, "<code>$1</code>");
  safe = safe.replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>");
  safe = safe.replace(/^### (.+)$/gm, "<strong>$1</strong>");
  safe = safe.replace(/^## (.+)$/gm, "<strong>$1</strong>");
  safe = safe.replace(/^# (.+)$/gm, "<strong>$1</strong>");
  return safe;
}

function originOf(url) {
  try {
    return new URL(url || DEFAULT_BACKEND).origin;
  } catch (e) {
    return DEFAULT_BACKEND;
  }
}

function loadSettings() {
  chrome.storage.sync.get(["backendUrl", "profile"], function (sync) {
    chrome.storage.local.get(["sessionCookie", "loggedInUser"], function (local) {
      els.backendUrl.value = sync.backendUrl || DEFAULT_BACKEND;
      els.profile.value = sync.profile || "company-user-a";
      if (local.sessionCookie) {
        setStatus(els.authStatus, "Logged in" + (local.loggedInUser ? " as " + local.loggedInUser : "") + ".", "ok");
      } else {
        setStatus(els.authStatus, "Not logged in.");
      }
    });
  });
}

function persistConfig() {
  chrome.storage.sync.set({
    backendUrl: originOf(els.backendUrl.value.trim()),
    profile: (els.profile.value || "").trim()
  });
}

function extractCookie(res) {
  var bridged = res.headers.get("X-Hermes-Session-Cookie");
  if (bridged) return bridged.trim();
  if (typeof res.headers.getSetCookie === "function") {
    var parts = res.headers.getSetCookie();
    if (parts && parts.length) {
      return parts.map(function (c) { return c.split(";")[0].trim(); }).filter(Boolean).join("; ");
    }
  }
  var raw = res.headers.get("set-cookie");
  if (raw) return raw.split(",").map(function (c) { return c.split(";")[0].trim(); }).join("; ");
  return "";
}

async function login() {
  persistConfig();
  var backend = originOf(els.backendUrl.value.trim());
  var username = (els.username.value || "").trim();
  var password = els.password.value || "";
  if (!username || !password) {
    setStatus(els.authStatus, "Username and password required.", "bad");
    return;
  }
  els.loginBtn.disabled = true;
  setStatus(els.authStatus, "Signing in…");
  try {
    var res = await fetch(backend + "/auth/password-login", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-Company-Page-Chat": "1"
      },
      body: JSON.stringify({
        provider: "company",
        username: username,
        password: password
      })
    });
    var data = {};
    try { data = await res.json(); } catch (e) { data = {}; }
    if (!res.ok) {
      throw new Error(data.detail || data.error || ("login failed (" + res.status + ")"));
    }
    var cookie = extractCookie(res);
    if (!cookie) {
      throw new Error("Login succeeded but no session cookie was returned. The backend must send X-Hermes-Session-Cookie.");
    }
    await chrome.storage.local.set({ sessionCookie: cookie, loggedInUser: username });
    els.password.value = "";
    setStatus(els.authStatus, "Logged in as " + username + ".", "ok");
  } catch (err) {
    setStatus(els.authStatus, err && err.message ? err.message : String(err), "bad");
  } finally {
    els.loginBtn.disabled = false;
  }
}

function logout() {
  chrome.storage.local.remove(["sessionCookie", "loggedInUser"], function () {
    setStatus(els.authStatus, "Logged out.");
  });
}

function ask() {
  persistConfig();
  var question = (els.question.value || "").trim();
  if (!question) {
    setStatus(els.askStatus, "Type a question first.", "bad");
    return;
  }
  els.askBtn.disabled = true;
  els.answer.hidden = true;
  els.answerBody.textContent = "";
  setStatus(els.askStatus, "Reading the page…");
  chrome.runtime.sendMessage(
    {
      type: "ask",
      question: question,
      profile: (els.profile.value || "").trim(),
      backendUrl: originOf(els.backendUrl.value.trim())
    },
    function (response) {
      els.askBtn.disabled = false;
      if (chrome.runtime.lastError) {
        setStatus(els.askStatus, chrome.runtime.lastError.message, "bad");
        return;
      }
      if (!response || !response.ok) {
        setStatus(els.askStatus, (response && response.error) || "Ask failed.", "bad");
        return;
      }
      var result = response.result || {};
      els.answer.hidden = false;
      els.answerBody.innerHTML = renderMarkdown(result.answer || "");
      setStatus(els.askStatus, "Done" + (result.title ? " — " + result.title : "") + ".", "ok");
    }
  );
}

chrome.runtime.onMessage.addListener(function (message) {
  if (!message || message.type !== "ask-progress") return;
  if (message.status === "snapshot") setStatus(els.askStatus, "Reading the page…");
  else if (message.status === "queued") setStatus(els.askStatus, "Sending snapshot…");
  else if (message.status === "running") setStatus(els.askStatus, "Waiting for the agent…");
  if (message.partial) {
    els.answer.hidden = false;
    els.answerBody.innerHTML = renderMarkdown(message.partial);
  }
  if (message.title) {
    els.pageMeta.textContent = message.title + (message.url ? " — " + message.url : "");
  }
});

els.backendUrl.addEventListener("change", persistConfig);
els.profile.addEventListener("change", persistConfig);
els.loginBtn.addEventListener("click", function () { login(); });
els.logoutBtn.addEventListener("click", logout);
els.askBtn.addEventListener("click", ask);
els.question.addEventListener("keydown", function (ev) {
  if ((ev.metaKey || ev.ctrlKey) && ev.key === "Enter") ask();
});

loadSettings();
