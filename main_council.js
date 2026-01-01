"use strict";

/* Ctrl+F -> DATA_API_URL */
const DATA_API_URL =
  "https://script.google.com/macros/s/AKfycbzgSYexWWQk7EXJAM_HQ1vqtLeJKDULkHLP7FzZLeR0hFZtwdScIIc97qJkb1VA7ihA/exec?tab=Main";

let COUNCILORS = [];

/* ---------- util ---------- */
function escapeHtml(s) {
  return String(s)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}
function normalizeForSearch(s) {
  return String(s).toLowerCase().replace(/\s+/g, "");
}
function statKey(line) {
  return String(line)
    .replace(/[-+]?\d+(\.\d+)?%?/g, "")
    .replace(/\s+/g, " ")
    .replace(/[()]/g, "")
    .trim();
}
function formatValueForDisplay(raw) {
  if (raw === null || raw === undefined) return "";
  let s = String(raw).trim();
  if (!s) return "";

  // 활성화됨 같은 문자열은 그대로
  const maybeNum = s.replace("%", "").replace(/\s+/g, "");
  const n = Number(maybeNum);
  if (!Number.isFinite(n)) return s;

  // % 포함이면 부호 보정 (+12%)
  if (/%/.test(s)) {
    const r = Math.round(n);
    return r >= 0 ? `+${r}%` : `${r}%`;
  }

  // 정수는 + 붙여서 통일 (+2 / -3)
  if (Number.isInteger(n)) return n >= 0 ? `+${n}` : `${n}`;

  // 소수는 퍼센트로(+12%)
  const pct = Math.round(n * 100);
  return pct >= 0 ? `+${pct}%` : `${pct}%`;
}
function splitOptionAndValue(line) {
  const s = String(line || "").trim();
  const m = s.match(/([+-]?\d+(?:\.\d+)?%?)\s*$/);
  if (!m) return { opt: s, val: "" };
  const val = m[1].replace(/\s+/g, "");
  const opt = s.slice(0, m.index).trim();
  return { opt: opt || s, val: opt ? val : "" };
}

/* ✅ 등급 -> 클래스 (전설=주황, 특급=보라) */
function getGradeClass(gradeText) {
  const t = String(gradeText || "");
  if (t.includes("특급")) return "is-special";
  if (t.includes("전설")) return "is-legend";
  return "";
}

/* ✅ API unique: ["옵션 +12%"] 또는 [{option,value}] 둘 다 지원 */
function canonicalizeUniqueFromApi(x) {
  if (Array.isArray(x.unique) && x.unique.length && typeof x.unique[0] === "string") {
    return x.unique.map((v) => String(v));
  }
  if (Array.isArray(x.unique) && x.unique.length && typeof x.unique[0] === "object") {
    return x.unique.map((u) => {
      const opt = (u.option ?? "").toString().trim();
      const val = formatValueForDisplay(u.value);
      return val ? `${opt} ${val}` : opt;
    });
  }

  // (option,value)로 직접 내려주는 경우도 커버
  if (x.option !== undefined) {
    const opt = String(x.option ?? "").trim();
    const val = formatValueForDisplay(x.value);
    return [val ? `${opt} ${val}` : opt];
  }

  return [];
}

function buildUniqueFilterList() {
  const set = new Set();
  for (const c of COUNCILORS) {
    for (const u of c.unique || []) {
      const key = statKey(u);
      if (key) set.add(key);
    }
  }
  return Array.from(set).sort((a, b) => a.localeCompare(b, "ko"));
}
function buildRoleList() {
  const set = new Set();
  for (const c of COUNCILORS) {
    const r = String(c.role || "").trim();
    if (r) set.add(r);
  }
  return Array.from(set).sort((a, b) => a.localeCompare(b, "ko"));
}

function renderRoleSelect() {
  const sel = document.getElementById("roleSelect");
  if (!sel) return;

  const roles = buildRoleList();
  const current = state.role || "";

  sel.innerHTML =
    `<option value="">전체</option>` +
    roles.map((r) => {
      const v = escapeHtml(r);
      const selected = r === current ? "selected" : "";
      return `<option value="${v}" ${selected}>${v}</option>`;
    }).join("");
}

/* ---------- state ---------- */
const state = {
  nameQuery: "",
  optionFilterQuery: "",
  selectedKeys: new Set(),
  role: "", // ✅ 추가
};

/* ---------- IME safe binder ---------- */
function bindImeSafeInput(inputEl, onValue) {
  if (!inputEl) return;
  let composing = false;

  inputEl.addEventListener("compositionstart", () => (composing = true));
  inputEl.addEventListener("compositionend", (e) => {
    composing = false;
    onValue(e.target.value || "");
  });
  inputEl.addEventListener("input", (e) => {
    if (composing) return;
    onValue(e.target.value || "");
  });
}

/* ---------- chips ---------- */
function renderOptionFilterChips() {
  const wrap = document.getElementById("optionFilters");
  if (!wrap) return;

  const q = (state.optionFilterQuery || "").trim();
  if (!q) {
    wrap.innerHTML = "";
    wrap.style.display = "none";
    return;
  }

  const keys = buildUniqueFilterList();
  const filtered = keys.filter((k) => k.includes(q));

  if (filtered.length === 0) {
    wrap.innerHTML = "";
    wrap.style.display = "none";
    return;
  }

  wrap.style.display = "flex";
  wrap.innerHTML = filtered
    .map((text) => {
      const checked = state.selectedKeys.has(text) ? "checked" : "";
      return `
        <label class="artifact-check-item">
          <input type="checkbox" data-key="${escapeHtml(text)}" ${checked} />
          <span>${escapeHtml(text)}</span>
        </label>
      `;
    })
    .join("");

  wrap.querySelectorAll('input[type="checkbox"][data-key]').forEach((el) => {
    el.addEventListener("change", (e) => {
      const key = e.target.getAttribute("data-key");
      if (!key) return;
      if (e.target.checked) state.selectedKeys.add(key);
      else state.selectedKeys.delete(key);
      renderList();
    });
  });
}

