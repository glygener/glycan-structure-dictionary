"use strict";

// ---------------------------------------------------------------------------
// tiny helpers
// ---------------------------------------------------------------------------
const $ = (sel) => document.querySelector(sel);
const el = (tag, attrs = {}, ...kids) => {
  const n = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs)) {
    if (k === "class") n.className = v;
    else if (k === "html") n.innerHTML = v;
    else if (k.startsWith("on")) n.addEventListener(k.slice(2), v);
    else if (v !== null && v !== undefined) n.setAttribute(k, v);
  }
  for (const kid of kids) n.append(kid?.nodeType ? kid : document.createTextNode(kid ?? ""));
  return n;
};
const esc = (s) => (s ?? "").toString().replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));

async function api(path, opts = {}) {
  const res = await fetch(path, { headers: { "Content-Type": "application/json" }, ...opts });
  if (!res.ok) {
    let detail = res.statusText;
    try { detail = (await res.json()).detail || detail; } catch {}
    throw new Error(detail);
  }
  return res.status === 204 ? null : res.json();
}

let toastTimer;
function toast(msg, kind = "") {
  const t = $("#toast");
  t.textContent = msg; t.className = kind; t.classList.remove("hidden");
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => t.classList.add("hidden"), 3200);
}

// ---------------------------------------------------------------------------
// state
// ---------------------------------------------------------------------------
const state = { meta: null, currentUuid: null, detail: null };

// ---------------------------------------------------------------------------
// meta + table
// ---------------------------------------------------------------------------
async function refreshMeta() {
  state.meta = await api("/api/meta");
  $("#meta-summary").textContent =
    `${state.meta.n_nodes} nodes · ${state.meta.n_edges} edges · session ${state.meta.session_id}`;
  $("#dirty").classList.toggle("hidden", !state.meta.dirty);
  const sel = $("#filter-class");
  if (sel.options.length <= 1) {
    for (const c of state.meta.classifications) sel.append(el("option", { value: c }, c));
  }
}

let searchTimer;
function debouncedLoad() { clearTimeout(searchTimer); searchTimer = setTimeout(loadNodes, 180); }

async function loadNodes() {
  const q = encodeURIComponent($("#search").value.trim());
  const k = encodeURIComponent($("#filter-class").value);
  const s = encodeURIComponent($("#sort").value);
  const data = await api(`/api/nodes?query=${q}&klass=${k}&sort=${s}&page=1&page_size=300`);
  const tb = $("#node-table").querySelector("tbody");
  tb.innerHTML = "";
  for (const r of data.rows) {
    const badges = [];
    if (r.classification) badges.push(`<span class="badge cls">${esc(r.classification)}</span>`);
    badges.push(`<span class="badge">${r.n_sources} src</span>`);
    if (r.n_exact) badges.push(`<span class="badge">${r.n_exact} syn</span>`);
    if (r.n_abbr) badges.push(`<span class="badge">${r.n_abbr} abbr</span>`);
    if (r.has_edges) badges.push(`<span class="badge">edges</span>`);
    if (r.merged_from?.length) badges.push(`<span class="badge">merged←${r.merged_from.length}</span>`);
    if (r.split_from) badges.push(`<span class="badge">split</span>`);
    const td = el("td", {});
    td.innerHTML = `<div class="lbl-main">${esc(r.lbl)}</div><div class="row-badges">${badges.join("")}</div>`;
    const tr = el("tr", { onclick: () => selectNode(r.term_uuid) }, td);
    tr.dataset.uuid = r.term_uuid;
    if (r.term_uuid === state.currentUuid) tr.classList.add("sel");
    tb.append(tr);
  }
  $("#table-foot").textContent = `${data.total} match${data.total === 1 ? "" : "es"}` +
    (data.total > data.rows.length ? ` (showing ${data.rows.length})` : "");
}

function markSelectedRow() {
  document.querySelectorAll("#node-table tr").forEach((tr) =>
    tr.classList.toggle("sel", tr.dataset.uuid === state.currentUuid));
}

