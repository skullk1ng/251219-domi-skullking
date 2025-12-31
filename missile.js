/* =========================================================
   Dominations Calculator - 미사일 & 파괴전술 계산기
   (FIX: 정찰 스캔 데미지 곱연산 반영 + 체크박스 이동 + DMG 2줄 표기
         + [공격수 협의회] 입력을 스캔 박스 내부로 이동 + % 자동표기
         + (정찰기 스캔 + 파괴전술 DMG) 하단 "총 추가 수치" 미표기용(JS는 값만 계산)
         + ✅ FIX: 미사일격납고 HP 박스(노란/빨간) 덮어쓰기 + % 자동표기 + 계산반영 완전수정
   ========================================================= */

/* -------------------------------
   1) 데이터 테이블
------------------------------- */
const TACTIC_BASE_DMG_BY_LEVEL = {
  1: 4334, 2: 6535, 3: 6518, 4: 7178, 5: 9350, 6: 12155, 7: 24151, 8: 27071,
};

const MISSILE_BASE_HP_BY_AGE = {
  "디지털": 73800,
  "정보화": 94180,
  "드론": 106465,
  "자동화": 119750,
  "로봇공학": 139679,
};

const ALLIANCE_TACTIC_PCT_BY_LEVEL = { 1: 10, 2: 15, 3: 20, 4: 25, 5: 30, 6: 35, 7: 40, 8: 45 };
const EGYPT_HP_PCT_BY_LEVEL = { 1: 10, 2: 15, 3: 20, 4: 25, 5: 30, 6: 35, 7: 40, 8: 45 };

const ALLIANCE_EXTRA_OPTIONS = [
  { key: "lib", name: "[도서관] 연구:연맹 병력", pct: 10 },
  { key: "uni", name: "[유니버시티] 몬테수마 황제", pct: 30 },
  { key: "law", name: "[의회] 연맹훈련", pct: 30 },
];

const SCOUT_PLANE_SCAN_OPTIONS = [
  { key: "scout_mk1_digital",  age: "디지털", name: "정찰기 Mk 1",  pct: 230 },
  { key: "scout_mk2_digital",  age: "디지털", name: "정찰기 Mk 2",  pct: 232 },
  { key: "scout_mk3_digital",  age: "디지털", name: "정찰기 Mk 3",  pct: 234 },
  { key: "scout_mk4_digital",  age: "디지털", name: "정찰기 Mk 4",  pct: 236 },
  { key: "scout_mk5_digital",  age: "디지털", name: "정찰기 Mk 5",  pct: 238 },
  { key: "scout_mk6_digital",  age: "디지털", name: "정찰기 Mk 6",  pct: 240 },

  { key: "supersonic_mk1_info", age: "정보화", name: "초음속 정찰기 Mk 1", pct: 240 },
  { key: "supersonic_mk2_info", age: "정보화", name: "초음속 정찰기 Mk 2", pct: 242 },
  { key: "supersonic_mk3_info", age: "정보화", name: "초음속 정찰기 Mk 3", pct: 244 },
  { key: "supersonic_mk4_info", age: "정보화", name: "초음속 정찰기 Mk 4", pct: 246 },
  { key: "supersonic_mk5_info", age: "정보화", name: "초음속 정찰기 Mk 5", pct: 248 },
  { key: "supersonic_mk6_info", age: "정보화", name: "초음속 정찰기 Mk 6", pct: 250 },

  { key: "spearhead_mk1_drone", age: "드론", name: "선봉 정찰기 Mk 1", pct: 250 },
  { key: "spearhead_mk2_drone", age: "드론", name: "선봉 정찰기 Mk 2", pct: 250 },
  { key: "spearhead_mk3_drone", age: "드론", name: "선봉 정찰기 Mk 3", pct: 250 },
  { key: "spearhead_mk4_drone", age: "드론", name: "선봉 정찰기 Mk 4", pct: 250 },
  { key: "spearhead_mk5_drone", age: "드론", name: "선봉 정찰기 Mk 5", pct: 250 },
  { key: "spearhead_mk6_drone", age: "드론", name: "선봉 정찰기 Mk 6", pct: 250 },

  { key: "captains_mk1_auto", age: "자동화", name: "캡틴스 정찰기 Mk 1", pct: 250 },
  { key: "captains_mk2_auto", age: "자동화", name: "캡틴스 정찰기 Mk 2", pct: 250 },
  { key: "captains_mk3_auto", age: "자동화", name: "캡틴스 정찰기 Mk 3", pct: 250 },
  { key: "captains_mk4_auto", age: "자동화", name: "캡틴스 정찰기 Mk 4", pct: 250 },
  { key: "captains_mk5_auto", age: "자동화", name: "캡틴스 정찰기 Mk 5", pct: 250 },
  { key: "captains_mk6_auto", age: "자동화", name: "캡틴스 정찰기 Mk 6", pct: 250 },

  { key: "majors_mk1_robot",  age: "로봇", name: "소령 정찰기 Mk 1",  pct: 252 },
  { key: "majors_mk2_robot",  age: "로봇", name: "소령 정찰기 Mk 2",  pct: 252 },
  { key: "majors_mk3_robot",  age: "로봇", name: "소령 정찰기 Mk 3",  pct: 252 },
  { key: "majors_mk4_robot",  age: "로봇", name: "소령 정찰기 Mk 4",  pct: 252 },
  { key: "majors_mk5_robot",  age: "로봇", name: "소령 정찰기 Mk 5",  pct: 252 },
  { key: "majors_mk6_robot",  age: "로봇", name: "소령 정찰기 Mk 6",  pct: 252 },
  { key: "majors_mk7_robot",  age: "로봇", name: "소령 정찰기 Mk 7",  pct: 252 },
  { key: "majors_mk8_robot",  age: "로봇", name: "소령 정찰기 Mk 8",  pct: 252 },
  { key: "majors_mk9_robot",  age: "로봇", name: "소령 정찰기 Mk 9",  pct: 252 },
  { key: "majors_mk10_robot", age: "로봇", name: "소령 정찰기 Mk 10", pct: 252 },
];

const SCOUT_PLANE_SCAN_MAP = Object.fromEntries(SCOUT_PLANE_SCAN_OPTIONS.map(o => [o.key, o]));

