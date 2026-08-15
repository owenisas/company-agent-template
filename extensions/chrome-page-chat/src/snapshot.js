/**
 * Structured, sanitized page snapshot. Injected on Ask via executeScript.
 * Last expression is the snapshot object (MV3 files injection return value).
 */
(function snapshotPage() {
  var TEXT_CAP = 12000;
  var LINKS_CAP = 50;
  var INTERACT_CAP = 80;
  var FORMS_CAP = 20;
  var FIELDS_PER_FORM = 30;
  var OUTLINE_CAP = 40;
  var SECRET_RE = /(pass(word|wd|code)?|secret|token|api[_-]?key|auth|csrf|otp|ssn|credit|card|cvv|cvc)/i;

  function visible(el) {
    if (!el || el.nodeType !== 1) return false;
    if (el.getAttribute("aria-hidden") === "true") return false;
    var st = window.getComputedStyle(el);
    if (!st) return false;
    if (st.display === "none" || st.visibility === "hidden" || st.opacity === "0") return false;
    var r = el.getBoundingClientRect();
    return r.width > 0 && r.height > 0;
  }

  function collapse(s) {
    return String(s || "").replace(/\s+/g, " ").trim();
  }

  function clip(s, n) {
    s = String(s || "");
    return s.length > n ? s.slice(0, n) : s;
  }

  function isSecretName(s) {
    return SECRET_RE.test(String(s || ""));
  }

  function cssEscape(ident) {
    if (window.CSS && CSS.escape) return CSS.escape(ident);
    return String(ident).replace(/[^a-zA-Z0-9_-]/g, "\\$&");
  }

  function selectorFor(el, index) {
    if (el.id) return "#" + cssEscape(el.id);
    var name = el.getAttribute("name");
    if (name) {
      var tagged = el.tagName.toLowerCase() + '[name="' + name.replace(/"/g, '\\"') + '"]';
      if (document.querySelectorAll(tagged).length === 1) return tagged;
    }
    var role = el.getAttribute("role");
    if (role) {
      var withRole = el.tagName.toLowerCase() + '[role="' + role + '"]';
      if (document.querySelectorAll(withRole).length === 1) return withRole;
    }
    return el.tagName.toLowerCase() + "[data-pf-el='" + index + "']";
  }

  function labelFor(el) {
    var aria = el.getAttribute("aria-label");
    if (aria) return collapse(aria);
    var labelled = el.getAttribute("aria-labelledby");
    if (labelled) {
      var bits = labelled.split(/\s+/).map(function (id) {
        var n = document.getElementById(id);
        return n ? collapse(n.innerText) : "";
      }).filter(Boolean);
      if (bits.length) return bits.join(" ");
    }
    if (el.id) {
      var lab = document.querySelector('label[for="' + cssEscape(el.id) + '"]');
      if (lab) return collapse(lab.innerText);
    }
    var wrap = el.closest && el.closest("label");
    if (wrap) return collapse(wrap.innerText);
    return collapse(el.getAttribute("placeholder") || el.getAttribute("title") || "");
  }

  function mainRoot() {
    return (
      document.querySelector("main") ||
      document.querySelector("[role='main']") ||
      document.querySelector("article") ||
      document.body
    );
  }

  function mainText() {
    var root = mainRoot();
    if (!root) return "";
    var clone = root.cloneNode(true);
    var kill = clone.querySelectorAll("script, style, noscript, template, [aria-hidden='true']");
    for (var i = 0; i < kill.length; i++) kill[i].remove();
    var pw = clone.querySelectorAll("input[type='password']");
    for (var j = 0; j < pw.length; j++) pw[j].setAttribute("value", "");
    return clip(collapse(clone.innerText || ""), TEXT_CAP);
  }

  var outline = [];
  var heads = document.querySelectorAll("h1, h2, h3");
  for (var h = 0; h < heads.length && outline.length < OUTLINE_CAP; h++) {
    var hd = heads[h];
    if (!visible(hd)) continue;
    outline.push({
      level: Number(hd.tagName.charAt(1)),
      text: clip(collapse(hd.innerText), 200)
    });
  }

  var links = [];
  var as = document.querySelectorAll("a[href]");
  for (var a = 0; a < as.length && links.length < LINKS_CAP; a++) {
    var anchor = as[a];
    if (!visible(anchor)) continue;
    var href = anchor.href || anchor.getAttribute("href") || "";
    if (!href || href.indexOf("javascript:") === 0) continue;
    links.push({
      text: clip(collapse(anchor.innerText || anchor.getAttribute("aria-label") || ""), 160),
      href: clip(href, 500)
    });
  }

  var interactables = [];
  var controls = document.querySelectorAll(
    "button, input, textarea, select, [role='button'], [role='textbox'], [role='link']"
  );
  for (var c = 0; c < controls.length && interactables.length < INTERACT_CAP; c++) {
    var el = controls[c];
    if (!visible(el)) continue;
    var type = (el.getAttribute("type") || "").toLowerCase();
    if (type === "hidden") continue;
    var idx = interactables.length + 1;
    var id = "el_" + String(idx).padStart(3, "0");
    try { el.setAttribute("data-pf-el", String(idx)); } catch (e) { /* ignore */ }
    var role = el.getAttribute("role") || el.tagName.toLowerCase();
    var name = labelFor(el) || clip(collapse(el.innerText), 80);
    interactables.push({
      id: id,
      role: role,
      tag: el.tagName,
      type: type || null,
      name: clip(name, 160),
      selector: selectorFor(el, idx),
      visible: true,
      disabled: !!(el.disabled || el.getAttribute("aria-disabled") === "true")
    });
  }

  var forms = [];
  var formEls = document.querySelectorAll("form");
  for (var f = 0; f < formEls.length && forms.length < FORMS_CAP; f++) {
    var form = formEls[f];
    var fields = [];
    var inputs = form.querySelectorAll("input, textarea, select");
    for (var i2 = 0; i2 < inputs.length && fields.length < FIELDS_PER_FORM; i2++) {
      var field = inputs[i2];
      var ftype = (field.getAttribute("type") || field.tagName.toLowerCase()).toLowerCase();
      var fname = field.getAttribute("name") || field.id || "";
      var secret = ftype === "password" || isSecretName(fname) || isSecretName(field.id);
      var value = "";
      if (!secret && ftype !== "hidden" && "value" in field) {
        value = clip(String(field.value || ""), 80);
      }
      fields.push({
        id: field.id || null,
        type: ftype,
        name: fname || null,
        label: clip(labelFor(field), 160),
        value: secret ? "" : value
      });
    }
    forms.push({
      id: form.id || "form_" + String(forms.length + 1),
      action: clip(form.getAttribute("action") || "", 400),
      method: (form.getAttribute("method") || "get").toLowerCase(),
      fields: fields
    });
  }

  var iframeCount = document.querySelectorAll("iframe").length;

  return {
    url: location.href,
    finalUrl: location.href,
    title: document.title || "",
    lang: document.documentElement.lang || "",
    capturedAt: new Date().toISOString(),
    viewport: {
      w: window.innerWidth || 0,
      h: window.innerHeight || 0,
      scrollY: window.scrollY || 0,
      scrollH: document.documentElement.scrollHeight || 0
    },
    outline: outline,
    text: mainText(),
    links: links,
    interactables: interactables,
    forms: forms,
    iframesSkipped: iframeCount,
    screenshot: null
  };
})();
