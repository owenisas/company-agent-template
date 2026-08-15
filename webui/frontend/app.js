(function () {
  "use strict";

  var loginEl = document.getElementById("login");
  var appEl = document.getElementById("app");
  var loginForm = document.getElementById("login-form");
  var loginError = document.getElementById("login-error");
  var profileSelect = document.getElementById("profile-select");
  var whoEl = document.getElementById("who");
  var logoutBtn = document.getElementById("logout");
  var chatForm = document.getElementById("chat-form");
  var messageEl = document.getElementById("message");
  var threadEl = document.getElementById("thread");
  var chatStatus = document.getElementById("chat-status");
  var chatSub = document.getElementById("chat-sub");
  var sendBtn = document.getElementById("send");
  var usageBody = document.getElementById("usage-body");
  var viewChat = document.getElementById("view-chat");
  var viewUsage = document.getElementById("view-usage");
  var viewNotion = document.getElementById("view-notion");
  var notionStatus = document.getElementById("notion-status");
  var notionDetail = document.getElementById("notion-detail");
  var notionConnect = document.getElementById("notion-connect");
  var notionDisconnect = document.getElementById("notion-disconnect");

  function api(path, options) {
    options = options || {};
    var headers = options.headers || {};
    if (options.body && typeof options.body === "string") {
      headers["Content-Type"] = "application/json";
    }
    return fetch(path, {
      credentials: "same-origin",
      method: options.method || "GET",
      headers: headers,
      body: options.body,
    }).then(function (res) {
      return res.json().catch(function () {
        return {};
      }).then(function (data) {
        if (!res.ok) {
          var err = new Error(data.detail || res.statusText || "request failed");
          err.status = res.status;
          throw err;
        }
        return data;
      });
    });
  }

  function showApp(who) {
    loginEl.hidden = true;
    appEl.hidden = false;
    var role = who.admin ? "admin" : who.role || "viewer";
    whoEl.textContent = who.username + " · " + role;
  }

  function showLogin(message) {
    appEl.hidden = true;
    loginEl.hidden = false;
    if (message) loginError.textContent = message;
  }

  function setStatus(text, bad) {
    chatStatus.textContent = text || "";
    chatStatus.classList.toggle("is-bad", !!bad);
  }

  function addMessage(kind, meta, text, pending) {
    var li = document.createElement("li");
    li.className = "msg msg-" + kind + (pending ? " msg-pending" : "");
    var m = document.createElement("p");
    m.className = "msg-meta";
    m.textContent = meta;
    var b = document.createElement("pre");
    b.className = "msg-body";
    b.textContent = text;
    li.appendChild(m);
    li.appendChild(b);
    threadEl.appendChild(li);
    li.scrollIntoView({ block: "end" });
    return b;
  }

  function loadProfiles(preferred) {
    return api("/api/profiles").then(function (data) {
      var names = data.profiles || [];
      profileSelect.innerHTML = "";
      names.forEach(function (name) {
        var opt = document.createElement("option");
        opt.value = name;
        opt.textContent = name;
        profileSelect.appendChild(opt);
      });
      if (preferred && names.indexOf(preferred) !== -1) {
        profileSelect.value = preferred;
      }
      var current = profileSelect.value || "none available";
      chatSub.textContent = names.length
        ? "Sending as " + current + "."
        : "No profiles in your scope.";
      sendBtn.disabled = !names.length;
    });
  }

  function loadUsage() {
    return api("/api/usage").then(function (data) {
      usageBody.innerHTML = "";
      (data.profiles || []).forEach(function (row) {
        var tr = document.createElement("tr");
        var cells = [
          row.profile,
          row.input_tokens,
          row.output_tokens,
          row.reasoning_tokens,
          row.total_tokens,
          row.api_call_count,
        ];
        cells.forEach(function (value, i) {
          var td = document.createElement(i === 0 ? "th" : "td");
          if (i === 0) td.scope = "row";
          if (i > 0) td.className = "num";
          td.textContent = value;
          tr.appendChild(td);
        });
        usageBody.appendChild(tr);
      });
    });
  }

  function loadNotion() {
    return api("/api/notion/status").then(function (data) {
      if (data.connected) {
        notionStatus.textContent = "Connected to " + (data.workspace_name || "a Notion workspace") + ".";
        notionDetail.textContent = data.owner_name
          ? "Authorized by " + data.owner_name + "."
          : "Server holds the grant. The browser never sees the token.";
        notionConnect.hidden = true;
        notionDisconnect.hidden = false;
        return;
      }
      notionConnect.hidden = false;
      notionDisconnect.hidden = true;
      if (!data.configured) {
        notionStatus.textContent = "Not configured.";
        notionDetail.textContent = "Set NOTION_CLIENT_ID, NOTION_CLIENT_SECRET, and NOTION_REDIRECT_URI. See docs/notion-setup.md.";
        notionConnect.classList.add("is-disabled");
        return;
      }
      notionStatus.textContent = "Not connected.";
      notionDetail.textContent = "Connect a workspace. You will pick pages on Notion's consent screen.";
      notionConnect.classList.remove("is-disabled");
    });
  }

  function switchView(name) {
    viewChat.hidden = name !== "chat";
    viewUsage.hidden = name !== "usage";
    if (viewNotion) viewNotion.hidden = name !== "notion";
    document.querySelectorAll(".nav-item").forEach(function (btn) {
      btn.classList.toggle("is-active", btn.getAttribute("data-view") === name);
    });
    if (name === "usage") loadUsage().catch(function (err) {
      setStatus(err.message, true);
    });
    if (name === "notion") loadNotion().catch(function (err) {
      notionStatus.textContent = err.message || "Could not load Notion status.";
    });
  }

  document.querySelectorAll(".nav-item").forEach(function (btn) {
    btn.addEventListener("click", function () {
      switchView(btn.getAttribute("data-view"));
    });
  });

  if (notionDisconnect) {
    notionDisconnect.addEventListener("click", function () {
      api("/api/notion/disconnect", { method: "POST" })
        .then(function () {
          return loadNotion();
        })
        .catch(function (err) {
          notionStatus.textContent = err.message || "Disconnect failed.";
        });
    });
  }

  profileSelect.addEventListener("change", function () {
    chatSub.textContent = "Sending as " + profileSelect.value + ".";
  });

  loginForm.addEventListener("submit", function (event) {
    event.preventDefault();
    loginError.textContent = "";
    var body = JSON.stringify({
      username: document.getElementById("username").value,
      password: document.getElementById("password").value,
    });
    api("/api/login", { method: "POST", body: body })
      .then(function (who) {
        showApp(who);
        return loadProfiles(who.profile);
      })
      .catch(function (err) {
        loginError.textContent = err.message || "Could not sign in.";
      });
  });

  logoutBtn.addEventListener("click", function () {
    api("/api/logout", { method: "POST" }).finally(function () {
      threadEl.innerHTML = "";
      showLogin("");
    });
  });

  function pollJob(jobId, bodyEl) {
    function tick() {
      api("/api/jobs/" + jobId)
        .then(function (job) {
          var text = job.result || job.partial || "";
          bodyEl.textContent = text || (job.status === "running" ? "Working…" : "");
          bodyEl.parentElement.classList.toggle("msg-pending", job.status === "running");
          if (job.status === "running") {
            setStatus("Running · " + Math.round(job.elapsed) + "s");
            window.setTimeout(tick, 700);
            return;
          }
          if (job.status === "error") {
            setStatus(job.error || "Job failed", true);
            if (!bodyEl.textContent) bodyEl.textContent = job.error || "error";
            sendBtn.disabled = !profileSelect.value;
            return;
          }
          setStatus("Done · " + Math.round(job.elapsed) + "s");
          sendBtn.disabled = !profileSelect.value;
        })
        .catch(function (err) {
          setStatus(err.message, true);
          sendBtn.disabled = !profileSelect.value;
        });
    }
    tick();
  }

  chatForm.addEventListener("submit", function (event) {
    event.preventDefault();
    var profile = profileSelect.value;
    var message = messageEl.value.trim();
    if (!profile || !message) return;
    sendBtn.disabled = true;
    addMessage("user", "You → " + profile, message, false);
    var bodyEl = addMessage("agent", profile, "Working…", true);
    messageEl.value = "";
    setStatus("Starting…");
    api("/api/chat", {
      method: "POST",
      body: JSON.stringify({ profile: profile, message: message }),
    })
      .then(function (data) {
        pollJob(data.job_id, bodyEl);
      })
      .catch(function (err) {
        bodyEl.textContent = err.message;
        setStatus(err.message, true);
        sendBtn.disabled = false;
      });
  });

  api("/api/whoami")
    .then(function (who) {
      showApp(who);
      return loadProfiles(who.profile);
    })
    .then(function () {
      var params = new URLSearchParams(window.location.search);
      if (params.get("notion")) {
        switchView("notion");
        loadNotion();
      }
    })
    .catch(function () {
      showLogin("");
    });
})();