const GUILD_LEVEL_HP_PARTS = [
  { key: "g2",  label: "길드 레벨 2 (HP +10%)",  pct: 10 },
  { key: "g13", label: "길드 레벨 13 (HP +5%)", pct: 5 },
  { key: "g21", label: "길드 레벨 21 (HP +5%)", pct: 5 },
];

/* -------------------------------
   2) 보너스 정의(id 기반)
   ✅ FIX: hpCouncilRelicMount에 따로 보여줄 3개는 리스트에서 숨김
------------------------------- */
const BONUS_DEFS = {
  hp_lib_rocket:   { name: "[도서관] 연구:로켓공학", pctDefault: 0, hideInList: true },
  hp_lib_guided:   { name: "[도서관] 연구:유도미사일", pctDefault: 0, hideInList: true },
  hp_law_overwhelm:{ name: "[의회] 압도적인 사격", pctDefault: 0, hideInList: true },

  // ✅ HP 노란/빨간 3개: 리스트 숨김 + hpCouncilRelicMount에서 % 자동 처리
  hp_def_council_tower: { name: "[수비수 협의회] 모든 방어타워 HP", pctDefault: 0, lockName: true, color: "#facc15", hideInList: true },
  hp_def_relic_tower:   { name: "[수비수 유물] 모든 방어타워 HP", pctDefault: 0, lockName: true, color: "#facc15", hideInList: true },

  hp_att_relic_enemy_tower: {
    name: "[공격수 유물] 모든 적 방어타워 -HP",
    pctDefault: 0,
    lockName: true,
    color: "#ef4444",
    enforceNegative: true,
    min: -85,
    max: 0,
    hideInList: true,
  },

  hp_auto_egypt: { name: "[AUTO] 연맹:이집트", pctDefault: 0, hideInList: true, lockName: true, color: "#e5e7eb" },
  hp_auto_guild: { name: "[AUTO] 길드 레벨",   pctDefault: 0, hideInList: true, lockName: true, color: "#e5e7eb" },

  dmg_auto_mongol: { name: "[AUTO] 연맹:몽골", pctDefault: 0, hideInList: true, lockName: true, color: "#e5e7eb" },

  dmg_lib_tactic:     { name: "[도서관] 연구:전술", pctDefault: 0, hideInList: true },
  dmg_uni_suleiman:   { name: "[유니버시티] 쉘레이만 대제: 파괴 데미지", pctDefault: 0, hideInList: true },

  // ✅ 아래 2개는 "정찰 스캔 데미지 효과" 쪽에서 더해짐
  dmg_lib_scout:      { name: "[도서관] 연구:정찰 항공기", pctDefault: 0, hideInList: true },
  dmg_uni_sunja:      { name: "[유니버시티] 손자: 정찰기 스캔 데미지 보너스", pctDefault: 0, hideInList: true },

  // ✅ [공격수 협의회] 입력은 스캔 박스 내부 입력칸으로 처리 → 리스트에서는 숨김
  dmg_att_council_scan: { name: "[공격수 협의회] 정찰 스캔 데미지 보너스", pctDefault: 0, hideInList: true, lockName: true, color: "#facc15" },

  // ✅ 정찰기 기본 스캔% (예: 252%)도 스캔 쪽에서 곱해짐
  dmg_auto_scoutscan: { name: "[시대 풀업 기준] 정찰기 기본 스캔 데미지 보너스", pctDefault: 0, hideInList: true, lockName: true, color: "#e5e7eb" },
};

const DEFAULT_HP_BONUS_IDS = [
  "hp_lib_rocket","hp_lib_guided","hp_law_overwhelm",
  "hp_def_council_tower","hp_def_relic_tower","hp_att_relic_enemy_tower",
  "hp_auto_egypt","hp_auto_guild",
];

const DEFAULT_DMG_BONUS_IDS = [
  "dmg_auto_mongol",
  "dmg_lib_tactic",
  "dmg_uni_suleiman",

  // 스캔 관련(별도 계산)
  "dmg_att_council_scan",
  "dmg_lib_scout",
  "dmg_uni_sunja",
  "dmg_auto_scoutscan",
];

/* -------------------------------
   3) 유틸
------------------------------- */
const $ = (id) => document.getElementById(id);

function safeNum(v) {
  const n = Number(String(v ?? "").replace(/,/g, "").replace(/%/g, ""));
  return Number.isFinite(n) ? n : 0;
}
function fmtInt(n) {
  if (!Number.isFinite(n)) return "-";
  return Math.round(n).toLocaleString("ko-KR");
}
function fmtPctInt(n) {
  if (!Number.isFinite(n)) return "-";
  return `${Math.round(n)}%`;
}

function forceTextColor(el, color) {
  if (!el) return;
  el.style.setProperty("color", color, "important");
  el.style.setProperty("-webkit-text-fill-color", color, "important");
  el.style.setProperty("opacity", "1", "important");
}
function lockNameOnly(nameEl) {
  if (!nameEl) return;
  nameEl.readOnly = true;
  nameEl.style.pointerEvents = "none";
  nameEl.tabIndex = -1;
}

function normalizePctGeneral(raw) {
  if (raw === "-") return { typingDash: true, valueStr: "-" };
  let num = Number(raw);
  if (Number.isNaN(num)) num = 0;
  if (num < 0) num = 0;
  if (num > 999) num = 999;
  return { typingDash: false, valueStr: String(num) };
}

function normalizePctNegativeOnly(raw, min, max) {
  if (raw === "-") return { typingDash: true, valueStr: "-" };
  let num = Number(raw);
  if (Number.isNaN(num)) num = 0;

  if (num !== 0) num = -Math.abs(num);
  if (num < min) num = min;
  if (num > max) num = max;

  return { typingDash: false, valueStr: String(num) };
}

function enableCommaFormatting(inputEl, onBlurCommit) {
  if (!inputEl) return;
  if (inputEl.dataset.boundComma === "1") return;
  inputEl.dataset.boundComma = "1";

  inputEl.addEventListener("focus", () => {
    inputEl.value = String(inputEl.value ?? "").replace(/,/g, "");
    setTimeout(() => { try { inputEl.select(); } catch {} }, 0);
  });

  inputEl.addEventListener("keydown", (e) => {
    if (e.key === "Enter") { e.preventDefault(); inputEl.blur(); }
  });

  inputEl.addEventListener("input", () => {
    inputEl.value = String(inputEl.value ?? "").replace(/[^\d]/g, "");
  });

  inputEl.addEventListener("blur", () => {
    const raw = String(inputEl.value ?? "").replace(/,/g, "");
    inputEl.value = raw === "" ? "0" : Number(raw).toLocaleString("ko-KR");
    onBlurCommit?.();
  });
}

