/* The Council — live deliberation UI logic (feature 002, contracts/web-ui-v2.md).
   EventSource + fetch only. No CDN, no build step. <500 lines. */
"use strict";
const $ = (id) => document.getElementById(id);
const esc = (s) => String(s == null ? "" : s).replace(/[&<>]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;" }[c]));
const COLORS = ["#58a6ff", "#3fb950", "#d29922", "#f778ba", "#7c5cff"];

let sessionId = crypto.randomUUID();
let providersData = null;      // last GET /api/providers payload
let streaming = false;
const colorMap = {};
const colorFor = (name) => (colorMap[name] || (colorMap[name] = COLORS[Object.keys(colorMap).length % COLORS.length]));

/* ---------------- boot ---------------- */
async function boot() {
  await refreshProviders();
  wireEvents();
}

async function refreshProviders() {
  try {
    const r = await fetch("/api/providers");
    providersData = await r.json();
  } catch (_) { providersData = { providers: [], active: null, configured_any: false }; }
  applyProviderState();
}

function applyProviderState() {
  const active = providersData.active;
  if (active) {
    setChip(active.provider, active.model);
    $("bar").classList.remove("hidden");
    $("getstarted").classList.add("hidden");
    $("run-hint").classList.add("hidden");
  } else {
    $("chip").classList.add("hidden");
    if (providersData.configured_any) {
      // A key exists but nothing is selected yet — show the bar but block runs.
      $("bar").classList.remove("hidden");
      $("getstarted").classList.add("hidden");
      showRunHint("Pick a provider in ⚙ Settings before asking.");
    } else {
      showGetStarted();
    }
  }
}

function providerName(id) {
  const p = (providersData.providers || []).find((x) => x.id === id);
  return p ? p.display_name : id;
}
function setChip(provider, model) {
  $("chip-provider").textContent = providerName(provider);
  $("chip-model").textContent = model ? " · " + model : "";
  $("chip").classList.remove("hidden");
}
function showRunHint(msg) { $("run-hint").textContent = msg; $("run-hint").classList.remove("hidden"); }
function showGetStarted() {
  $("getstarted").classList.remove("hidden");
  $("bar").classList.add("hidden");
  const extra = $("getstarted-extra");
  extra.innerHTML = 'No key yet? Google AI Studio issues a free one at ' +
    '<a href="https://aistudio.google.com/apikey" target="_blank" rel="noopener">aistudio.google.com/apikey</a>.';
  extra.classList.remove("hidden");
}

/* ---------------- settings panel ---------------- */
function openSettings() {
  const sel = $("p-provider");
  sel.innerHTML = (providersData.providers || [])
    .map((p) => `<option value="${p.id}">${esc(p.display_name)}</option>`).join("");
  const active = providersData.active;
  sel.value = active ? active.provider : (providersData.providers[0] && providersData.providers[0].id);
  onProviderChange();
  $("p-error").classList.add("hidden");
  $("p-key").value = "";
  $("overlay").classList.remove("hidden");
  $("settings").classList.remove("hidden");
}
function closeSettings() { $("overlay").classList.add("hidden"); $("settings").classList.add("hidden"); }

function currentSpec() { return (providersData.providers || []).find((p) => p.id === $("p-provider").value); }

function onProviderChange() {
  const spec = currentSpec();
  if (!spec) return;
  // Models: curated list + an "Other…" free-text option.
  const models = spec.curated_models || [];
  const opts = models.map((m) => `<option value="${esc(m)}">${esc(m)}</option>`).join("") +
    `<option value="__other__">Other (type a model)…</option>`;
  $("p-model").innerHTML = opts;
  const active = providersData.active;
  if (active && active.provider === spec.id && models.includes(active.model)) {
    $("p-model").value = active.model;
  } else if (models.length) {
    $("p-model").value = spec.default_model || models[0];
  } else {
    $("p-model").value = "__other__";
  }
  onModelChange();
  // Base URL only for providers that allow a custom endpoint.
  $("p-baseurl-field").classList.toggle("hidden", !spec.allows_custom_base_url);
  $("p-baseurl").placeholder = "http://localhost:11434/v1";
  // "configured via environment" badge, no key reveal (US1 #4).
  const envConfigured = spec.key_source === "env";
  $("p-env").classList.toggle("hidden", !envConfigured);
  $("p-key").placeholder = envConfigured
    ? "A key is set in the environment — leave blank to keep it"
    : "Paste your key — held in memory only";
}
function onModelChange() {
  const other = $("p-model").value === "__other__";
  $("p-model-custom-field").classList.toggle("hidden", !other);
}
function chosenModel() {
  return $("p-model").value === "__other__" ? $("p-model-custom").value.trim() : $("p-model").value;
}

async function saveSettings() {
  const spec = currentSpec();
  const body = { provider: spec.id, model: chosenModel() };
  const key = $("p-key").value.trim();
  if (key) body.api_key = key;
  if (spec.allows_custom_base_url) body.base_url = $("p-baseurl").value.trim();
  $("p-save").disabled = true;
  try {
    const r = await fetch("/api/providers/active", {
      method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body),
    });
    const data = await r.json();
    if (!r.ok) { showFormError(data.error); return; }
    await refreshProviders();
    setChip(data.active.provider, data.active.model);
    closeSettings();
  } catch (e) {
    showFormError({ message: "Could not reach the server.", hint: "Is the app still running?" });
  } finally { $("p-save").disabled = false; }
}
function showFormError(err) {
  err = err || { message: "Something went wrong.", hint: "" };
  $("p-error").innerHTML = esc(err.message) + (err.hint ? `<div class="hint">${esc(err.hint)}</div>` : "");
  $("p-error").classList.remove("hidden");
}

