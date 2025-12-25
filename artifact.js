"use strict";

/*
  규칙 (네 요구사항 기준)
  - 표에는 항상 업그레이드 반영 수치만 표시 (기본 수치 표기 제거)
  - %가 있는 숫자: 기본 수치에 +9 퍼센트포인트
    예) +9% -> +18%, -8% -> -17%
  - [도서관] 연구: 고고학 위업 체크 시: 위 결과에서 +1 퍼센트포인트
    예) 18% -> 19%, -17% -> -18%
  - %가 없는 숫자(예: +1)는 변경하지 않음
*/

const ARTIFACTS = [
  {
    ko: "줄리어스 시저 동상",
    en: "Statue of Julius Caesar",
    type: "전설",
    unique: [
      "침략 영웅 데미지 -8%",
      "침략 영웅 HP -8%",
      "영웅 데미지 +9%",
      "훈련소 병력 데미지 +8%",
      "침략 훈련소 병력 데미지 -9%",
    ],
    price: 300,
  },
  {
    ko: "레오니다스 흉상",
    en: "Bust of Leonidas",
    type: "전설",
    unique: [
      "용병 야영지 파괴 시 스파르타 병사 +1",
      "빠른 승리 제한 시간 +6%",
      "영웅 HP와 데미지 +6%",
      "바주카 데미지 +6%",
      "바주카 HP +6%",
    ],
    price: 300,
  },
  {
    ko: "자유의 종",
    en: "Liberty Bell",
    type: "전설",
    unique: [
      "원거리 보병 데미지 +8%",
      "원거리 보병 데미지 +8%",
      "비행장 병력 HP +7%",
      "적 방공 시설 데미지 -11%",
      "모든 적 방어 타워 데미지 -7%",
    ],
    price: 300,
  },
  {
    ko: "마오리족 전투 곤봉",
    en: "Maori War Club",
    type: "전설",
    unique: [
      "모든 방어 타워 HP 및 데미지 +3%",
      "수비병 소환 시간 -6%",
      "수비병 이동 속도 +3%",
      "침략 정찰 스캔 지속 시간 -7%",
      "영웅 공격 속도 +3%",
    ],
    price: 300,
  },
  {
    ko: "나폴레옹의 박스록 피스톨",
    en: "Napoleon’s Boxlock Pistol",
    type: "전설",
    unique: [
      "보급 차량 치유 +9%",
      "영웅 HP +7%",
      "중장갑 기병 HP +9%",
      "훈련소 병력 HP +6%",
      "전사 데미지 +7%",
    ],
    price: 300,
  },
  {
    ko: "나르메르 팔레트",
    en: "Narmer Palette",
    type: "전설",
    unique: [
      "침략 전투기 데미지 -6%",
      "방공 시설 데미지 +6%",
      "폭격기 HP +3%",
      "전투기 HP +6%",
      "바주카 HP +6%",
    ],
    price: 300,
  },
  {
    ko: "노든 폭격조준기",
    en: "Norden Bombsight",
    type: "전설",
    unique: [
      "APC 사망 시 해병 소환 +1",
      "연맹 병력 데미지 +8%",
      "수비병 소환 시간 -8%",
      "침략 전투기 데미지 -8%",
      "기관총 보병 데미지 +8%",
    ],
    price: 300,
  },
  {
    ko: "올멕 거대 두상",
    en: "Olmec Colossal Head",
    type: "전설",
    unique: [
      "집결 재사용 대기 시간 -11%",
      "집결 지속 시간 +11%",
      "적군 수비병 소환 시간 +6%",
      "전사 데미지 +8%",
      "전사 데미지 +8%",
    ],
    price: 300,
  },
  {
    ko: "휴이 무장 시스템",
    en: "Huey Weapon System",
    type: "전설",
    unique: [
      "공격 헬리콥터 데미지 +9%",
      "공격 헬리콥터 데미지 +9%",
      "공격 헬리콥터 HP +9%",
      "바주카 데미지 +9%",
      "모든 적 방어 타워 데미지 -6%",
    ],
    price: 300,
  },
  {
    ko: "환희의 검",
    en: "Sword of Joy",
    type: "전설",
    unique: [
      "공장 병력 데미지 +6%",
      "중전차 데미지 +6%",
      "폭격기 데미지 +6%",
      "영웅 데미지 +6%",
      "수비병 데미지 +6%",
    ],
    price: 300,
  },
  {
    ko: "소필로스 다이노스",
    en: "Sophilos Dinos",
    type: "전설",
    unique: [
      "토목공병 데미지 +9%",
      "게릴라 데미지 +6%",
      "게릴라 HP +8%",
      "유인용 전술 HP 증가 +6%",
      "적군 수비병 소환 시간 +6%",
    ],
    price: 300,
  },
  {
    ko: "슈퍼마린 스피트파이어 엔진",
    en: "Supermarine Spitfire Engine",
    type: "전설",
    unique: [
      "폭격기 데미지 +9%",
      "폭격기 HP +9%",
      "폭격기 HP +8%",
      "중전차 데미지 +9%",
      "전사 데미지 +9%",
    ],
    price: 300,
  },
  {
    ko: "손자병법",
    en: "Art of War",
    type: "전설",
    unique: [
      "중전차 HP +9%",
      "중전차 데미지 +9%",
      "침략 영웅 HP -9%",
      "침략 영웅 데미지 -9%",
      "영웅 HP와 데미지 +9%",
    ],
    price: 300,
  },
  {
    ko: "항공기 자이로 조준기",
    en: "Aircraft Gyro Gunsight",
    type: "전설",
    unique: [
      "폭격기 HP +6%",
      "폭격기 HP +6%",
      "정찰 스캔 지속 시간 증가 +3%",
      "바주카 공격 속도 증가 +3%",
      "빠른 승리 제한 시간 +6%",
    ],
    price: 300,
  },
  {
    ko: "람세스 2세의 아부 심벨",
    en: "Abu Simbel of Ramses II",
    type: "전설",
    unique: [
      "모든 방어 타워 HP +9%",
      "수비병 소환 시간 -9%",
      "침략 바주카 데미지 -7%",
      "침략 게릴라 데미지 -9%",
      "모든 방어 타워 데미지 +9%",
    ],
    price: 300,
  },
  {
    ko: "까마귀 딸랑이",
    en: "Raven Rattle",
    type: "전설",
    unique: [
      "전투기 HP +7%",
      "전사 데미지 +7%",
      "적 보루 데미지 -6%",
      "적 타워 데미지 -6%",
      "모든 적 방어 타워 데미지 -11%",
    ],
    price: 300,
  },
  {
    ko: "붉은 남작의 엔진",
    en: "Red Baron’s Engine",
    type: "전설",
    unique: [
      "전사 데미지 +6%",
      "폭격기 데미지 +6%",
      "중전차 데미지 +6%",
      "기관총 보병 데미지 +6%",
      "침략 전투기 HP -6%",
    ],
    price: 300,
  },
  {
    ko: "RQ-2 파이어니어",
    en: "RQ-2 Pioneer",
    type: "전설",
    unique: [
      "침략 폭격기 데미지 -8%",
      "침략 폭격기 데미지 -8%",
      "침략 폭격기 HP -7%",
      "방공 시설 HP +6%",
      "방공 시설 데미지 +6%",
    ],
    price: 300,
  },
  {
    ko: "사나다 유키무라의 투구",
    en: "Sanada Yukimura’s Helmet",
    type: "전설",
    unique: [
      "성이 파괴되면 검성 소환 +1",
      "영웅 HP +6%",
      "바주카 데미지 +6%",
      "전사 데미지 +8%",
      "게릴라 HP +8%",
    ],
    price: 300,
  },
  {
    ko: "6주년 기념식 식스슈터",
    en: "6th Anniversary Six-Shooter",
    type: "전설",
    unique: [
      "바주카 데미지 +9%",
      "바주카 데미지 +8%",
      "폭격기 HP +9%",
      "공격 헬리콥터 데미지 +9%",
      "침략 낙하산병 데미지 -9%",
    ],
    price: 300,
  },
  {
    ko: "웰로드 Mk II",
    en: "Welrod Mk II",
    type: "전설",
    unique: [
      "모든 적 방어 타워 HP -8%",
      "적군 수비병 소환 시간 +8%",
      "게릴라 데미지 +6%",
      "게릴라 HP +6%",
      "비행장 병력 데미지 +6%",
    ],
    price: 300,
  },
];