function makeUserBonusId(prefix) {
  return `${prefix}_user_${Date.now()}_${Math.random().toString(16).slice(2)}`;
}

/* ✅ % 자동표기 + 포커스시 전체선택(덮어쓰기) */
function enablePctSuffixInput(inputEl, onCommit, min = -999, max = 999) {
  if (!inputEl) return;
  if (inputEl.dataset.boundPctSuf === "1") return;
  inputEl.dataset.boundPctSuf = "1";

  inputEl.addEventListener("focus", () => {
    inputEl.value = String(inputEl.value ?? "").replace(/%/g, "");
    setTimeout(() => { try { inputEl.select(); } catch {} }, 0);
  });

  inputEl.addEventListener("keydown", (e) => {
    if (e.key === "Enter") { e.preventDefault(); inputEl.blur(); }
  });

  inputEl.addEventListener("input", () => {
    inputEl.value = String(inputEl.value ?? "").replace(/[^\d\-]/g, "");
    onCommit?.();
  });

  inputEl.addEventListener("blur", () => {
    let raw = String(inputEl.value ?? "").replace(/[^\d\-]/g, "");
    if (raw === "" || raw === "-") raw = "0";

    let n = Number(raw);
    if (!Number.isFinite(n)) n = 0;

    n = Math.trunc(n);
    if (n < min) n = min;
    if (n > max) n = max;

    inputEl.value = `${n}%`;
    onCommit?.();
  });

  const initRaw = String(inputEl.value ?? "").replace(/[^\d\-]/g, "") || "0";
  const initNum = Number(initRaw);
  inputEl.value = `${Number.isFinite(initNum) ? Math.trunc(initNum) : 0}%`;
}

/* ✅ 음수 전용(양수 입력해도 음수로) + % 자동표기 + 덮어쓰기 */
function enableNegPctSuffixRange(inputEl, minNeg, maxNeg, onCommit) {
  if (!inputEl) return;
  if (inputEl.dataset.boundNegPct === "1") return;
  inputEl.dataset.boundNegPct = "1";

  inputEl.addEventListener("focus", () => {
    inputEl.value = String(inputEl.value ?? "").replace(/%/g, "");
    setTimeout(() => { try { inputEl.select(); } catch {} }, 0);
  });

  inputEl.addEventListener("keydown", (e) => {
    if (e.key === "Enter") { e.preventDefault(); inputEl.blur(); }
  });

  inputEl.addEventListener("input", () => {
    inputEl.value = String(inputEl.value ?? "").replace(/[^\d\-]/g, "");
    onCommit?.();
  });

  inputEl.addEventListener("blur", () => {
    let raw = String(inputEl.value ?? "").replace(/[^\d\-]/g, "");
    if (raw === "" || raw === "-") raw = "0";

    let n = Number(raw);
    if (!Number.isFinite(n)) n = 0;

    if (n !== 0) n = -Math.abs(n);
    if (n < minNeg) n = minNeg;
    if (n > maxNeg) n = maxNeg;

    inputEl.value = `${Math.trunc(n)}%`;
    onCommit?.();
  });

  const initRaw = String(inputEl.value ?? "").replace(/[^\d\-]/g, "") || "0";
  let initNum = Number(initRaw);
  if (!Number.isFinite(initNum)) initNum = 0;
  if (initNum !== 0) initNum = -Math.abs(initNum);
  if (initNum < minNeg) initNum = minNeg;
  if (initNum > maxNeg) initNum = maxNeg;
  inputEl.value = `${Math.trunc(initNum)}%`;
}

/* ✅ [공격수 협의회] 정찰 스캔 입력: 10 -> 10% 자동 표기 */
function enablePercentFormatting(inputEl, onCommit) {
  if (!inputEl) return;
  if (inputEl.dataset.boundPct === "1") return;
  inputEl.dataset.boundPct = "1";

  inputEl.addEventListener("focus", () => {
    inputEl.value = String(inputEl.value ?? "").replace(/%/g, "");
    setTimeout(() => { try { inputEl.select(); } catch {} }, 0);
  });

  inputEl.addEventListener("keydown", (e) => {
    if (e.key === "Enter") { e.preventDefault(); inputEl.blur(); }
  });

  inputEl.addEventListener("input", () => {
    const raw = String(inputEl.value ?? "").replace(/[^\d]/g, "");
    const norm = normalizePctGeneral(raw);
    inputEl.value = norm.valueStr;
    onCommit?.();
  });

  inputEl.addEventListener("blur", () => {
    const raw = String(inputEl.value ?? "").replace(/[^\d]/g, "");
    const norm = normalizePctGeneral(raw);
    const finalStr = norm.typingDash ? "0" : norm.valueStr;
    inputEl.value = `${finalStr}%`;
    onCommit?.();
  });

  const initRaw = String(inputEl.value ?? "").replace(/[^\d]/g, "");
  const initNorm = normalizePctGeneral(initRaw);
  const initStr = initNorm.typingDash ? "0" : initNorm.valueStr;
  inputEl.value = `${initStr}%`;
}

/* -------------------------------
   4) 상태
------------------------------- */
function makeDefaultBonuses(ids) {
  return ids.map(id => ({
    id,
    name: BONUS_DEFS[id]?.name ?? id,
    pct: String(BONUS_DEFS[id]?.pctDefault ?? 0),
    userAdded: false,
  }));
}

let hpBonuses = makeDefaultBonuses(DEFAULT_HP_BONUS_IDS);
let dmgBonuses = makeDefaultBonuses(DEFAULT_DMG_BONUS_IDS);

/* -------------------------------
   5) recalc 스케줄러
------------------------------- */
let _rafPending = false;
let _needRerenderBonuses = true;

function scheduleRecalc(rerenderBonuses) {
  if (rerenderBonuses) _needRerenderBonuses = true;
  if (_rafPending) return;

  _rafPending = true;
  requestAnimationFrame(() => {
    _rafPending = false;
    const doRerender = _needRerenderBonuses;
    _needRerenderBonuses = false;
    recalc(doRerender);
  });
}