/* ---------------- stage timeline ---------------- */
const STAGES = ["recruit", "debate", "factcheck", "synth", "verdict"];
function setStage(name) {
  const idx = STAGES.indexOf(name);
  if (idx < 0) return;
  $("timeline").classList.remove("hidden");
  STAGES.forEach((s, i) => {
    const step = document.querySelector(`.step[data-stage="${s}"]`);
    step.classList.toggle("done", i < idx);
    step.classList.toggle("active", i === idx);
  });
}
function stopTimeline() { document.querySelectorAll(".step.active").forEach((s) => s.classList.remove("active")); }
function completeTimeline() {
  STAGES.forEach((s) => {
    const step = document.querySelector(`.step[data-stage="${s}"]`);
    step.classList.add("done"); step.classList.remove("active");
  });
}

/* ---------------- reset ---------------- */
function reset() {
  ["panel", "debate", "facts", "verdict", "refusal-card", "clarify-card", "error-card", "trace"].forEach((k) => ($(k).innerHTML = ""));
  ["panel-sec", "debate-sec", "facts-sec", "verdict-sec", "refusal-sec", "clarify-sec", "error-sec"].forEach((k) => $(k).classList.add("hidden"));
  $("notice").classList.add("hidden");
  STAGES.forEach((s) => document.querySelector(`.step[data-stage="${s}"]`).classList.remove("done", "active"));
  Object.keys(colorMap).forEach((k) => delete colorMap[k]);
}