// ---------- util ----------
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

// %수치만 규칙 적용: base에 +9p, archaeology면 +1p
function upgradePercentValue(n, isArchaeology) {
  const mag = Math.abs(n);
  const upgraded = mag + 9 + (isArchaeology ? 1 : 0);
  return n < 0 ? -upgraded : upgraded;
}

function upgradeLine(line, isArchaeology) {
  const s = String(line);

  // % 수치가 있으면 숫자(들)를 +9p(+1p)로 변경
  if (/%/.test(s)) {
    return s.replace(/[-+]?\d+(\.\d+)?/g, (m) => {
      const n = Number(m);
      if (!Number.isFinite(n)) return m;
      return String(upgradePercentValue(n, isArchaeology));
    });
  }
  // %가 없는 수치는 변경하지 않음
  return s;
}

function buildUniqueFilterList() {
  const set = new Set();
  for (const a of ARTIFACTS) {
    for (const u of (a.unique || [])) {
      const key = statKey(u);
      if (key) set.add(key);
    }
  }
  return Array.from(set).sort((a, b) => a.localeCompare(b, "ko"));
}

// ---------- state ----------
const state = {
  query: "",
  onlyUnique: false,
  archaeology: false,
  uniqueFilterQuery: "",
  selectedKeys: new Set(),
};