/* -------------------------------
   6) 보너스 렌더
------------------------------- */
function renderBonusList(containerEl, bonuses, onChange) {
  if (!containerEl) return;
  containerEl.innerHTML = "";

  let insertedTowerHint = false;

  bonuses.forEach((b, idx) => {
    const def = BONUS_DEFS[b.id];
    if (def?.hideInList) return;

    const row = document.createElement("div");
    row.className = "bonus-item";

    const name = document.createElement("input");
    name.type = "text";
    name.className = "input";
    name.value = b.name;
    name.placeholder = "항목명";

    const pct = document.createElement("input");
    pct.type = "text";
    pct.className = "input";
    pct.value = String(b.pct ?? "0");
    pct.inputMode = (def?.enforceNegative) ? "text" : "numeric";
    pct.placeholder = "%";
    pct.maxLength = 6;
    pct.setAttribute("autocomplete", "off");

    if (def?.lockName) lockNameOnly(name);
    if (def?.color) {
      forceTextColor(name, def.color);
      forceTextColor(pct, def.color);
    }

    row.appendChild(name);
    row.appendChild(pct);

    name.addEventListener("input", () => {
      bonuses[idx].name = name.value;
      onChange(false);
    });

    pct.addEventListener("input", () => {
      const rawFiltered = String(pct.value ?? "").replace(/[^0-9\-]/g, "");
      const norm = def?.enforceNegative
        ? normalizePctNegativeOnly(rawFiltered, def.min ?? -85, def.max ?? 0)
        : normalizePctGeneral(rawFiltered);

      pct.value = norm.valueStr;
      bonuses[idx].pct = norm.valueStr;
      onChange(false);
    });

    pct.addEventListener("blur", () => {
      const rawFiltered = String(pct.value ?? "").replace(/[^0-9\-]/g, "");
      const norm = def?.enforceNegative
        ? normalizePctNegativeOnly(rawFiltered, def.min ?? -85, def.max ?? 0)
        : normalizePctGeneral(rawFiltered);

      pct.value = norm.typingDash ? "0" : norm.valueStr;
      bonuses[idx].pct = norm.typingDash ? "0" : norm.valueStr;
      onChange(false);
    });

    if (b.userAdded === true) {
      const del = document.createElement("button");
      del.className = "icon-btn";
      del.type = "button";
      del.textContent = "×";
      del.title = "삭제";
      del.addEventListener("click", () => {
        bonuses.splice(idx, 1);
        onChange(true);
      });
      row.appendChild(del);
    }

    containerEl.appendChild(row);

    if (!insertedTowerHint && b.id === "hp_def_relic_tower") {
      const hint = document.createElement("div");
      hint.className = "hint tower-hint";
      hint.textContent = "↑모든 방어 타워 HP에는 미사일 격납고 HP 옵션도 포함하여 입력↑";
      containerEl.appendChild(hint);
      insertedTowerHint = true;
    }
  });
}

function sumBonusPct(bonuses) {
  return bonuses.reduce((acc, b) => acc + safeNum(b.pct), 0);
}

function sumBonusPctExcept(bonuses, excludeIds) {
  const ex = new Set(excludeIds || []);
  return bonuses.reduce((acc, b) => (ex.has(b.id) ? acc : acc + safeNum(b.pct)), 0);
}

function getBonusPctById(bonuses, id) {
  const found = bonuses.find(x => x.id === id);
  return found ? safeNum(found.pct) : 0;
}

/* -------------------------------
   7) Select 옵션 + 참고표
------------------------------- */
function initSelectOptions() {
  const ageSel = $("enemyAgeHp");
  if (ageSel) {
    ageSel.innerHTML = "";
    ageSel.appendChild(new Option("— 선택 또는 직접 입력 —", ""));
    Object.keys(MISSILE_BASE_HP_BY_AGE).forEach((age) => ageSel.appendChild(new Option(age, age)));
    ageSel.value = "";
  }

  const levelSel = $("tacticLevel");
  if (levelSel) {
    levelSel.innerHTML = "";
    levelSel.appendChild(new Option("— 선택 안함 —", ""));
    Object.keys(TACTIC_BASE_DMG_BY_LEVEL).forEach((lvl) => levelSel.appendChild(new Option(`레벨 ${lvl}`, lvl)));
    levelSel.value = "";
  }
}

function renderReferenceTables() {
  const aEl = $("tableAdvisorsHp");
  if (aEl) {
    aEl.textContent = [
      "로버트 더 브루스 +6%",
      "선덕여왕 +8%",
      "도모에 고젠 +40%",
      "마리 퀴리 +10%",
      "미야모토 무사시 +6%",
      "부디카 +6%",
    ].join("\n");
  }

  const sEl = $("tableAdvisorsScanDmg");
  if (sEl) {
    sEl.textContent = [
      "새뮤얼 모스 +10%",
      "알프레드 노벨 +10%",
      "조지 워싱턴 +10%",
    ].join("\n");
  }
}

/* -------------------------------
   8) AUTO 박스들
------------------------------- */
const FIXED_HP_CHECK_ITEMS = [
  { id: "hp_lib_rocket",    pct: 10 },
  { id: "hp_lib_guided",    pct: 5 },
  { id: "hp_law_overwhelm", pct: 5 },
];

const FIXED_DMG_CHECK_ITEMS = [
  { id: "dmg_lib_tactic",   pct: 10 },
  { id: "dmg_uni_suleiman", pct: 10 },
];

const FIXED_SCAN_CHECK_ITEMS = [
  { id: "dmg_lib_scout", pct: 10, label: "[도서관] 연구:정찰 항공기 (+10%)" },
  { id: "dmg_uni_sunja", pct: 20, label: "[유니버시티] 손자: 정찰기 스캔 데미지 보너스 (+20%)" },
];

function findBonusIndex(list, id) {
  return list.findIndex(b => b.id === id);
}

