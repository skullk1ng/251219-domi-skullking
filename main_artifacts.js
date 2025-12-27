"use strict";

/*
  규칙
  - 표에는 업그레이드 반영 수치만 표시
  - %가 있는 숫자: 기본 수치에 +9 퍼센트포인트
  - [도서관] 연구(고고학 위업) 체크 시: 위 결과에서 +1 퍼센트포인트
  - %가 없는 숫자(예: +1)는 변경하지 않음
*/

const TOKEN_ICON_SRC = "/image/icon/token.png";

/* Ctrl+F -> DATA_API_URL */
const DATA_API_URL =
  "https://script.google.com/macros/s/AKfycbwIDx-aPZ7Uy285yUHq2eDnjs5CzAwHZiauYrbghoirGTGhx0aaZsKbG8GJRp2yYbwMAw/exec?tab=Main";

let ARTIFACTS = [];

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

/* ✅ 퍼센트 업그레이드 규칙 */
function upgradePercentValue(n, isArchaeology) {
  const mag = Math.abs(n);
  const upgraded = mag + 9 + (isArchaeology ? 1 : 0);
  return n < 0 ? -upgraded : upgraded;
}

/* ✅ "옵션 +12%" 같은 문자열의 숫자만 업그레이드 */
function upgradeLine(line, isArchaeology) {
  const s = String(line).trim();

  // 마지막 숫자(정수/소수) + 선택적 % 를 "수치"로 인식
  // 예: "... +6%", "... -8%", "... +1", "... 1"
  const m = s.match(/([+-]?\s*\d+(?:\.\d+)?)(\s*%?)\s*$/);
  if (!m) return s;

  const rawNum = m[1].replace(/\s+/g, "");
  const hasPercent = (m[2] || "").includes("%");

  const n = Number(rawNum);
  if (!Number.isFinite(n)) return s;

  // ✅ %든 정수든 동일하게 +9, (도서관 체크 시) +1
  const add = 9 + (isArchaeology ? 1 : 0);
  const mag = Math.abs(n);
  const upgraded = mag + add;
  const signed = n < 0 ? -upgraded : upgraded;

  // 표시 포맷:
  // - 양수는 + 붙이기
  // - %면 % 유지
  // - 정수면 % 없이 숫자만
  const outNum = signed >= 0 ? `+${signed}` : String(signed);
  const out = hasPercent ? `${outNum}%` : outNum;

  // 기존 문장의 "마지막 수치" 부분만 교체
  return s.slice(0, m.index).trimEnd() + " " + out;
}

function statKey(line) {
  return String(line)
    .replace(/[-+]?\d+(\.\d+)?%?/g, "")
    .replace(/\s+/g, " ")
    .replace(/[()]/g, "")
    .trim();
}

function normalizeTrailingValueToPercent(line) {
  const s = String(line).trim();

  // 이미 %가 있으면 그대로
  if (/%\s*$/.test(s)) return s;

  // 끝에 숫자가 붙은 케이스: 0.12 / -0.1 같은 소수만 퍼센트로 변환
  const m = s.match(/([+-]?\d+(?:\.\d+)?)\s*$/);
  if (!m) return s;

  const n = Number(m[1]);
  if (!Number.isFinite(n)) return s;

  // 정수는 그대로(요구사항)
  if (Number.isInteger(n)) return s;

  // 소수면 퍼센트로(+12%)
  const pct = Math.round(n * 100);
  const pctText = pct >= 0 ? `+${pct}%` : `${pct}%`;

  return s.slice(0, m.index).trim() + " " + pctText;
}

/* (옵션명, 수치) 분리 */
function splitOptionAndValue(upgradedLine) {
  // ✅ 1단계: 0.12 / -0.1 같은 값을 +12% / -10%로 보정
  const s = normalizeTrailingValueToPercent(upgradedLine).trim();

  // ✅ 2단계: 뒤에 붙은 수치만 분리
  const m = s.match(/([+-]?\d+(?:\.\d+)?%?)\s*$/);
  if (!m) return { opt: s, val: "" };

  const val = m[1].replace(/\s+/g, "");
  const opt = s.slice(0, m.index).trim();

  return {
    opt: opt || s,
    val: opt ? val : "",
  };
}

function buildUniqueFilterList() {
  const set = new Set();
  for (const a of ARTIFACTS) {
    for (const u of a.unique || []) {
      const key = statKey(u);
      if (key) set.add(key);
    }
  }
  return Array.from(set).sort((a, b) => a.localeCompare(b, "ko"));
}

function isNumericPrice(p) {
  if (typeof p === "number" && Number.isFinite(p)) return true;
  if (typeof p === "string") return /^\s*\d+(\.\d+)?\s*$/.test(p);
  return false;
}

/* ✅ API value를 출력 규칙으로 변환
   - 0.12 / "0.12" -> "+12%"
   - -0.11 -> "-11%"
   - 정수는 정수 그대로 출력 (요구사항)
   - "12%" -> "+12%" (부호 보정)
*/
function formatValueForDisplay(raw) {
  if (raw === null || raw === undefined) return "";

  let s = String(raw).trim();
  if (!s) return "";

  if (/%/.test(s)) {
    const n = Number(s.replace("%", "").replace(/\s+/g, ""));
    if (!Number.isFinite(n)) return s;
    const rounded = Math.round(n);
    return rounded >= 0 ? `+${rounded}%` : `${rounded}%`;
  }

  const n = Number(s.replace(/\s+/g, ""));
  if (!Number.isFinite(n)) return s;

  if (Number.isInteger(n)) return String(n);

  const pct = Math.round(n * 100);
  return pct >= 0 ? `+${pct}%` : `${pct}%`;
}