// ---------------------------------------------------------------------------
// detail
// ---------------------------------------------------------------------------
async function selectNode(uuid) {
  state.currentUuid = uuid;
  markSelectedRow();
  state.detail = await api(`/api/nodes/${uuid}`);
  renderDetail();
}

function chip(value, field) {
  const c = el("span", { class: "chip" }, value);
  const other = field === "exact_synonyms" ? "→abbr" : "→syn";
  c.append(el("button", { class: "mv", title: "Move to other list", onclick: () => listEdit("move", field, value) }, "⇄"));
  c.append(el("button", { title: "Rename", onclick: () => renameTerm(field, value) }, "✎"));
  c.append(el("button", { title: "Remove", onclick: () => listEdit("remove", field, value) }, "✕"));
  return c;
}

function listSection(title, field, values) {
  const sec = el("div", { class: "section" });
  sec.append(el("h3", {}, title));
  const chips = el("div", { class: "chips" });
  (values || []).forEach((v) => chips.append(chip(v, field)));
  if (!values || !values.length) chips.append(el("span", { class: "rationale" }, "—"));
  sec.append(chips);
  const inp = el("input", { placeholder: `add ${title.toLowerCase()}…` });
  const add = el("button", {}, "Add");
  add.addEventListener("click", () => { if (inp.value.trim()) listEdit("add", field, inp.value.trim()); });
  inp.addEventListener("keydown", (e) => { if (e.key === "Enter" && inp.value.trim()) listEdit("add", field, inp.value.trim()); });
  sec.append(el("div", { class: "add-inline" }, inp, add));
  return sec;
}

function renderDetail() {
  const d = state.detail; const n = d.node;
  $("#detail-empty").classList.add("hidden");
  const root = $("#detail"); root.classList.remove("hidden"); root.innerHTML = "";

  // head
  const head = el("div", { class: "detail-head" });
  head.append(el("h2", {}, n.lbl));
  if (n.classification) head.append(el("span", { class: "badge cls" }, n.classification));
  head.append(el("span", { class: "uuid" }, n.term_uuid));
  if (n.merged_from_term_uuids?.length) head.append(el("span", { class: "legacy" }, `merged ← ${n.merged_from_term_uuids.length}`));
  if (n.split_from_term_uuid) head.append(el("span", { class: "legacy" }, `split from ${n.split_from_term_uuid.slice(0, 12)}…`));
  root.append(head);

  // actions
  const actions = el("div", { class: "actions" });
  actions.append(el("button", { onclick: openRelabel }, "✎ Relabel"));
  actions.append(el("button", { onclick: openMerge }, "⤵ Merge into…"));
  actions.append(el("button", { onclick: openSplit }, "✂ Split"));
  actions.append(el("button", { class: "danger", onclick: dropNode }, "🗑 Drop"));
  root.append(actions);

  // synonym / abbreviation lists
  root.append(listSection("Exact synonyms", "exact_synonyms", n.exact_synonyms));
  root.append(listSection("Abbreviations", "abbreviations", n.abbreviations));

  // gtc / xref
  if ((n.gtc_id && n.gtc_id.length) || (n.db_xref && n.db_xref.length)) {
    const sec = el("div", { class: "section" });
    sec.append(el("h3", {}, "Identifiers"));
    if (n.gtc_id?.length) sec.append(el("div", {}, "GlyTouCan: " + n.gtc_id.join(", ")));
    if (n.db_xref?.length) sec.append(el("div", { class: "rationale" }, "db_xref: " + n.db_xref.join(", ")));
    root.append(sec);
  }

  // edges
  const esec = el("div", { class: "section" });
  esec.append(el("h3", {}, `Relationships (${d.edges.length})`));
  d.edges.forEach((e) => {
    const dir = e.subj === n.term_uuid ? `${e.pred} →` : `← ${e.pred}`;
    const other = e.subj === n.term_uuid ? e.obj_lbl : e.subj_lbl;
    const row = el("div", { class: "edge-row" });
    row.append(el("span", { class: "pred" }, dir));
    row.append(el("span", {}, other));
    row.append(el("button", { class: "mini danger", style: "margin-left:auto",
      onclick: () => edgeOp("remove", e.subj, e.pred, e.obj) }, "remove"));
    esec.append(row);
  });
  esec.append(el("button", { class: "mini", style: "margin-top:8px", onclick: openAddEdge }, "+ add relationship"));
  root.append(esec);

  // provenance
  const psec = el("div", { class: "section" });
  psec.append(el("h3", {}, `Provenance — ${d.provenance.length} source row(s)`));
  const tbl = el("table", { class: "prov" });
  tbl.innerHTML = "<thead><tr><th>source</th><th>src_lbl</th><th>action</th><th>edge_type</th><th>rationale</th></tr></thead>";
  const body = el("tbody");
  d.provenance.forEach((p) => {
    const tr = el("tr", {});
    tr.innerHTML = `<td>${esc((p.src || "").replace("SRC:", ""))}</td><td>${esc(p.src_lbl)}</td>` +
      `<td>${esc(p.action || "")}</td><td>${esc(p.edge_type || "")}</td>` +
      `<td class="rationale">${esc(p.rationale || "")}</td>`;
    body.append(tr);
  });
  tbl.append(body); psec.append(tbl); root.append(psec);
}