/* ✅ FIX: HP 노란/빨간 입력 박스 mount + 포맷 적용 */
function mountHpCouncilRelicRows() {
  const mount = $("hpCouncilRelicMount");
  if (!mount) return;
  if (mount.dataset.mounted === "1") return;
  mount.dataset.mounted = "1";

  mount.innerHTML = `
    <div class="hp-rows">
      <div class="hp-rowbox hp-yellow">
        <div class="hp-rowbox-left">[수비수 협의회] 미사일격납고 HP</div>
        <input id="hp_def_council_tower" class="hp-rowbox-right" value="0%" />
      </div>

      <div class="hp-rowbox hp-yellow">
        <div class="hp-rowbox-left">[수비수 유물] 미사일격납고 HP</div>
        <input id="hp_def_relic_tower" class="hp-rowbox-right" value="0%" />
      </div>

      <div class="hp-rowbox hp-red">
        <div class="hp-rowbox-left">[공격수 유물] 모든 적 방어타워 -HP</div>
        <input id="hp_att_relic_enemy_tower" class="hp-rowbox-right" value="0%" />
      </div>

      <div class="hp-rowbox-subdesc">[공격수 유물 허용 범위: 0 ~ -85]</div>
    </div>
  `;

  // 노란 2개: 일반 % + 덮어쓰기
  enablePctSuffixInput($("hp_def_council_tower"), () => scheduleRecalc(false), -999, 999);
  enablePctSuffixInput($("hp_def_relic_tower"),   () => scheduleRecalc(false), -999, 999);

  // 빨간 1개: 음수 강제 + 범위 0 ~ -85
  enableNegPctSuffixRange($("hp_att_relic_enemy_tower"), -85, 0, () => scheduleRecalc(false));
}

function mountHpAutoBoxes() {
  const mount = $("hpAutoMount");
  if (!mount) return;
  if (mount.dataset.mounted === "1") return;
  mount.dataset.mounted = "1";

  mount.innerHTML = `
  <div class="auto-box all-research-box" id="allHpResearchBox">
    <div class="auto-checks">
      <label class="check-item">
        <input type="checkbox" id="allHpResearchApply" />
        <span>모든 연구 완료 (일괄 적용)</span>
      </label>
    </div>
  </div>

  <div class="auto-box" id="fixedHpBox">
    <div class="auto-title">[AUTO] 도서관/의회 HP+</div>
    <div class="auto-checks">
      ${FIXED_HP_CHECK_ITEMS.map(it => `
        <label class="check-item">
          <input type="checkbox" id="fixedhp_${it.id}" />
          <span>${BONUS_DEFS[it.id].name} (+${it.pct}%)</span>
        </label>
      `).join("")}
    </div>
    <div class="auto-sum">
      <span>합계</span>
      <b id="fixedHpAutoOut">0%</b>
    </div>
  </div>

  <div class="auto-box" id="egyptBox">
    <div class="auto-title">[AUTO] 연맹: 이집트 HP+</div>
    <div class="auto-checks">
      <div>
        <label class="label">이집트 레벨</label>
        <select id="egyptLevel" class="input"></select>
      </div>
      ${ALLIANCE_EXTRA_OPTIONS.map(o => `
        <label class="check-item">
          <input type="checkbox" id="egypt_${o.key}" />
          <span>${o.name}</span>
        </label>
      `).join("")}
    </div>
    <div class="auto-sum">
      <span>합계</span>
      <b id="egyptAutoOut">0%</b>
    </div>
  </div>

  <div class="auto-box" id="guildBox">
    <div class="auto-title">[AUTO] 길드 레벨 HP+</div>
    <div class="auto-sub">달성한 길드레벨 모두 체크 (예시: 길드레벨 25 → 3개 모두 체크)</div>
    <div class="auto-checks">
      ${GUILD_LEVEL_HP_PARTS.map(p => `
        <label class="check-item">
          <input type="checkbox" id="guild_${p.key}" />
          <span>${p.label}</span>
        </label>
      `).join("")}
    </div>
    <div class="auto-sum">
      <span>합계</span>
      <b id="guildAutoOut">0%</b>
    </div>
  </div>
  `;

  const sel = $("egyptLevel");
  if (sel) {
    sel.innerHTML = "";
    sel.appendChild(new Option("적용 안함 (0%)", "0"));
    Object.keys(EGYPT_HP_PCT_BY_LEVEL).forEach((lvl) => {
      sel.appendChild(new Option(`레벨 ${lvl}`, String(lvl)));
    });
    sel.value = "0";
  }

  FIXED_HP_CHECK_ITEMS.forEach(it => $(`fixedhp_${it.id}`)?.addEventListener("change", applyFixedHpToBonuses));
  $("egyptLevel")?.addEventListener("change", applyEgyptAutoToHpBonus);
  ALLIANCE_EXTRA_OPTIONS.forEach(o => $(`egypt_${o.key}`)?.addEventListener("change", applyEgyptAutoToHpBonus));
  GUILD_LEVEL_HP_PARTS.forEach(p => $(`guild_${p.key}`)?.addEventListener("change", applyGuildAutoToHpBonus));

  $("allHpResearchApply")?.addEventListener("change", (e) => {
    const on = !!e.target.checked;

    FIXED_HP_CHECK_ITEMS.forEach(it => { const cb = $(`fixedhp_${it.id}`); if (cb) cb.checked = on; });

    const egyptLevel = $("egyptLevel");
    if (egyptLevel) egyptLevel.value = on ? "8" : "0";
    ALLIANCE_EXTRA_OPTIONS.forEach(o => { const cb = $(`egypt_${o.key}`); if (cb) cb.checked = on; });

    GUILD_LEVEL_HP_PARTS.forEach(p => { const cb = $(`guild_${p.key}`); if (cb) cb.checked = on; });

    applyFixedHpToBonuses();
    applyEgyptAutoToHpBonus();
    applyGuildAutoToHpBonus();
  });

  applyFixedHpToBonuses();
  applyEgyptAutoToHpBonus();
  applyGuildAutoToHpBonus();
}