/* ---------- filtering ---------- */
function passesFilters(item) {
  if (state.selectedKeys.size > 0) {
    const ok = (item.unique || []).some((u) => state.selectedKeys.has(statKey(u)));
    if (!ok) return false;
  }

  if (state.role) {
    if (String(item.role || "").trim() !== state.role) return false;
  }

  if (state.nameQuery) {
    const q = normalizeForSearch(state.nameQuery);
    const hay = normalizeForSearch(`${item.ko} ${item.en}`);
    if (!hay.includes(q)) return false;
  }

  return true;
}

/* ---------- render ---------- */
function renderList() {
  const list = document.getElementById("councilList");
  if (!list) return;

  const items = COUNCILORS.filter(passesFilters).map((c) => {
    const pairs = (c.unique || []).map(splitOptionAndValue);

    const ovRows = pairs
      .map((p) => {
        const opt = escapeHtml(p.opt || "");
        const val = escapeHtml(p.val || "");
        return `
          <div class="ov-row">
            <div class="ov-opt">${opt}</div>
            <div class="ov-val">${val}</div>
          </div>
        `;
      })
      .join("");

    const gradeText = String(c.grade || "");
    const gradeClass = getGradeClass(gradeText);

    return `
      <div class="council-item ${gradeClass}">
        <div class="council-name">${escapeHtml(c.ko)}</div>
        <div class="council-en">${escapeHtml(c.en)}</div>

        <div class="council-role center">${escapeHtml(c.role)}</div>
        <div class="council-kind center">${escapeHtml(c.kind)}</div>

        <div class="council-grade">
          <span class="council-badge ${gradeClass}">${escapeHtml(gradeText)}</span>
        </div>

        <div class="council-ov">
          <div class="ov-table">
            ${ovRows}
          </div>
        </div>

        <div class="council-val right"></div>
      </div>
    `;
  });

  list.innerHTML = items.length
    ? items.join("")
    : `<div class="artifact-empty">조건에 맞는 고문관이 없어.</div>`;
}

/* ---------- data load ---------- */
async function loadCouncilors() {
  const list = document.getElementById("councilList");
  if (list) list.innerHTML = `<div class="artifact-empty">데이터 불러오는 중...</div>`;

  try {
    const res = await fetch(`${DATA_API_URL}&_=${Date.now()}`, { cache: "no-store" });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);

    const data = await res.json();
    if (!Array.isArray(data)) throw new Error("JSON is not an array");

    // API 형태 가정:
    // [{ ko,en, role, kind, grade, unique:[{option,value}...] }]
    // 또는 "행 단위"로 [{ko,en, role, kind, grade, option, value}] 로 올 수도 있음
    // -> 행 단위면 같은 이름끼리 묶어서 unique 배열로 합침
    const byKey = new Map();

    for (const x of data) {
      const ko = x.ko ?? x.name ?? "";
      const en = x.en ?? "";
      const role = x.role ?? "";
      const kind = x.kind ?? x.type ?? "";
      const grade = x.grade ?? x.rank ?? "";
      const key = `${ko}||${en}||${role}||${kind}||${grade}`;

      const u = canonicalizeUniqueFromApi(x); // 배열 반환
      if (!byKey.has(key)) {
        byKey.set(key, { ko, en, role, kind, grade, unique: [] });
      }
      const obj = byKey.get(key);
      obj.unique.push(...u.filter(Boolean));
    }

    COUNCILORS = Array.from(byKey.values());

    renderRoleSelect();
    renderOptionFilterChips();
    renderList();
  } catch (err) {
    if (list) {
      list.innerHTML = `<div class="artifact-empty">데이터 로드 실패: ${escapeHtml(
        err.message || String(err)
      )}</div>`;
    }
  }
}

/* ---------- ui ---------- */
function bindUI() {
  const search = document.getElementById("councilSearch");
  const clear = document.getElementById("clearFilters");
  const oSearch = document.getElementById("optionFilterSearch");
  const roleSelect = document.getElementById("roleSelect");


  bindImeSafeInput(search, (v) => {
    state.nameQuery = v;
    renderList();
  });

  bindImeSafeInput(oSearch, (v) => {
    state.optionFilterQuery = v;
    renderOptionFilterChips();
  });

  if (roleSelect) {
  roleSelect.addEventListener("change", (e) => {
    state.role = e.target.value;
    renderList();
  });
}

  if (clear) {
    clear.addEventListener("click", () => {
      state.nameQuery = "";
      state.optionFilterQuery = "";
      state.selectedKeys.clear();
      state.role = "";

      if (search) search.value = "";
      if (oSearch) oSearch.value = "";
      if (roleSelect) roleSelect.value = "";

      renderOptionFilterChips();
      renderList();
    });
  }
}

document.addEventListener("DOMContentLoaded", () => {
  bindUI();
  loadCouncilors();
});