/* ---------------- SSE handlers ---------------- */
function onRunConfig(d) { setChip(d.provider, d.model); setStage("recruit"); }
function onRecruit(d) {
  setStage("recruit"); $("panel-sec").classList.remove("hidden");
  const p = d.panelist;
  $("panel").insertAdjacentHTML("beforeend",
    `<div class="card pcard" style="border-top-color:${colorFor(p.name)}">
       <div class="name">${esc(p.name)}</div>
       <div class="meta">${esc(p.expertise)} · ${esc(p.stance)}</div>
       <div class="reason">${esc(p.recruitment_reason)}</div>
       ${p.is_challenger ? '<span class="badge">⚔ Challenger</span>' : ""}
     </div>`);
}
function onFallback(d) {
  setStage("recruit"); $("panel-sec").classList.remove("hidden");
  $("notice").classList.remove("hidden");
  $("notice").textContent = "Live recruitment failed, so a deterministic fallback panel was substituted (FR-016). The run still completes.";
  (d.roster.panelists || []).forEach((p) => onRecruit({ panelist: p }));
}
function onTurn(d) {
  setStage("debate"); $("debate-sec").classList.remove("hidden");
  let group = $("debate").querySelector(`[data-round="${d.round}"]`);
  if (!group) {
    $("debate").insertAdjacentHTML("beforeend",
      `<div data-round="${d.round}"><div class="round-label">Round ${d.round}</div></div>`);
    group = $("debate").querySelector(`[data-round="${d.round}"]`);
  }
  const color = d.references_prior ? "var(--accent)" : colorFor(d.panelist_name);
  group.insertAdjacentHTML("beforeend",
    `<div class="turn${d.references_prior ? " rebuttal" : ""}" style="border-left-color:${color}">
       <div class="who">${esc(d.panelist_name)}${d.references_prior ? '<span class="tag">rebuttal</span>' : ""}</div>
       <div>${esc(d.content)}</div>
     </div>`);
}
function onToolCall() { setStage("factcheck"); $("facts-sec").classList.remove("hidden"); }
function onClaimRow(c) {
  $("facts-sec").classList.remove("hidden");
  const link = c.source_url ? ` · <a href="${esc(c.source_url)}" target="_blank" rel="noopener">${esc(c.source_title || "source")}</a>` : "";
  $("facts").insertAdjacentHTML("beforeend",
    `<div class="claim"><span class="status ${esc(c.status)}">${esc(c.status)}</span><div>${esc(c.text)}${link}</div></div>`);
}
function onSynthesize() { setStage("synth"); }
function onVerdict(v) {
  completeTimeline();
  $("verdict-sec").classList.remove("hidden");
  (v.fact_checks || []).forEach(onClaimRow);
  const pct = { high: 100, medium: 60, low: 30 }[v.confidence] || 30;
  const pos = (v.positions || []).map((p) => `<div class="pos"><b>${esc(p.label)}:</b> ${esc(p.strongest_argument)}</div>`).join("");
  const dis = (v.dissents || []).map((x) => `<li>${esc(x.panelist_name)}: ${esc(x.objection)}</li>`).join("");
  $("verdict").innerHTML =
    `<div class="cap">Question</div><div class="q">${esc(v.question)}</div>
     <div class="cap">Positions</div>${pos}
     <div class="cap" style="margin-top:10px">Recommendation</div><div class="rec">${esc(v.recommendation)}</div>
     <div class="cap">Confidence · <b>${esc(v.confidence)}</b></div><div class="meter"><i style="width:${pct}%"></i></div>
     ${dis ? `<div class="cap" style="margin-top:12px">Dissents</div><ul>${dis}</ul>` : ""}
     <button class="btn" id="dl" style="margin-top:14px">⬇ Download JSON</button>`;
  $("dl").onclick = () => {
    const b = new Blob([JSON.stringify(v, null, 2)], { type: "application/json" });
    const a = document.createElement("a");
    a.href = URL.createObjectURL(b); a.download = "council-verdict.json"; a.click();
  };
}
function onRefusal(d) { stopTimeline(); $("refusal-sec").classList.remove("hidden"); $("refusal-card").textContent = d.reason || "The question was declined."; }
function onClarify(d) { stopTimeline(); $("clarify-sec").classList.remove("hidden"); $("clarify-card").textContent = d.question_back || "Could you clarify the question?"; $("q").focus(); }
function onError(d) {
  stopTimeline(); $("error-sec").classList.remove("hidden");
  const detail = (d && d.detail) || "The deliberation could not complete.";
  const next = d && d.code === "unconfigured" ? "Open ⚙ Settings to choose a provider and add a key." : "Check your provider settings and try again.";
  $("error-card").innerHTML = `${esc(detail)}<div class="next">${esc(next)}</div>`;
  if (d && d.code === "unconfigured") { refreshProviders(); }
}
function onTrace(kind, label, detail) {
  $("trace").insertAdjacentHTML("beforeend",
    `<div class="trace-event"><b>${esc(kind)}</b> ${esc(label)} ${esc(detail)}</div>`);
}

/* ---------------- stream ---------------- */
const TERMINAL = new Set(["verdict", "refusal", "clarify", "error"]);
function stream(question) {
  reset();
  streaming = true; $("ask").disabled = true; $("run-hint").classList.add("hidden");
  const url = `/api/deliberate/stream?question=${encodeURIComponent(question)}` +
    `&rounds=${$("rounds").value}&panel=${$("panel").value}&session_id=${encodeURIComponent(sessionId)}`;
  const es = new EventSource(url);
  const handlers = {
    run_config: onRunConfig, recruit: onRecruit, fallback: onFallback, turn: onTurn,
    tool_call: onToolCall, guardrail: () => {}, synthesize: onSynthesize,
    verdict: onVerdict, refusal: onRefusal, clarify: onClarify, error: onError,
  };
  Object.keys(handlers).forEach((k) => es.addEventListener(k, (e) => {
    let d = {}; try { d = JSON.parse(e.data); } catch (_) {}
    handlers[k](d);
    onTrace(k, d.panelist ? d.panelist.name : (d.panelist_name || d.tool || d.rule || d.provider || ""),
      d.reason || d.question_back || d.outcome || d.detail || (d.roster ? "fallback roster" : ""));
    if (TERMINAL.has(k)) { es.close(); streaming = false; $("ask").disabled = false; }
  }));
  es.onerror = () => { es.close(); if (streaming) { streaming = false; $("ask").disabled = false; } };
}

/* ---------------- wire up ---------------- */
function submit() {
  if (streaming) return;
  if (!providersData.active) { openSettings(); return; }  // blocked while unconfigured (US1 #5)
  const q = $("q").value.trim();
  if (q) stream(q);
}
function wireEvents() {
  $("open-settings").onclick = openSettings;
  $("getstarted-btn").onclick = openSettings;
  $("close-settings").onclick = closeSettings;
  $("p-cancel").onclick = closeSettings;
  $("overlay").onclick = closeSettings;
  $("p-provider").onchange = onProviderChange;
  $("p-model").onchange = onModelChange;
  $("p-save").onclick = saveSettings;
  $("ask").onclick = submit;
  $("q").addEventListener("keydown", (e) => { if (e.key === "Enter") submit(); });
}

boot();