// ---------------------------------------------------------------------------
// list / relabel / edge operations
// ---------------------------------------------------------------------------
async function listEdit(action, field, value, new_value) {
  try {
    await api(`/api/nodes/${state.currentUuid}/lists`, {
      method: "POST", body: JSON.stringify({ changes: [{ action, field, value, new_value }] }),
    });
    await afterMutation(state.currentUuid);
  } catch (e) { toast(e.message, "err"); }
}

function renameTerm(field, value) {
  const nv = prompt(`Rename "${value}" to:`, value);
  if (nv && nv.trim() && nv.trim() !== value) listEdit("rename", field, value, nv.trim());
}

async function edgeOp(action, subj, pred, obj, comment) {
  try {
    await api(`/api/edges`, { method: "POST", body: JSON.stringify({ action, subj, pred, obj, comment }) });
    await afterMutation(state.currentUuid);
  } catch (e) { toast(e.message, "err"); }
}

async function dropNode() {
  if (!confirm(`Drop "${state.detail.node.lbl}"? It will be excluded from the release.`)) return;
  try {
    await api(`/api/nodes/${state.currentUuid}/drop`, { method: "POST" });
    state.currentUuid = null; state.detail = null;
    $("#detail").classList.add("hidden"); $("#detail-empty").classList.remove("hidden");
    await refreshAll();
    toast("Node dropped", "ok");
  } catch (e) { toast(e.message, "err"); }
}

// ---------------------------------------------------------------------------
// modal scaffold
// ---------------------------------------------------------------------------
function openModal(title, bodyNode) {
  $("#modal-title").textContent = title;
  const b = $("#modal-body"); b.innerHTML = ""; b.append(bodyNode);
  $("#modal-backdrop").classList.remove("hidden");
}
function closeModal() { $("#modal-backdrop").classList.add("hidden"); }

// ---------------------------------------------------------------------------
// relabel
// ---------------------------------------------------------------------------
function openRelabel() {
  const n = state.detail.node;
  const inp = el("input", { value: n.lbl, style: "width:100%;padding:6px;border:1px solid var(--border);border-radius:6px" });
  const body = el("div", {});
  body.append(el("p", {}, "New canonical label:"), inp);
  body.append(el("p", {}, "Old label becomes:"));
  const sel = el("select", {});
  ["exact", "abbreviation", "discard"].forEach((o) => sel.append(el("option", { value: o }, o)));
  body.append(sel);
  const go = el("button", { class: "primary" }, "Relabel");
  go.addEventListener("click", async () => {
    try {
      await api(`/api/nodes/${n.term_uuid}/relabel`, { method: "POST",
        body: JSON.stringify({ new_lbl: inp.value.trim(), old_lbl_dest: sel.value }) });
      closeModal(); await afterMutation(n.term_uuid); toast("Relabelled", "ok");
    } catch (e) { toast(e.message, "err"); }
  });
  body.append(el("div", { class: "modal-actions" }, go));
  openModal("Relabel node", body);
}