function mountDmgAutoBoxes() {
  const mount = $("dmgAutoMount");
  if (!mount) return;
  if (mount.dataset.mounted === "1") return;
  mount.dataset.mounted = "1";

  mount.innerHTML = `
    <div class="auto-box all-research-box" id="allDmgResearchBox">
      <div class="auto-checks">
        <label class="check-item">
          <input type="checkbox" id="allDmgResearchApply" />
          <span>모든 연구 완료 (일괄 적용)</span>
        </label>
      </div>
    </div>

    <div class="auto-box" id="fixedDmgBox">
      <div class="auto-title">[AUTO] 도서관/유니버시티 DMG+</div>
      <div class="auto-checks">
        ${FIXED_DMG_CHECK_ITEMS.map(it => `
          <label class="check-item">
            <input type="checkbox" id="fixeddmg_${it.id}" />
            <span>${BONUS_DEFS[it.id].name} (+${it.pct}%)</span>
          </label>
        `).join("")}
      </div>
      <div class="auto-sum">
        <span>합계</span>
        <b id="fixedDmgAutoOut">0%</b>
      </div>
    </div>

    <div class="auto-box" id="mongolBox">
      <div class="auto-title">[AUTO] 연맹: 몽골 DMG+</div>
      <div class="auto-checks">
        <div>
          <label class="label">연맹 레벨</label>
          <select id="mongolLevel" class="input"></select>
        </div>
        ${ALLIANCE_EXTRA_OPTIONS.map(o => `
          <label class="check-item">
            <input type="checkbox" id="mongol_${o.key}" />
            <span>${o.name}</span>
          </label>
        `).join("")}
      </div>
      <div class="auto-sum">
        <span>합계</span>
        <b id="mongolAutoOut">0%</b>
      </div>
    </div>

    <div class="auto-box" id="scoutBox">
      <div class="auto-title">[AUTO] 정찰기 기본 스캔 데미지</div>
      <div>
        <label class="label">정찰기 선택</label>
        <select id="scoutPlane" class="input"></select>
      </div>

      <div class="auto-checks" style="margin-top:10px;">
        ${FIXED_SCAN_CHECK_ITEMS.map(it => `
          <label class="check-item">
            <input type="checkbox" id="scancheck_${it.id}" />
            <span>${it.label}</span>
          </label>
        `).join("")}
      </div>

      <div class="hp-rows" style="margin-top:12px;">
        <div class="hp-rowbox hp-yellow">
          <div class="hp-rowbox-left">[공격수 협의회] 정찰 스캔 데미지 보너스</div>
          <input id="councilScanInput" class="hp-rowbox-right" type="text" inputmode="numeric" autocomplete="off" value="0%" />
        </div>
      </div>

      <div class="auto-sum" style="margin-top:12px;">
        <span>합계</span>
        <b id="scoutAutoOut">0%</b>
      </div>
    </div>
  `;

  const mongolSel = $("mongolLevel");
  if (mongolSel) {
    mongolSel.innerHTML = "";
    mongolSel.appendChild(new Option("적용 안함 (0%)", "0"));
    Object.keys(ALLIANCE_TACTIC_PCT_BY_LEVEL).forEach((lvl) => {
      mongolSel.appendChild(new Option(`레벨 ${lvl}`, String(lvl)));
    });
    mongolSel.value = "0";
  }

  const scoutSel = $("scoutPlane");
  if (scoutSel) {
    scoutSel.innerHTML = "";
    scoutSel.appendChild(new Option("적용 안함 (0%)", ""));
    const ages = ["디지털", "정보화", "드론", "자동화", "로봇공학"];
    ages.forEach(age => {
      const sep = new Option(`── ${age} ──`, "__sep__");
      sep.disabled = true;
      scoutSel.appendChild(sep);

      SCOUT_PLANE_SCAN_OPTIONS
        .filter(o => (o.age === age) || (age === "로봇공학" && o.age === "로봇"))
        .forEach(o => scoutSel.appendChild(new Option(`${o.name} - ${o.age}`, o.key)));
    });
    scoutSel.value = "";
  }

  FIXED_DMG_CHECK_ITEMS.forEach(it => $(`fixeddmg_${it.id}`)?.addEventListener("change", applyFixedDmgToBonuses));
  $("mongolLevel")?.addEventListener("change", applyMongolAutoToDmgBonus);
  ALLIANCE_EXTRA_OPTIONS.forEach(o => $(`mongol_${o.key}`)?.addEventListener("change", applyMongolAutoToDmgBonus));
  $("scoutPlane")?.addEventListener("change", applyScoutAutoToBonus);

  FIXED_SCAN_CHECK_ITEMS.forEach(it => {
    $(`scancheck_${it.id}`)?.addEventListener("change", () => scheduleRecalc(false));
  });

  enablePercentFormatting($("councilScanInput"), () => scheduleRecalc(false));

  $("allDmgResearchApply")?.addEventListener("change", (e) => {
    const on = !!e.target.checked;

    FIXED_DMG_CHECK_ITEMS.forEach(it => {
      const cb = $(`fixeddmg_${it.id}`);
      if (cb) cb.checked = on;
    });

    const mongolLevel = $("mongolLevel");
    if (mongolLevel) mongolLevel.value = on ? "8" : "0";
    ALLIANCE_EXTRA_OPTIONS.forEach(o => {
      const cb = $(`mongol_${o.key}`);
      if (cb) cb.checked = on;
    });

    const scoutPlane = $("scoutPlane");
    if (scoutPlane) {
      if (on) {
        let lastValue = "";
        for (let i = scoutPlane.options.length - 1; i >= 0; i--) {
          const v = scoutPlane.options[i].value;
          if (v && v !== "__sep__") { lastValue = v; break; }
        }
        scoutPlane.value = lastValue;
      } else {
        scoutPlane.value = "";
      }
    }

    FIXED_SCAN_CHECK_ITEMS.forEach(it => {
      const cb = $(`scancheck_${it.id}`);
      if (cb) cb.checked = on;
    });

    const council = $("councilScanInput");
    if (council) council.value = "0%";

    applyFixedDmgToBonuses();
    applyMongolAutoToDmgBonus();
    applyScoutAutoToBonus();
    scheduleRecalc(false);
  });

  applyFixedDmgToBonuses();
  applyMongolAutoToDmgBonus();
  applyScoutAutoToBonus();
}

function applyFixedHpToBonuses() {
  let sum = 0;

  FIXED_HP_CHECK_ITEMS.forEach(it => {
    const checked = !!$(`fixedhp_${it.id}`)?.checked;
    const val = checked ? it.pct : 0;
    sum += val;

    const idx = findBonusIndex(hpBonuses, it.id);
    if (idx >= 0) hpBonuses[idx].pct = String(val);
  });

  const out = $("fixedHpAutoOut");
  if (out) out.textContent = `${sum}%`;

  scheduleRecalc(true);
}