/* ✅ API에서 (option,value)로 온 데이터를 "옵션 +12%" 형태로 변환 */
function canonicalizeUniqueFromApi(item) {
  if (Array.isArray(item.unique) && item.unique.length && typeof item.unique[0] === "string") {
    return item.unique.map((x) => String(x));
  }

  if (Array.isArray(item.unique) && item.unique.length && typeof item.unique[0] === "object") {
    return item.unique.map((x) => {
      const opt = (x.option ?? "").toString().trim();
      const val = formatValueForDisplay(x.value);
      return val ? `${opt} ${val}` : opt;
    });
  }

  return [];
}

/* ✅ 등급 -> 클래스 */
function getTypeClass(typeText) {
  const t = String(typeText || "");
  if (t.includes("신화")) return "is-myth";
  if (t.includes("전설")) return "is-legend";
  return "";
}

/* ---------- state ---------- */
const state = {
  nameQuery: "",
  archaeology: false,
  uniqueFilterQuery: "",
  selectedKeys: new Set(),
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
function renderUniqueFilterChips() {
  const wrap = document.getElementById("uniqueFilters");
  if (!wrap) return;

  const q = (state.uniqueFilterQuery || "").trim();
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
function passesFilters(artifact) {
  if (state.selectedKeys.size > 0) {
    const ok = (artifact.unique || []).some((u) => state.selectedKeys.has(statKey(u)));
    if (!ok) return false;
  }

  if (state.nameQuery) {
    const q = normalizeForSearch(state.nameQuery);
    const hay = normalizeForSearch(`${artifact.ko} ${artifact.en}`);
    if (!hay.includes(q)) return false;
  }

  return true;
}

/* ---------- render ---------- */
function renderList() {
  const list = document.getElementById("artifactList");
  if (!list) return;

  const items = ARTIFACTS.filter(passesFilters).map((a) => {
    // ✅ 업그레이드(+9/+1) 적용
    const upgradedLines = (a.unique || []).map((u) => upgradeLine(u, state.archaeology));
    const pairs = upgradedLines.map(splitOptionAndValue);

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

    const price = a.price;

    const priceHtml = isNumericPrice(price)
      ? `
        <div class="artifact-price">
          <span class="price-wrap">
            <img class="token-icon" src="${escapeHtml(TOKEN_ICON_SRC)}" alt="" />
            <span class="price-num">${escapeHtml(price)}</span>
          </span>
        </div>
      `
      : `
        <div class="artifact-price">
          <span class="price-text">${escapeHtml(price)}</span>
        </div>
      `;

    const typeText = String(a.type || "");
    const typeClass = getTypeClass(typeText);

    return `
      <div class="artifact-item ${typeClass}">
        <div class="artifact-name">${escapeHtml(a.ko)}</div>
        <div class="artifact-en">${escapeHtml(a.en)}</div>

        <div class="artifact-grade">
          <span class="artifact-badge ${typeClass}">${escapeHtml(typeText)}</span>
        </div>

        <div class="artifact-ov">
          <div class="ov-table">
            ${ovRows}
          </div>
        </div>

        ${priceHtml}
      </div>
    `;
  });

  list.innerHTML = items.length
    ? items.join("")
    : `<div class="artifact-empty">조건에 맞는 유물이 없어.</div>`;
}

/* ---------- data load ---------- */
async function loadArtifacts() {
  const list = document.getElementById("artifactList");
  if (list) list.innerHTML = `<div class="artifact-empty">데이터 불러오는 중...</div>`;

  try {
const res = await fetch(`${DATA_API_URL}&_=${Date.now()}`, { cache: "no-store" });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);

    const data = await res.json();
    if (!Array.isArray(data)) throw new Error("JSON is not an array");

    ARTIFACTS = data.map((x) => {
      const unique = canonicalizeUniqueFromApi(x);
      return {
        ko: x.ko ?? "",
        en: x.en ?? "",
        type: x.type ?? "",
        unique,
        price: x.price ?? "",
      };
    });

    renderUniqueFilterChips();
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
  const search = document.getElementById("artifactSearch");
  const archaeology = document.getElementById("archaeology");
  const clear = document.getElementById("clearFilters");
  const uSearch = document.getElementById("uniqueFilterSearch");

  bindImeSafeInput(search, (v) => {
    state.nameQuery = v;
    renderList();
  });

  bindImeSafeInput(uSearch, (v) => {
    state.uniqueFilterQuery = v;
    renderUniqueFilterChips();
  });

  if (archaeology) {
    archaeology.addEventListener("change", (e) => {
      state.archaeology = !!e.target.checked;
      renderList();
    });
  }

  if (clear) {
    clear.addEventListener("click", () => {
      state.nameQuery = "";
      state.archaeology = false;
      state.uniqueFilterQuery = "";
      state.selectedKeys.clear();

      if (search) search.value = "";
      if (archaeology) archaeology.checked = false;
      if (uSearch) uSearch.value = "";

      renderUniqueFilterChips();
      renderList();
    });
  }
}

document.addEventListener("DOMContentLoaded", () => {
  bindUI();
  loadArtifacts();
});