// ---------------------------------------------------------------------------
// merge
// ---------------------------------------------------------------------------
function openMerge() {
  const A = state.detail.node;
  const body = el("div", {});
  body.append(el("p", { html: `Merge <b>${esc(A.lbl)}</b> <i>into</i> a survivor node. ` +
    `The survivor keeps its UUID; <code>${esc(A.term_uuid)}</code> is recorded as legacy.` }));
  body.append(el("div", {},
    el("label", { class: "inline" }, el("input", { type: "radio", name: "rel", value: "exact_synonym", checked: "checked" }), "as exact synonym"),
    el("label", { class: "inline" }, el("input", { type: "radio", name: "rel", value: "abbreviation" }), "as abbreviation")));
  const search = el("input", { placeholder: "search survivor node…", style: "width:100%;padding:6px;margin-top:8px;border:1px solid var(--border);border-radius:6px" });
  const list = el("div", { class: "pick-list" });
  body.append(search, list);
  let chosen = null;
  const doSearch = async () => {
    const q = encodeURIComponent(search.value.trim());
    const data = await api(`/api/nodes?query=${q}&page_size=25`);
    list.innerHTML = "";
    data.rows.filter((r) => r.term_uuid !== A.term_uuid).forEach((r) => {
      const row = el("div", { class: "pick-row" }, `${r.lbl}  ` );
      row.append(el("span", { class: "uuid" }, r.term_uuid));
      row.addEventListener("click", () => {
        chosen = r.term_uuid;
        list.querySelectorAll(".pick-row").forEach((x) => x.style.background = "");
        row.style.background = "var(--accent-soft)";
        go.disabled = false; go.textContent = `Merge into "${r.lbl}"`;
      });
      list.append(row);
    });
  };
  let st; search.addEventListener("input", () => { clearTimeout(st); st = setTimeout(doSearch, 180); });
  const go = el("button", { class: "primary", disabled: "true" }, "Pick a survivor");
  go.addEventListener("click", async () => {
    const relation = body.querySelector("input[name=rel]:checked").value;
    try {
      await api("/api/merge", { method: "POST", body: JSON.stringify({ survivor: chosen, absorbed: A.term_uuid, relation }) });
      closeModal(); state.currentUuid = chosen; await refreshAll(); await selectNode(chosen); toast("Merged", "ok");
    } catch (e) { toast(e.message, "err"); }
  });
  body.append(el("div", { class: "modal-actions" }, go));
  openModal("Merge node", body);
  doSearch();
}