function applyEgyptAutoToHpBonus() {
  const lvl = Number($("egyptLevel")?.value || 0);

  let finalPct = 0;
  if (lvl !== 0) {
    const base = EGYPT_HP_PCT_BY_LEVEL[lvl] || 0;
    const extraSum = ALLIANCE_EXTRA_OPTIONS.reduce((acc, o) => acc + ($(`egypt_${o.key}`)?.checked ? o.pct : 0), 0);
    finalPct = Math.floor(base * (1 + extraSum / 100));
  }

  const out = $("egyptAutoOut");
  if (out) out.textContent = `${finalPct}%`;

  const idx = findBonusIndex(hpBonuses, "hp_auto_egypt");
  if (idx >= 0) hpBonuses[idx].pct = String(finalPct);

  scheduleRecalc(true);
}

function applyGuildAutoToHpBonus() {
  const sum = GUILD_LEVEL_HP_PARTS.reduce((acc, p) => acc + ($(`guild_${p.key}`)?.checked ? p.pct : 0), 0);

  const out = $("guildAutoOut");
  if (out) out.textContent = `${sum}%`;

  const idx = findBonusIndex(hpBonuses, "hp_auto_guild");
  if (idx >= 0) hpBonuses[idx].pct = String(sum);

  scheduleRecalc(true);
}

function applyFixedDmgToBonuses() {
  let sum = 0;

  FIXED_DMG_CHECK_ITEMS.forEach(it => {
    const checked = !!$(`fixeddmg_${it.id}`)?.checked;
    const val = checked ? it.pct : 0;
    sum += val;

    const idx = findBonusIndex(dmgBonuses, it.id);
    if (idx >= 0) dmgBonuses[idx].pct = String(val);
  });

  const out = $("fixedDmgAutoOut");
  if (out) out.textContent = `${sum}%`;

  scheduleRecalc(true);
}

function applyMongolAutoToDmgBonus() {
  const lvl = Number($("mongolLevel")?.value || 0);

  let finalPct = 0;
  if (lvl !== 0) {
    const base = ALLIANCE_TACTIC_PCT_BY_LEVEL[lvl] || 0;
    const extraSum = ALLIANCE_EXTRA_OPTIONS.reduce((acc, o) => acc + ($(`mongol_${o.key}`)?.checked ? o.pct : 0), 0);
    finalPct = Math.floor(base * (1 + extraSum / 100));
  }

  const out = $("mongolAutoOut");
  if (out) out.textContent = `${finalPct}%`;

  const idx = findBonusIndex(dmgBonuses, "dmg_auto_mongol");
  if (idx >= 0) dmgBonuses[idx].pct = String(finalPct);

  scheduleRecalc(true);
}

function applyScoutAutoToBonus() {
  const key = $("scoutPlane")?.value || "";
  const picked = key && key !== "__sep__" ? SCOUT_PLANE_SCAN_MAP[key] : null;
  const pct = picked ? picked.pct : 0;

  const idx = findBonusIndex(dmgBonuses, "dmg_auto_scoutscan");
  if (idx >= 0) dmgBonuses[idx].pct = String(pct);

  scheduleRecalc(true);
}

/* -------------------------------
   9) 계산/렌더
   ✅ FIX: hpCouncilRelicMount 입력값을 hpBonuses에 동기화해서 계산에 반영
------------------------------- */
function syncHpCouncilRelicToBonuses() {
  const councilPct = safeNum($("hp_def_council_tower")?.value);
  const relicPct   = safeNum($("hp_def_relic_tower")?.value);
  const enemyPct   = safeNum($("hp_att_relic_enemy_tower")?.value); // 음수로 들어옴

  const i1 = findBonusIndex(hpBonuses, "hp_def_council_tower");
  if (i1 >= 0) hpBonuses[i1].pct = String(councilPct);

  const i2 = findBonusIndex(hpBonuses, "hp_def_relic_tower");
  if (i2 >= 0) hpBonuses[i2].pct = String(relicPct);

  const i3 = findBonusIndex(hpBonuses, "hp_att_relic_enemy_tower");
  if (i3 >= 0) hpBonuses[i3].pct = String(enemyPct);
}

function recalc(rerenderBonuses) {
  if (rerenderBonuses) {
    const onChange = (needRerender) => scheduleRecalc(!!needRerender);
    renderBonusList($("hpBonusList"), hpBonuses, onChange);
    renderBonusList($("dmgBonusList"), dmgBonuses, onChange);
  }

  // ✅ HP 노란/빨간 박스 값 → 실제 hpBonuses에 반영
  syncHpCouncilRelicToBonuses();

  const baseHp = safeNum($("baseHp")?.value);
  const baseDmg = safeNum($("baseDmg")?.value);

  // HP
  const hpSumPct = sumBonusPct(hpBonuses);
  const totalHp = baseHp * (1 + hpSumPct / 100);

  // 파괴전술 DMG (스캔 관련 제외)
  const DMG_EXCLUDE_IDS = ["dmg_auto_scoutscan", "dmg_lib_scout", "dmg_uni_sunja", "dmg_att_council_scan"];
  const dmgSumPct = sumBonusPctExcept(dmgBonuses, DMG_EXCLUDE_IDS);
  const totalDmg = baseDmg * (1 + dmgSumPct / 100);

  // 협의회 입력값(스캔용)
  const councilScanPct = safeNum($("councilScanInput")?.value);

  const cIdx = findBonusIndex(dmgBonuses, "dmg_att_council_scan");
  if (cIdx >= 0) dmgBonuses[cIdx].pct = String(councilScanPct);

  // 정찰 스캔 총 수치(%)
  const scoutBasePct = getBonusPctById(dmgBonuses, "dmg_auto_scoutscan");
  const scanScoutResearchPct = ($("scancheck_dmg_lib_scout")?.checked ? 10 : 0);
  const scanSunjaPct         = ($("scancheck_dmg_uni_sunja")?.checked ? 20 : 0);
  const scanTotalPct = scoutBasePct + scanScoutResearchPct + scanSunjaPct + councilScanPct;

  // 정찰기 스캔 + 파괴전술 DMG
  const totalDmgScan = (totalDmg > 0 && scanTotalPct > 0) ? (totalDmg * (scanTotalPct / 100)) : NaN;

  // 표시값
  if ($("hpBonusSum")) $("hpBonusSum").textContent = fmtPctInt(hpSumPct);
  if ($("dmgBonusSum")) $("dmgBonusSum").textContent = fmtPctInt(dmgSumPct);

  if ($("totalHp")) $("totalHp").textContent = fmtInt(totalHp);

  if ($("totalDmg")) $("totalDmg").textContent = fmtInt(totalDmg);
  if ($("totalDmgScan")) $("totalDmgScan").textContent = fmtInt(totalDmgScan);

  if ($("scoutAutoOut")) $("scoutAutoOut").textContent = fmtPctInt(scanTotalPct);

    // ✅ 필요 개수
  // - 스캔%가 있으면: HP ÷ (파괴전술DMG × 스캔%)
  // - 스캔%가 0이면:  HP ÷ 파괴전술DMG (fallback)
  const denom =
    (Number.isFinite(totalDmgScan) && totalDmgScan > 0)
      ? totalDmgScan
      : (Number.isFinite(totalDmg) && totalDmg > 0 ? totalDmg : NaN);

  const raw = Number.isFinite(denom) ? (totalHp / denom) : NaN;

  if ($("needCountRaw")) $("needCountRaw").textContent = Number.isFinite(raw) ? raw.toFixed(2) : "-";
  if ($("needCountCeil")) $("needCountCeil").textContent = Number.isFinite(raw) ? Math.ceil(raw).toLocaleString("ko-KR") : "-";

}