// ---------- filter rendering (검색어 있을 때만 노출) ----------
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

  // ✅ 한국어 포함 검색이 잘 되게 “그대로 포함” 기준
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

      renderTable();
    });
  });
}

function passesFilters(artifact) {
  if (state.onlyUnique && (!artifact.unique || artifact.unique.length === 0)) return false;

  if (state.selectedKeys.size > 0) {
    const ok = (artifact.unique || []).some((u) => state.selectedKeys.has(statKey(u)));
    if (!ok) return false;
  }

  if (state.query) {
    const q = normalizeForSearch(state.query);

    // 검색도 업그레이드 반영 문자열 기준으로
    const upgradedUnique = (artifact.unique || [])
      .map((u) => upgradeLine(u, state.archaeology))
      .join(" ");

    const hay = normalizeForSearch(
      `${artifact.ko} ${artifact.en} ${artifact.type} ${upgradedUnique} ${artifact.price}`
    );

    if (!hay.includes(q)) return false;
  }

  return true;
}

// ---------- table ----------
function renderTable() {
  const tbody = document.getElementById("artifactTbody");
  if (!tbody) return;

  const rows = ARTIFACTS
    .filter(passesFilters)
    .map((a) => {
      const lines = (a.unique || [])
        .map((line) => `<li>${escapeHtml(upgradeLine(line, state.archaeology))}</li>`)
        .join("");

      return `
        <tr>
          <td class="artifact-name">${escapeHtml(a.ko)}</td>
          <td class="artifact-en">${escapeHtml(a.en)}</td>
          <td class="artifact-type">${escapeHtml(a.type)}</td>
          <td><ul class="artifact-unique">${lines}</ul></td>
          <td class="artifact-price">${escapeHtml(a.price)}</td>
        </tr>
      `;
    });

  tbody.innerHTML = rows.length
    ? rows.join("")
    : `<tr><td colspan="5" class="artifact-empty">조건에 맞는 유물이 없어.</td></tr>`;
}

// ---------- IME safe binder (한글 입력 안정) ----------
function bindImeSafeInput(inputEl, onValue) {
  if (!inputEl) return;

  let composing = false;

  inputEl.addEventListener("compositionstart", () => {
    composing = true;
  });

  inputEl.addEventListener("compositionend", (e) => {
    composing = false;
    onValue(e.target.value || "");
  });

  inputEl.addEventListener("input", (e) => {
    if (composing) return;
    onValue(e.target.value || "");
  });
}

// ---------- ui ----------
function bindUI() {
  const search = document.getElementById("artifactSearch");
  const onlyUnique = document.getElementById("onlyUnique");
  const archaeology = document.getElementById("archaeology");
  const clear = document.getElementById("clearFilters");
  const uSearch = document.getElementById("uniqueFilterSearch");

  bindImeSafeInput(search, (v) => {
    state.query = v;
    renderTable();
  });

  bindImeSafeInput(uSearch, (v) => {
    state.uniqueFilterQuery = v;
    renderUniqueFilterChips();
  });

  if (onlyUnique) {
    onlyUnique.addEventListener("change", (e) => {
      state.onlyUnique = !!e.target.checked;
      renderTable();
    });
  }

  if (archaeology) {
    archaeology.addEventListener("change", (e) => {
      state.archaeology = !!e.target.checked;
      renderTable();
    });
  }

  if (clear) {
    clear.addEventListener("click", () => {
      state.selectedKeys.clear();
      state.uniqueFilterQuery = "";
      if (uSearch) uSearch.value = "";
      renderUniqueFilterChips();
      renderTable();
    });
  }
}

document.addEventListener("DOMContentLoaded", () => {
  bindUI();
  renderUniqueFilterChips(); // 최초엔 숨김
  renderTable();
});