// ---------------------------------------------------------------------------
// split
// ---------------------------------------------------------------------------
function openSplit() {
  const d = state.detail; const A = d.node;
  let nBuckets = 2;
  const body = el("div", {});
  body.append(el("p", { html: `Split <b>${esc(A.lbl)}</b> into separate nodes. Each child gets a new UUID citing ` +
    `<code>${esc(A.term_uuid)}</code>. Assign every source row, synonym, abbreviation and edge to a bucket.` }));

  const labelRow = el("div", { class: "bucket-grid", style: "margin:8px 0" });
  const labelInputs = [];
  function renderLabels() {
    labelRow.innerHTML = ""; labelInputs.length = 0;
    for (let i = 0; i < nBuckets; i++) {
      const inp = el("input", { class: "blabel", placeholder: `Bucket ${i + 1} label`, value: i === 0 ? A.lbl : "" });
      labelInputs.push(inp);
      labelRow.append(el("div", { class: "bucket" }, el("div", {}, `Child ${i + 1}`), inp));
    }
  }
  renderLabels();
  const addB = el("button", { class: "mini" }, "+ bucket");
  addB.addEventListener("click", () => { nBuckets++; renderLabels(); rebuildRoutes(); });
  body.append(addB, labelRow);

  // routing items
  const routeWrap = el("div", {});
  const routeSelects = []; // {kind, value, select}
  function bucketSelect(defaultIdx = 0) {
    const s = el("select", {});
    for (let i = 0; i < nBuckets; i++) s.append(el("option", { value: i }, `Child ${i + 1}`));
    s.append(el("option", { value: "drop" }, "drop"));
    s.value = String(defaultIdx);
    return s;
  }
  function routeItem(kind, label, sub, value) {
    const it = el("div", { class: "route-item" });
    it.append(el("span", {}, label));
    if (sub) it.append(el("span", { class: "src" }, sub));
    const s = bucketSelect(0);
    it.append(s);
    routeSelects.push({ kind, value, select: s });
    return it;
  }
  function rebuildRoutes() {
    routeWrap.innerHTML = ""; routeSelects.length = 0;
    routeWrap.append(el("h3", {}, "Source rows"));
    d.provenance.forEach((p) => routeWrap.append(routeItem("src", p.src_lbl, (p.src || "").replace("SRC:", ""), p.src_uuid)));
    if (A.exact_synonyms?.length) {
      routeWrap.append(el("h3", {}, "Exact synonyms"));
      A.exact_synonyms.forEach((v) => routeWrap.append(routeItem("exact", v, "", v)));
    }
    if (A.abbreviations?.length) {
      routeWrap.append(el("h3", {}, "Abbreviations"));
      A.abbreviations.forEach((v) => routeWrap.append(routeItem("abbr", v, "", v)));
    }
    if (d.edges.length) {
      routeWrap.append(el("h3", {}, "Relationships"));
      d.edges.forEach((e, i) => {
        const other = e.subj === A.term_uuid ? e.obj_lbl : e.subj_lbl;
        routeWrap.append(routeItem("edge", `${e.pred} ${other}`, "", String(i)));
      });
    }
  }
  rebuildRoutes();
  body.append(routeWrap);

  const go = el("button", { class: "primary" }, "Split");
  go.addEventListener("click", async () => {
    const labels = labelInputs.map((i) => i.value.trim());
    if (labels.some((l) => !l)) { toast("Every bucket needs a label", "err"); return; }
    const children = labels.map((lbl) => ({ lbl, src_uuids: [], exact: [], abbr: [] }));
    const edge_routing = {};
    for (const r of routeSelects) {
      if (r.select.value === "drop") { if (r.kind === "edge") edge_routing[r.value] = "drop"; continue; }
      const idx = parseInt(r.select.value, 10);
      if (r.kind === "src") children[idx].src_uuids.push(r.value);
      else if (r.kind === "exact") children[idx].exact.push(r.value);
      else if (r.kind === "abbr") children[idx].abbr.push(r.value);
      else if (r.kind === "edge") edge_routing[r.value] = idx;
    }
    try {
      const res = await api("/api/split", { method: "POST", body: JSON.stringify({ parent: A.term_uuid, children, edge_routing }) });
      closeModal();
      const firstChild = res.entry.children[0].uuid;
      state.currentUuid = firstChild; await refreshAll(); await selectNode(firstChild);
      toast(`Split into ${res.entry.children.length} nodes`, "ok");
    } catch (e) { toast(e.message, "err"); }
  });
  body.append(el("div", { class: "modal-actions" }, go));
  openModal("Split node", body);
}