/* -------------------------------
   10) Reset
------------------------------- */
function setCommaInputValue(id, valueNumber) {
  const el = $(id);
  if (!el) return;
  el.value = Number(valueNumber || 0).toLocaleString("ko-KR");
}

function resetHpSectionToZero() {
  if ($("allHpResearchApply")) $("allHpResearchApply").checked = false;
  setCommaInputValue("baseHp", 0);
  if ($("enemyAgeHp")) $("enemyAgeHp").value = "";

  hpBonuses = makeDefaultBonuses(DEFAULT_HP_BONUS_IDS);

  // ✅ HP 노란/빨간 입력도 초기화(표시 + 데이터)
  if ($("hp_def_council_tower")) $("hp_def_council_tower").value = "0%";
  if ($("hp_def_relic_tower")) $("hp_def_relic_tower").value = "0%";
  if ($("hp_att_relic_enemy_tower")) $("hp_att_relic_enemy_tower").value = "0%";

  FIXED_HP_CHECK_ITEMS.forEach(it => { const cb = $(`fixedhp_${it.id}`); if (cb) cb.checked = false; });
  if ($("egyptLevel")) $("egyptLevel").value = "0";
  ALLIANCE_EXTRA_OPTIONS.forEach(o => { const cb = $(`egypt_${o.key}`); if (cb) cb.checked = false; });
  GUILD_LEVEL_HP_PARTS.forEach(p => { const cb = $(`guild_${p.key}`); if (cb) cb.checked = false; });

  applyFixedHpToBonuses();
  applyEgyptAutoToHpBonus();
  applyGuildAutoToHpBonus();

  scheduleRecalc(true);
}

function resetDmgSectionToZero() {
  if ($("allDmgResearchApply")) $("allDmgResearchApply").checked = false;

  setCommaInputValue("baseDmg", 0);
  if ($("tacticLevel")) $("tacticLevel").value = "";

  dmgBonuses = makeDefaultBonuses(DEFAULT_DMG_BONUS_IDS);

  FIXED_DMG_CHECK_ITEMS.forEach(it => { const cb = $(`fixeddmg_${it.id}`); if (cb) cb.checked = false; });
  if ($("mongolLevel")) $("mongolLevel").value = "0";
  ALLIANCE_EXTRA_OPTIONS.forEach(o => { const cb = $(`mongol_${o.key}`); if (cb) cb.checked = false; });
  if ($("scoutPlane")) $("scoutPlane").value = "";

  FIXED_SCAN_CHECK_ITEMS.forEach(it => { const cb = $(`scancheck_${it.id}`); if (cb) cb.checked = false; });

  if ($("councilScanInput")) $("councilScanInput").value = "0%";
  const cIdx = findBonusIndex(dmgBonuses, "dmg_att_council_scan");
  if (cIdx >= 0) dmgBonuses[cIdx].pct = "0";

  applyFixedDmgToBonuses();
  applyMongolAutoToDmgBonus();
  applyScoutAutoToBonus();

  scheduleRecalc(true);
}

/* -------------------------------
   11) 이벤트 연결
------------------------------- */
function wireEvents() {
  enableCommaFormatting($("baseHp"), () => scheduleRecalc(false));
  enableCommaFormatting($("baseDmg"), () => scheduleRecalc(false));

  setCommaInputValue("baseHp", safeNum($("baseHp")?.value) || 0);
  setCommaInputValue("baseDmg", safeNum($("baseDmg")?.value) || 0);

  enablePercentFormatting($("councilScanInput"), () => scheduleRecalc(false));

  $("enemyAgeHp")?.addEventListener("change", (e) => {
    const age = e.target.value;
    setCommaInputValue("baseHp", age && MISSILE_BASE_HP_BY_AGE[age] ? MISSILE_BASE_HP_BY_AGE[age] : 0);
    scheduleRecalc(false);
  });

  $("tacticLevel")?.addEventListener("change", (e) => {
    const lvl = e.target.value;
    setCommaInputValue("baseDmg", (lvl && TACTIC_BASE_DMG_BY_LEVEL[lvl]) ? TACTIC_BASE_DMG_BY_LEVEL[lvl] : 0);
    scheduleRecalc(false);
  });

  $("addHpBonus")?.addEventListener("click", () => {
    hpBonuses.push({ id: makeUserBonusId("hp"), name: "새 HP 보너스", pct: "0", userAdded: true });
    scheduleRecalc(true);
  });

  $("addDmgBonus")?.addEventListener("click", () => {
    dmgBonuses.push({ id: makeUserBonusId("dmg"), name: "새 DMG 보너스", pct: "0", userAdded: true });
    scheduleRecalc(true);
  });

  $("resetHpBonuses")?.addEventListener("click", resetHpSectionToZero);
  $("resetDmgBonuses")?.addEventListener("click", resetDmgSectionToZero);
}

/* -------------------------------
   12) 시작
------------------------------- */
(function start() {
  initSelectOptions();
  renderReferenceTables();

  mountHpAutoBoxes();
  mountHpCouncilRelicRows();  // ✅ FIX: 실제 mount 호출

  mountDmgAutoBoxes();

  scheduleRecalc(true);
  wireEvents();

  scheduleRecalc(true);
})();