// ---------------------------------------------------------------------------
// add edge
// ---------------------------------------------------------------------------
function openAddEdge() {
  const A = state.detail.node;
  const body = el("div", {});
  const sel = el("select", {});
  ["broad_synonym_of", "narrow_synonym_of", "related_synonym_of", "is_a"].forEach((p) => sel.append(el("option", { value: p }, p)));
  body.append(el("p", { html: `<b>${esc(A.lbl)}</b>` }), sel);
  const search = el("input", { placeholder: "search target node…", style: "width:100%;padding:6px;margin-top:8px;border:1px solid var(--border);border-radius:6px" });
  const list = el("div", { class: "pick-list" });
  body.append(search, list);
  let target = null;
  const doSearch = async () => {
    const data = await api(`/api/nodes?query=${encodeURIComponent(search.value.trim())}&page_size=25`);
    list.innerHTML = "";
    data.rows.filter((r) => r.term_uuid !== A.term_uuid).forEach((r) => {
      const row = el("div", { class: "pick-row" }, `${r.lbl}  `);
      row.append(el("span", { class: "uuid" }, r.term_uuid));
      row.addEventListener("click", () => { target = r.term_uuid; list.querySelectorAll(".pick-row").forEach((x) => x.style.background = ""); row.style.background = "var(--accent-soft)"; go.disabled = false; });
      list.append(row);
    });
  };
  let st; search.addEventListener("input", () => { clearTimeout(st); st = setTimeout(doSearch, 180); });
  const go = el("button", { class: "primary", disabled: "true" }, "Add relationship");
  go.addEventListener("click", async () => {
    try { await edgeOp("add", A.term_uuid, sel.value, target); closeModal(); toast("Edge added", "ok"); }
    catch (e) { toast(e.message, "err"); }
  });
  body.append(el("div", { class: "modal-actions" }, go));
  openModal("Add relationship", body);
  doSearch();
}

// ---------------------------------------------------------------------------
// persistence + journal
// ---------------------------------------------------------------------------
async function afterMutation(reselect) {
  await refreshMeta();
  await loadNodes();
  if (reselect) await selectNode(reselect);
}
async function refreshAll() { await refreshMeta(); await loadNodes(); }

$("#btn-save").addEventListener("click", async () => {
  try { const r = await api("/api/save", { method: "POST" }); await refreshMeta(); toast(`Saved ${r.n_nodes} nodes → master_*_curated.json`, "ok"); }
  catch (e) { toast(e.message, "err"); }
});
$("#btn-sync").addEventListener("click", async () => {
  if (!confirm("Write changes back to the resolved source files + curator_overrides.json? (.bak backups are made.)")) return;
  try { const r = await api("/api/sync-sources", { method: "POST" }); toast(`Synced: ${r.stats.rows_regrouped} regrouped, ${r.stats.rows_dropped} dropped, ${r.stats.override_nodes} override nodes`, "ok"); }
  catch (e) { toast(e.message, "err"); }
});
$("#btn-publish").addEventListener("click", async () => {
  if (!confirm("Publish a timestamped release and rebuild the reviewer TSV?\nExisting EoG sentences are kept as-is (no new sentences fetched, no API calls).")) return;
  try { const r = await api("/api/publish", { method: "POST" }); toast(`Published ${r.timestamp}` + (r.tsv_returncode === 0 ? " · TSV refreshed" : " · TSV step see console"), "ok"); if (r.tsv_tail) console.log(r.tsv_tail); }
  catch (e) { toast(e.message, "err"); }
});
$("#btn-undo").addEventListener("click", async () => {
  try { await api("/api/undo", { method: "POST" }); state.currentUuid = null; state.detail = null; $("#detail").classList.add("hidden"); $("#detail-empty").classList.remove("hidden"); await refreshAll(); toast("Undone", "ok"); }
  catch (e) { toast(e.message, "err"); }
});
$("#btn-journal").addEventListener("click", async () => {
  const j = await api("/api/journal");
  const pre = el("pre", { class: "journal" }, j.entries.map((e) => JSON.stringify(e)).join("\n") || "(empty)");
  openModal(`Journal — ${j.entries.length} entries`, pre);
});

$("#modal-close").addEventListener("click", closeModal);
$("#modal-backdrop").addEventListener("click", (e) => { if (e.target.id === "modal-backdrop") closeModal(); });
$("#search").addEventListener("input", debouncedLoad);
$("#filter-class").addEventListener("change", loadNodes);
$("#sort").addEventListener("change", loadNodes);

// ---------------------------------------------------------------------------
// boot
// ---------------------------------------------------------------------------
(async function boot() {
  await refreshMeta();
  await loadNodes();
})();
