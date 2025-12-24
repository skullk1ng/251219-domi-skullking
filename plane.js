/* =========================================================
   Dominations Calculator - plane.js (UNIFIED + OPTIMIZED, SAFE)
   - 비행기 HP / GCI / SAM + 몇 방 계산
   - "모든 연구 완료(일괄 적용)"은 각 섹션의 하위 항목만 자동 적용
     ⚠️ GCI/SAM의 상대 시대 드롭다운(gciAge/samAge) 및 기본DMG는 절대 건드리지 않음
   - GCI 길드 보너스 UI + 합계 출력 JS 렌더 (guildGciBlock)
   - SAM은 협의회/유물 입력칸 없음(코드에서도 참조 제거)
   ========================================================= */

(() => {
  "use strict";

  const $ = (id) => document.getElementById(id);

  /* -------------------------------
     Utils
  ------------------------------- */
  function safeNum(v) {
    const n = Number(String(v ?? "").replace(/,/g, ""));
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

  function bindOnce(el, evt, handler, key) {
    if (!el) return;
    const k = `bound_${evt}_${key || "1"}`;
    if (el.dataset[k] === "1") return;
    el.dataset[k] = "1";
    el.addEventListener(evt, handler);
  }

  function enableCommaFormatting(inputEl, onBlurCommit) {
    if (!inputEl) return;

    bindOnce(inputEl, "focus", () => {
      inputEl.value = String(inputEl.value ?? "").replace(/,/g, "");
    }, "comma_focus");

    bindOnce(inputEl, "input", () => {
      inputEl.value = String(inputEl.value ?? "").replace(/[^\d]/g, "");
    }, "comma_input");

    bindOnce(inputEl, "blur", () => {
      const raw = String(inputEl.value ?? "").replace(/,/g, "");
      if (raw === "") {
        inputEl.value = "0";
        onBlurCommit?.();
        return;
      }
      inputEl.value = Number(raw).toLocaleString("ko-KR");
      onBlurCommit?.();
    }, "comma_blur");
  }

  function enablePctInput(inputEl, onCommit) {
    if (!inputEl) return;

    bindOnce(inputEl, "input", () => {
      inputEl.value = String(inputEl.value ?? "").replace(/[^\d]/g, "");
      onCommit?.();
    }, "pct_input");

    bindOnce(inputEl, "blur", () => {
      if (String(inputEl.value ?? "") === "") inputEl.value = "0";
      onCommit?.();
    }, "pct_blur");
  }

  // 음수 강제(0~85). 사용자가 정수 넣으면 blur 시 자동 -로 변환
  function enableEnemyNegPct(inputEl, onCommit) {
    if (!inputEl) return;

    bindOnce(inputEl, "input", () => {
      const raw = String(inputEl.value ?? "").replace(/[^\d\-]/g, "");
      inputEl.value = raw.replace(/-/g, "");
      onCommit?.();
    }, "neg_input");

    bindOnce(inputEl, "blur", () => {
      const raw = String(inputEl.value ?? "").replace(/[^\d]/g, "");
      let v = Number(raw);
      if (!Number.isFinite(v)) v = 0;
      if (v < 0) v = 0;
      if (v > 85) v = 85;
      inputEl.value = String(v === 0 ? 0 : -v);
      onCommit?.();
    }, "neg_blur");
  }

  function setCommaValue(id, n) {
    const el = $(id);
    if (!el) return;
    el.value = Number(n || 0).toLocaleString("ko-KR");
  }

  /* -------------------------------
     Data: Aircraft base HP tables
  ------------------------------- */
  const AIRCRAFT_DATA = {
    transport: [
      { age: "디지털", name: "첨단 수송기 Mk.1", hp: 12214 },
      { age: "디지털", name: "첨단 수송기 Mk.2", hp: 11654 },
      { age: "디지털", name: "첨단 수송기 Mk.3", hp: 12115 },
      { age: "디지털", name: "첨단 수송기 Mk.4", hp: 12590 },
      { age: "디지털", name: "첨단 수송기 Mk.5", hp: 13045 },
      { age: "디지털", name: "첨단 수송기 Mk.6", hp: 13500 },

      { age: "정보화", name: "뱅가드 수송기 Mk.1", hp: 14175 },
      { age: "정보화", name: "뱅가드 수송기 Mk.2", hp: 14884 },
      { age: "정보화", name: "뱅가드 수송기 Mk.3", hp: 15628 },
      { age: "정보화", name: "뱅가드 수송기 Mk.4", hp: 16409 },
      { age: "정보화", name: "뱅가드 수송기 Mk.5", hp: 17230 },
      { age: "정보화", name: "뱅가드 수송기 Mk.6", hp: 18091 },

      { age: "드론", name: "스피어헤드 수송기 Mk.1", hp: 18543 },
      { age: "드론", name: "스피어헤드 수송기 Mk.2", hp: 19007 },
      { age: "드론", name: "스피어헤드 수송기 Mk.3", hp: 19482 },
      { age: "드론", name: "스피어헤드 수송기 Mk.4", hp: 19969 },
      { age: "드론", name: "스피어헤드 수송기 Mk.5", hp: 20468 },
      { age: "드론", name: "스피어헤드 수송기 Mk.6", hp: 20980 },

      { age: "자동화", name: "캡틴 수송기 Mk.1", hp: 21520 },
      { age: "자동화", name: "캡틴 수송기 Mk.2", hp: 22070 },
      { age: "자동화", name: "캡틴 수송기 Mk.3", hp: 22750 },
      { age: "자동화", name: "함장 수송기 Mk.4", hp: 23228 },
      { age: "자동화", name: "함장 수송기 Mk.5", hp: 23903 },
      { age: "자동화", name: "캡틴 수송기 Mk.6", hp: 24582 },

      { age: "로봇공학", name: "메이저 수송기 Mk1", hp: 25852 },
      { age: "로봇공학", name: "메이저 수송기 Mk2", hp: 26311 },
      { age: "로봇공학", name: "메이저 수송기 Mk3", hp: 26770 },
      { age: "로봇공학", name: "메이저 수송기 Mk4", hp: 27229 },
      { age: "로봇공학", name: "메이저 수송기 Mk5", hp: 27688 },
      { age: "로봇공학", name: "메이저 수송기 Mk6", hp: 28147 },
      { age: "로봇공학", name: "메이저 수송기 Mk7", hp: 28606 },
      { age: "로봇공학", name: "메이저 수송기 Mk8", hp: 29065 },
      { age: "로봇공학", name: "메이저 수송기 Mk9", hp: 29524 },
      { age: "로봇공학", name: "메이저 수송기 Mk10", hp: 29983 },
    ],
    bomber: [
      { age: "디지털", name: "고급 폭격기 Mk.1", hp: 8135 },
      { age: "디지털", name: "고급 폭격기 Mk.2", hp: 8455 },
      { age: "디지털", name: "고급 폭격기 Mk.3", hp: 8795 },
      { age: "디지털", name: "고급 폭격기 Mk.4", hp: 9155 },
      { age: "디지털", name: "고급 폭격기 Mk.5", hp: 9535 },
      { age: "디지털", name: "고급 폭격기 Mk.6", hp: 9950 },

      { age: "정보화", name: "뱅가드 폭격기 Mk.1", hp: 10448 },
      { age: "정보화", name: "뱅가드 폭격기 Mk.2", hp: 10970 },
      { age: "정보화", name: "뱅가드 폭격기 Mk.3", hp: 11518 },
      { age: "정보화", name: "뱅가드 폭격기 Mk.4", hp: 12094 },
      { age: "정보화", name: "뱅가드 폭격기 Mk.5", hp: 12670 },
      { age: "정보화", name: "뱅가드 폭격기 Mk.6", hp: 13334 },

      { age: "드론", name: "스피어헤드 폭격기 Mk.1", hp: 14000 },
      { age: "드론", name: "스피어헤드 폭격기 Mk.2", hp: 14750 },
      { age: "드론", name: "스피어헤드 폭격기 Mk.3", hp: 15488 },
      { age: "드론", name: "스피어헤드 폭격기 Mk.4", hp: 16262 },
      { age: "드론", name: "스피어헤드 폭격기 Mk.5", hp: 17075 },
      { age: "드론", name: "스피어헤드 폭격기 Mk.6", hp: 17929 },

      { age: "자동화", name: "캡틴 폭격기 Mk.1", hp: 18850 },
      { age: "자동화", name: "캡틴스 폭격기 Mk.2", hp: 19774 },
      { age: "자동화", name: "캡틴스 폭격기 Mk.3", hp: 20605 },
      { age: "자동화", name: "캡틴 폭격기 Mk.4", hp: 21525 },
      { age: "자동화", name: "캡틴 폭격기 Mk.5", hp: 22456 },
      { age: "자동화", name: "캡틴 폭격기 Mk.6", hp: 23377 },

      { age: "로봇공학", name: "메이저 폭격기 Mk1", hp: 25298 },
      { age: "로봇공학", name: "메이저 폭격기 Mk2", hp: 25993 },
      { age: "로봇공학", name: "메이저 폭격기 Mk3", hp: 26688 },
      { age: "로봇공학", name: "메이저 폭격기 Mk4", hp: 27383 },
      { age: "로봇공학", name: "메이저 폭격기 Mk5", hp: 28078 },
      { age: "로봇공학", name: "메이저 폭격기 Mk6", hp: 28773 },
      { age: "로봇공학", name: "메이저 폭격기 Mk7", hp: 29468 },
      { age: "로봇공학", name: "메이저 폭격기 Mk8", hp: 30163 },
      { age: "로봇공학", name: "메이저 폭격기 Mk9", hp: 30858 },
      { age: "로봇공학", name: "메이저 폭격기 Mk10", hp: 31553 },
    ],
    scout: [
      { age: "디지털", name: "정찰기 Mk.1", hp: 9978 },
      { age: "디지털", name: "정찰기 Mk.2", hp: 10329 },
      { age: "디지털", name: "정찰기 Mk.3", hp: 10703 },
      { age: "디지털", name: "정찰기 Mk.4", hp: 11121 },
      { age: "디지털", name: "정찰기 Mk.5", hp: 12561 },
      { age: "디지털", name: "정찰기 Mk.6", hp: 12023 },

      { age: "정보화", name: "초음속 정찰기 Mk.1", hp: 12624 },
      { age: "정보화", name: "초음속 정찰기 Mk.2", hp: 13255 },
      { age: "정보화", name: "초음속 정찰기 Mk.3", hp: 13918 },
      { age: "정보화", name: "초음속 정찰기 Mk.4", hp: 14613 },
      { age: "정보화", name: "초음속 정찰기 Mk.5", hp: 15344 },
      { age: "정보화", name: "초음속 정찰기 Mk.6", hp: 16111 },

      { age: "드론", name: "스피어헤드 정찰기 Mk.1", hp: 16917 },
      { age: "드론", name: "스피어헤드 정찰기 Mk.2", hp: 17763 },
      { age: "드론", name: "스피어헤드 정찰기 Mk.3", hp: 18651 },
      { age: "드론", name: "스피어헤드 정찰기 Mk.4", hp: 19584 },
      { age: "드론", name: "스피어헤드 정찰기 Mk.5", hp: 20563 },
      { age: "드론", name: "스피어헤드 정찰기 Mk.6", hp: 21591 },

      { age: "자동화", name: "캡틴스 정찰기 Mk.1", hp: 22585 },
      { age: "자동화", name: "캡틴스 정찰기 Mk.2", hp: 23574 },
      { age: "자동화", name: "캡틴스 정찰기 Mk.3", hp: 24563 },
      { age: "자동화", name: "캡틴스 정찰기 Mk.4", hp: 25555 },
      { age: "자동화", name: "캡틴스 정찰기 Mk.5", hp: 26537 },
      { age: "자동화", name: "캡틴스 정찰기 Mk.6", hp: 27515 },

      { age: "로봇공학", name: "메이저스 정찰기 Mk1", hp: 29604 },
      { age: "로봇공학", name: "메이저스 정찰기 Mk2", hp: 30360 },
      { age: "로봇공학", name: "메이저스 정찰기 Mk3", hp: 31116 },
      { age: "로봇공학", name: "메이저스 정찰기 Mk4", hp: 31872 },
      { age: "로봇공학", name: "메이저스 정찰기 Mk5", hp: 32628 },
      { age: "로봇공학", name: "메이저스 정찰기 Mk6", hp: 33384 },
      { age: "로봇공학", name: "메이저스 정찰기 Mk7", hp: 34140 },
      { age: "로봇공학", name: "메이저스 정찰기 Mk8", hp: 34896 },
      { age: "로봇공학", name: "메이저스 정찰기 Mk9", hp: 35652 },
      { age: "로봇공학", name: "메이저의 정찰기 Mk10", hp: 36408 },
    ],
  };

  const AGES_ORDER = ["디지털", "정보화", "드론", "자동화", "로봇공학"];

  /* -------------------------------
     Trap base DMG tables
  ------------------------------- */
  const GCI_BASE_DMG_BY_AGE = { 정보화: 9936, 드론: 11091, 자동화: 12245 };
  const SAM_BASE_DMG_BY_AGE = { 디지털: 5635, 정보화: 7468, 드론: 9660, 자동화: 11300 };

  /* -------------------------------
     Alliance tables + extras
  ------------------------------- */
  const ALLIANCE_EXTRA_OPTIONS = [
    { key: "lib", name: "[도서관] 연구:연맹 병력", pct: 10 },
    { key: "uni", name: "[유니버시티] 몬테수마 황제", pct: 30 },
    { key: "law", name: "[의회] 연맹훈련", pct: 30 },
  ];

  const US_HP_PCT_BY_LEVEL = { 1: 10, 2: 15, 3: 20, 4: 25, 5: 30, 6: 35, 7: 40, 8: 45 };
  const MAORI_GCI_PCT_BY_LEVEL = { 1: 10, 2: 12, 3: 15, 4: 20, 5: 25, 6: 30, 7: 35, 8: 40 };

  /* -------------------------------
     Manufacturing equipment tables
  ------------------------------- */
  const MANU_EQUIP = {
    composite: {
      name: "합성내벽",
      hpPctByLevel: { 2: 2, 4: 2, 6: 4, 7: 4, 9: 4, 12: 5, 14: 5, 18: 5, 19: 5 },
      commonReduceByLevel: { 1: 5, 20: 10 },
      samOnlyReduceByLevel: {},
    },
    drfm: {
      name: "DRFM 전파방해기",
      hpPctByLevel: {
        2: 3, 3: 3, 4: 3, 5: 3,
        7: 5, 8: 5, 9: 5,
        12: 5, 13: 5, 14: 5, 15: 5, 16: 5, 17: 5, 18: 5, 19: 5, 20: 5,
      },
      commonReduceByLevel: { 1: 5, 6: 5, 20: 5 },
      samOnlyReduceByLevel: {},
    },
    eject: {
      name: "사출좌석",
      hpPctByLevel: { 3: 3, 6: 5, 8: 5, 13: 5, 15: 5, 18: 5, 19: 5 },
      commonReduceByLevel: {},
      samOnlyReduceByLevel: { 1: 5 },
    },
  };

  function manuAllowedKeys(type) {
    if (type === "bomber") return ["composite", "drfm", "eject"];
    return ["composite", "drfm"];
  }

  /* -------------------------------
     State
  ------------------------------- */
  let planeType = "transport";
  let manuSlot1 = { equip: "", level: 0 };
  let manuSlot2 = { equip: "", level: 0 };

  let allPlaneHpResearchOn = false;
  let allGciResearchOn = false;
  let allSamResearchOn = false;

  /* -------------------------------
     Rendering: aircraft select
  ------------------------------- */
  function buildPlaneSelectOptions(type) {
    const sel = $("planeModel");
    if (!sel) return;

    sel.innerHTML = "";
    sel.appendChild(new Option("— 선택 —", ""));

    const list = AIRCRAFT_DATA[type] ?? [];
    AGES_ORDER.forEach((age) => {
      const sep = new Option(`── ${age} ──`, "__sep__");
      sep.disabled = true;
      sel.appendChild(sep);

      list
        .filter((x) => x.age === age)
        .forEach((item) => {
          const opt = new Option(`${item.name} - ${item.age}`, `${type}__${age}__${item.name}`);
          opt.dataset.hp = String(item.hp);
          sel.appendChild(opt);
        });
    });

    sel.value = "";
    setCommaValue("basePlaneHp", 0);
  }

  function getPlaneHpFromSelect() {
    const sel = $("planeModel");
    if (!sel) return 0;
    const opt = sel.options[sel.selectedIndex];
    return safeNum(opt?.dataset?.hp);
  }

  /* -------------------------------
     Rendering: trap selects
  ------------------------------- */
  function initTrapSelects() {
    const gciSel = $("gciAge");
    if (gciSel) {
      gciSel.innerHTML = "";
      gciSel.appendChild(new Option("— 선택 —", ""));
      ["정보화", "드론", "자동화"].forEach((age) => {
        const label = (age === "자동화") ? "자동화/로봇공학" : age;
        gciSel.appendChild(new Option(label, age));
      });
      gciSel.value = "";
      setCommaValue("baseGciDmg", 0);
    }

    const samSel = $("samAge");
    if (samSel) {
      samSel.innerHTML = "";
      samSel.appendChild(new Option("— 선택 —", ""));
      ["디지털", "정보화", "드론", "자동화"].forEach((age) => {
        const label = (age === "자동화") ? "자동화/로봇공학" : age;
        samSel.appendChild(new Option(label, age));
      });
      samSel.value = "";
      setCommaValue("baseSamDmg", 0);
    }
  }

  /* -------------------------------
     UI blocks: 렌더
  ------------------------------- */
  function renderPlaneHpAutoBox() {
    const box = $("planeHpAutoBox");
    if (!box) return;

    const isTransport = planeType === "transport";
    const isBomber = planeType === "bomber";
    const isScout = planeType === "scout";

    box.innerHTML = `
      <div class="auto-box all-research-box" id="allPlaneHpResearchBox">
        <div class="auto-checks">
          <label class="check-item">
            <input type="checkbox" id="allPlaneHpResearchApply" />
            <span>모든 연구 완료 (일괄 적용)</span>
          </label>
        </div>
      </div>

      <div class="auto-box">
        <div class="auto-title">[AUTO] 연구 및 길드보너스</div>
        <div class="auto-checks">
          <label class="check-item"><input type="checkbox" id="lib_flight_all" /><span>도서관 연구: 비행</span></label>
          ${isTransport ? `<label class="check-item"><input type="checkbox" id="lib_elite_airborne" /><span>도서관 연구: 정예 공수부대</span></label>` : ""}
          ${isScout ? `<label class="check-item"><input type="checkbox" id="uni_sunzhu_scout_hp" /><span>유니버시티: 손자</span></label>` : ""}
          ${isTransport ? `<label class="check-item"><input type="checkbox" id="uni_amelia_transport_hp" /><span>유니버시티: 아멜리아 에어하트</span></label>` : ""}
          ${isBomber ? `<label class="check-item"><input type="checkbox" id="uni_amelia_bomber_hp" /><span>유니버시티: 아멜리아 에어하트</span></label>` : ""}
          <label class="check-item"><input type="checkbox" id="guild_lv7_plane_hp" /><span>길드보너스 레벨7</span></label>
        </div>
        <div class="auto-sum">
          <span>합계</span>
          <b id="planeAutoOut">0%</b>
        </div>
      </div>
    `;
  }

  function renderUsAllianceBox() {
    const box = $("usAllianceBox");
    if (!box) return;

    box.innerHTML = `
      <div class="auto-box">
        <div class="auto-title">[AUTO] 연맹: 미국</div>

        <label class="label" style="margin-top:2px;">연맹 레벨</label>
        <select id="usLevel" class="input"></select>

        <div class="auto-checks" style="margin-top:10px;">
          ${ALLIANCE_EXTRA_OPTIONS.map(o => `
            <label class="check-item"><input type="checkbox" id="us_${o.key}" /><span>${o.name}</span></label>
          `).join("")}
        </div>

        <div class="auto-sum">
          <span>합계</span>
          <b id="usAutoOut">0%</b>
        </div>
      </div>
    `;

    const sel = $("usLevel");
    if (!sel) return;

    sel.innerHTML = "";
    sel.appendChild(new Option("선택 안함 (0%)", "0"));
    Object.keys(US_HP_PCT_BY_LEVEL).forEach((lvl) => sel.appendChild(new Option(`레벨 ${lvl}`, String(lvl))));
    sel.value = "0";

    ALLIANCE_EXTRA_OPTIONS.forEach(o => {
      const cb = $(`us_${o.key}`);
      if (cb) cb.checked = false;
    });
  }

  function renderGciAllResearchBox() {
    const mount = $("gciAllResearchMount");
    if (!mount) return;

    mount.innerHTML = `
      <div class="auto-box all-research-box" id="allGciResearchBox">
        <div class="auto-checks">
          <label class="check-item">
            <input type="checkbox" id="allGciResearchApply" />
            <span>모든 연구 완료 (일괄 적용)</span>
          </label>
        </div>
      </div>
    `;
  }

  function renderSamAllResearchBox() {
    const mount = $("samAllResearchMount");
    if (!mount) return;

    mount.innerHTML = `
      <div class="auto-box all-research-box" id="allSamResearchBox">
        <div class="auto-checks">
          <label class="check-item">
            <input type="checkbox" id="allSamResearchApply" />
            <span>모든 연구 완료 (일괄 적용)</span>
          </label>
        </div>
      </div>
    `;
  }

  function renderMaoriAllianceBox() {
    const box = $("maoriAllianceBox");
    if (!box) return;

    box.innerHTML = `
      <div class="auto-box">
        <div class="auto-title">[AUTO] 연맹: 마오리</div>

        <label class="label" style="margin-top:2px;">마오리 레벨</label>
        <select id="maoriLevel" class="input"></select>

        <div class="auto-checks" style="margin-top:10px;">
          ${ALLIANCE_EXTRA_OPTIONS.map(o => `
            <label class="check-item"><input type="checkbox" id="maori_${o.key}" /><span>${o.name}</span></label>
          `).join("")}
        </div>

        <div class="auto-sum">
          <span>합계</span>
          <b id="maoriAutoOut">0%</b>
        </div>
      </div>
    `;

    const sel = $("maoriLevel");
    if (!sel) return;

    sel.innerHTML = "";
    sel.appendChild(new Option("선택 안함 (0%)", "0"));
    Object.keys(MAORI_GCI_PCT_BY_LEVEL).forEach((lvl) => sel.appendChild(new Option(`레벨 ${lvl}`, String(lvl))));
    sel.value = "0";

    ALLIANCE_EXTRA_OPTIONS.forEach(o => {
      const cb = $(`maori_${o.key}`);
      if (cb) cb.checked = false;
    });
  }

  // ✅ GCI 길드 보너스 UI + 합계 렌더
  function renderGuildGciBlock() {
    const box = $("guildGciBlock");
    if (!box) return;

    box.innerHTML = `
      <div class="auto-box" id="guildGciBox">
        <div class="auto-title">길드 보너스</div>

        <div class="auto-checks">
          <label class="check-item">
            <input type="checkbox" id="guild_gci_lv8" />
            <span>길드 레벨 8 (GCI DMG +10%)</span>
          </label>
          <label class="check-item">
            <input type="checkbox" id="guild_gci_lv13" />
            <span>길드 레벨 13 (GCI DMG +10%)</span>
          </label>
          <label class="check-item">
            <input type="checkbox" id="guild_gci_lv21" />
            <span>길드 레벨 21 (GCI DMG +10%)</span>
          </label>
        </div>

        <div class="hint spaced">
          달성한 길드레벨 모두 체크 (예시: 길드레벨 21 → 3개 모두 체크)
        </div>

        <div class="auto-sum">
          <span>합계</span>
          <b id="guildGciOut">0%</b>
        </div>
      </div>
    `;
  }

  /* -------------------------------
     Manufacturing UI
  ------------------------------- */
  function renderManuBox() {
    const box = $("manuBox");
    if (!box) return;

    box.innerHTML = `
      <div class="auto-box manu-block">
        <div class="auto-title">제조소 장비 (최대 2개 / 중복 장착 불가)</div>

        <div class="grid2">
          <div>
            <label class="label">슬롯 1 장비</label>
            <select id="manuEquip1" class="input"></select>
          </div>
          <div>
            <label class="label">장비 레벨</label>
            <select id="manuLevel1" class="input"></select>
          </div>
        </div>

        <div class="grid2" style="margin-top:10px;">
          <div>
            <label class="label">슬롯 2 장비</label>
            <select id="manuEquip2" class="input"></select>
          </div>
          <div>
            <label class="label">장비 레벨</label>
            <select id="manuLevel2" class="input"></select>
          </div>
        </div>

        <div class="manu-sub-block">
          <div class="auto-title" style="margin:0;">[AUTO] 받는 피해 감소 수치</div>
          <div id="manuReduceWrap" class="reduce-wrap">
            <div id="manuReduceCommon" class="reduce-chip">GCI+SAM = 0%</div>
            <div id="manuReduceSamOnly" class="reduce-chip">ONLY SAM = 0%</div>
          </div>
        </div>

        <div class="manu-conditions">
          <div class="manu-research-box">
            <div class="manu-research-title">연구 완료 여부</div>

            <div class="manu-research-checks">
              <label class="manu-research-item">
                <input type="checkbox" id="research_ransom_olds" />
                <span>[유니버시티] 랜섬 E. 올즈 '병력 군수품 HP 보너스' 연구</span>
              </label>

              <label class="manu-research-item">
                <input type="checkbox" id="research_fully_armed_attack" />
                <span>[도서관] '완전 무장된 공격' 연구</span>
              </label>
            </div>
          </div>

          <div class="manu-cond-row">
            <div class="manu-cond-text">레벨 20 장비 장착 개당 HP +10%</div>
            <div class="manu-cond-status is-off" id="cond_ransom_status">비활성</div>
          </div>

          <div class="manu-cond-row">
            <div class="manu-cond-text">장비 2개 모두 장착 시 HP +16%</div>
            <div class="manu-cond-status is-off" id="cond_fullyarmed_status">비활성</div>
          </div>
        </div>
      </div>
    `;

    populateManuEquipSelects();
    populateLevelSelect("manuLevel1");
    populateLevelSelect("manuLevel2");

    manuSlot1 = { equip: "", level: 0 };
    manuSlot2 = { equip: "", level: 0 };

    $("manuEquip1").value = "";
    $("manuEquip2").value = "";
    $("manuLevel1").value = "0";
    $("manuLevel2").value = "0";

    if ($("research_ransom_olds")) $("research_ransom_olds").checked = false;
    if ($("research_fully_armed_attack")) $("research_fully_armed_attack").checked = false;
  }

  function populateLevelSelect(id) {
    const sel = $(id);
    if (!sel) return;
    sel.innerHTML = "";
    sel.appendChild(new Option("없음", "0"));
    for (let i = 1; i <= 20; i++) sel.appendChild(new Option(`Lv ${i}`, String(i)));
    sel.value = "0";
  }

  function populateManuEquipSelects() {
    const allowed = manuAllowedKeys(planeType);

    const build = (selId) => {
      const sel = $(selId);
      if (!sel) return;
      sel.innerHTML = "";
      sel.appendChild(new Option("없음", ""));
      allowed.forEach((key) => sel.appendChild(new Option(MANU_EQUIP[key].name, key)));
      sel.value = "";
    };

    build("manuEquip1");
    build("manuEquip2");
    syncManuDuplicateBlock();
  }

  function syncManuDuplicateBlock() {
    const sel1 = $("manuEquip1");
    const sel2 = $("manuEquip2");
    if (!sel1 || !sel2) return;

    const v1 = sel1.value;
    const v2 = sel2.value;

    [...sel1.options].forEach((opt) => {
      if (!opt.value) { opt.disabled = false; return; }
      opt.disabled = (opt.value === v2);
    });

    [...sel2.options].forEach((opt) => {
      if (!opt.value) { opt.disabled = false; return; }
      opt.disabled = (opt.value === v1);
    });
  }

  /* -------------------------------
     Calculations
  ------------------------------- */
  function calcAllianceFinalPct(level, map, prefixId) {
    const lvl = Number(level || 0);
    if (!lvl) return 0;

    const base = map[lvl] || 0;
    const extraSum = ALLIANCE_EXTRA_OPTIONS.reduce((acc, o) => {
      return acc + ($(`${prefixId}_${o.key}`)?.checked ? o.pct : 0);
    }, 0);

    return Math.floor(base * (1 + extraSum / 100));
  }

  function calcManuEffects() {
    const slots = [manuSlot1, manuSlot2];

    let hpPctSum = 0;
    let commonReduce = 0;
    let samOnlyReduce = 0;

    let equippedCount = 0;
    let lvl20Count = 0;

    slots.forEach((s) => {
      if (!s.equip || !s.level) return;

      equippedCount += 1;
      if (s.level === 20) lvl20Count += 1;

      const def = MANU_EQUIP[s.equip];
      if (!def) return;

      hpPctSum += (def.hpPctByLevel[s.level] || 0);
      commonReduce += (def.commonReduceByLevel[s.level] || 0);
      samOnlyReduce += (def.samOnlyReduceByLevel[s.level] || 0);
    });

    const ransomResearchDone = !!$("research_ransom_olds")?.checked;
    const fullyArmedResearchDone = !!$("research_fully_armed_attack")?.checked;

    const ransomOk = ransomResearchDone && (lvl20Count > 0);
    const fullyArmedOk = fullyArmedResearchDone && (equippedCount === 2);

    if (ransomOk) hpPctSum += (lvl20Count * 10);
    if (fullyArmedOk) hpPctSum += 16;

    return { hpPctSum, commonReduce, samOnlyReduce, equippedCount, lvl20Count };
  }

  function calcPlaneHpPctSum(manu) {
    let sum = 0;

    let autoSum = 0;
    if ($("lib_flight_all")?.checked) autoSum += 10;
    if ($("lib_elite_airborne")?.checked) autoSum += 10;
    if ($("uni_sunzhu_scout_hp")?.checked) autoSum += 20;
    if ($("uni_amelia_transport_hp")?.checked) autoSum += 30;
    if ($("uni_amelia_bomber_hp")?.checked) autoSum += 30;
    if ($("guild_lv7_plane_hp")?.checked) autoSum += 10;

    const autoOut = $("planeAutoOut");
    if (autoOut) autoOut.textContent = `${autoSum}%`;
    sum += autoSum;

    const usLvl = Number($("usLevel")?.value || 0);
    const usPct = calcAllianceFinalPct(usLvl, US_HP_PCT_BY_LEVEL, "us");
    const usOut = $("usAutoOut");
    if (usOut) usOut.textContent = `${usPct}%`;
    sum += usPct;

    sum += safeNum($("councilPlaneHpPct")?.value);
    sum += safeNum($("relicPlaneHpPct")?.value);

    sum += (manu?.hpPctSum || 0);

    sum += safeNum($("enemyInvasionPlaneHpNegPct")?.value);

    return sum;
  }

  function calcGciDmgPctSum() {
    let sum = 0;

    const maoriLvl = Number($("maoriLevel")?.value || 0);
    const maoriPct = calcAllianceFinalPct(maoriLvl, MAORI_GCI_PCT_BY_LEVEL, "maori");
    const maoriOut = $("maoriAutoOut");
    if (maoriOut) maoriOut.textContent = `${maoriPct}%`;
    sum += maoriPct;

    let guildSum = 0;
    if ($("guild_gci_lv8")?.checked) guildSum += 10;
    if ($("guild_gci_lv13")?.checked) guildSum += 10;
    if ($("guild_gci_lv21")?.checked) guildSum += 10;

    const guildOut = $("guildGciOut");
    if (guildOut) guildOut.textContent = `${guildSum}%`;
    sum += guildSum;

    sum += safeNum($("councilGciPct")?.value);
    sum += safeNum($("relicGciPct")?.value);

    return sum;
  }

  function calcSamDmgPctSum() {
    let sum = 0;

    if ($("lib_sam_deception")?.checked) sum += 20;
    if ($("lib_sam_aa")?.checked) sum += 10;
    if ($("lib_sam_early")?.checked) sum += 10;

    if ($("uni_amelia_sam")?.checked) sum += 30;
    if ($("law_defensive_interference")?.checked) sum += 10;

    if ($("guild_sam_lv13")?.checked) sum += 10;
    if ($("guild_sam_lv21")?.checked) sum += 10;

    const out = $("samAutoOut");
    if (out) out.textContent = `${sum}%`;

    return sum;
  }

  function renderReduceChips(manu) {
    const common = manu?.commonReduce || 0;
    const samOnly = manu?.samOnlyReduce || 0;

    const chipCommon = $("manuReduceCommon");
    const chipSamOnly = $("manuReduceSamOnly");

    if (chipCommon) chipCommon.textContent = `GCI+SAM = ${common}%`;
    if (chipSamOnly) chipSamOnly.textContent = `ONLY SAM = ${samOnly}%`;
  }

  function setCondStatus(el, isOn) {
    if (!el) return;
    el.classList.toggle("is-on", !!isOn);
    el.classList.toggle("is-off", !isOn);
    el.textContent = isOn ? "활성" : "비활성";
  }

  function setCondRansomStatus(el, lvl20Count, researchDone) {
    if (!el) return;

    const n = researchDone ? Math.max(0, Math.min(2, Number(lvl20Count || 0))) : 0;
    const isOn = n > 0;

    el.classList.toggle("is-on", isOn);
    el.classList.toggle("is-off", !isOn);

    el.textContent = isOn ? `${n * 10}%` : "비활성";
  }

  function updateManuConditionUI(manu) {
    const ransomResearchDone = !!$("research_ransom_olds")?.checked;
    const fullyArmedResearchDone = !!$("research_fully_armed_attack")?.checked;

    const fullyArmedOn = fullyArmedResearchDone && ((manu?.equippedCount || 0) === 2);

    setCondRansomStatus($("cond_ransom_status"), (manu?.lvl20Count || 0), ransomResearchDone);
    setCondStatus($("cond_fullyarmed_status"), fullyArmedOn);
  }

  function recalc() {
    const basePlaneHp = safeNum($("basePlaneHp")?.value);
    const baseGciDmg = safeNum($("baseGciDmg")?.value);
    const baseSamDmg = safeNum($("baseSamDmg")?.value);

    const manu = calcManuEffects();
    updateManuConditionUI(manu);
    renderReduceChips(manu);

    const planeHpPctSum = calcPlaneHpPctSum(manu);
    const totalPlaneHp = basePlaneHp * (1 + planeHpPctSum / 100);
    if ($("planeHpBonusSum")) $("planeHpBonusSum").textContent = fmtPctInt(planeHpPctSum);
    if ($("totalPlaneHp")) $("totalPlaneHp").textContent = fmtInt(totalPlaneHp);

    const gciPctSum = calcGciDmgPctSum();
    const totalGci = baseGciDmg * (1 + gciPctSum / 100);
    const gciAfter = totalGci * (1 - (manu.commonReduce || 0) / 100);
    if ($("totalGciDmg")) $("totalGciDmg").textContent = fmtInt(totalGci);
    if ($("gciDmgAfterReduce")) $("gciDmgAfterReduce").textContent = fmtInt(gciAfter);

    const gciRaw = gciAfter > 0 ? (totalPlaneHp / gciAfter) : NaN;
    if ($("gciShotsRaw")) $("gciShotsRaw").textContent = Number.isFinite(gciRaw) ? gciRaw.toFixed(2) : "-";
    if ($("gciShotsCeil")) $("gciShotsCeil").textContent = Number.isFinite(gciRaw) ? Math.ceil(gciRaw).toLocaleString("ko-KR") : "-";

    const samPctSum = calcSamDmgPctSum();
    const totalSam = baseSamDmg * (1 + samPctSum / 100);
    const samReduceSum = (manu.commonReduce || 0) + (manu.samOnlyReduce || 0);
    const samAfter = totalSam * (1 - samReduceSum / 100);
    if ($("totalSamDmg")) $("totalSamDmg").textContent = fmtInt(totalSam);
    if ($("samDmgAfterReduce")) $("samDmgAfterReduce").textContent = fmtInt(samAfter);

    const samRaw = samAfter > 0 ? (totalPlaneHp / samAfter) : NaN;
    if ($("samShotsRaw")) $("samShotsRaw").textContent = Number.isFinite(samRaw) ? samRaw.toFixed(2) : "-";
    if ($("samShotsCeil")) $("samShotsCeil").textContent = Number.isFinite(samRaw) ? Math.ceil(samRaw).toLocaleString("ko-KR") : "-";
  }

  /* -------------------------------
     Apply "All Research" (HP/GCI/SAM)
  ------------------------------- */
  function applyAllPlaneHpResearchUI(on) {
    [
      "lib_flight_all",
      "lib_elite_airborne",
      "uni_sunzhu_scout_hp",
      "uni_amelia_transport_hp",
      "uni_amelia_bomber_hp",
      "guild_lv7_plane_hp",
    ].forEach((id) => {
      const cb = $(id);
      if (cb) cb.checked = on;
    });

    const us = $("usLevel");
    if (us) us.value = on ? "8" : "0";

    ALLIANCE_EXTRA_OPTIONS.forEach((o) => {
      const cb = $(`us_${o.key}`);
      if (cb) cb.checked = on;
    });
  }

  // ⚠️ gciAge/baseGciDmg 절대 건드리지 않음
  function applyAllGciResearchUI(on) {
    const maori = $("maoriLevel");
    if (maori) maori.value = on ? "8" : "0";

    ALLIANCE_EXTRA_OPTIONS.forEach((o) => {
      const cb = $(`maori_${o.key}`);
      if (cb) cb.checked = on;
    });

    ["guild_gci_lv8", "guild_gci_lv13", "guild_gci_lv21"].forEach((id) => {
      const cb = $(id);
      if (cb) cb.checked = on;
    });
  }

  // ⚠️ samAge/baseSamDmg 절대 건드리지 않음
  function applyAllSamResearchUI(on) {
    [
      "lib_sam_deception", "lib_sam_aa", "lib_sam_early",
      "uni_amelia_sam", "law_defensive_interference",
      "guild_sam_lv13", "guild_sam_lv21",
    ].forEach((id) => {
      const cb = $(id);
      if (cb) cb.checked = on;
    });
  }

  function restoreAllResearchCheckboxes() {
    const hpAll = $("allPlaneHpResearchApply");
    if (hpAll) {
      hpAll.checked = !!allPlaneHpResearchOn;
      if (hpAll.checked) applyAllPlaneHpResearchUI(true);
    }

    const gciAll = $("allGciResearchApply");
    if (gciAll) {
      gciAll.checked = !!allGciResearchOn;
      if (gciAll.checked) applyAllGciResearchUI(true);
    }

    const samAll = $("allSamResearchApply");
    if (samAll) {
      samAll.checked = !!allSamResearchOn;
      if (samAll.checked) applyAllSamResearchUI(true);
    }
  }

  /* -------------------------------
     Wiring
  ------------------------------- */
  function bindHandlers() {
    bindOnce($("planeModel"), "change", () => {
      const sel = $("planeModel");
      if (!sel) return;

      const v = sel.value;
      if (!v || v === "__sep__") {
        setCommaValue("basePlaneHp", 0);
        recalc();
        return;
      }

      setCommaValue("basePlaneHp", getPlaneHpFromSelect());
      recalc();
    }, "planeModel_change");

    bindOnce($("allPlaneHpResearchApply"), "change", (e) => {
      const on = !!e.target.checked;
      allPlaneHpResearchOn = on;
      applyAllPlaneHpResearchUI(on);
      recalc();
    }, "hp_all_change");

    [
      "lib_flight_all",
      "lib_elite_airborne",
      "uni_sunzhu_scout_hp",
      "uni_amelia_transport_hp",
      "uni_amelia_bomber_hp",
      "guild_lv7_plane_hp",
    ].forEach((id) => bindOnce($(id), "change", recalc, `hp_auto_${id}`));

    bindOnce($("usLevel"), "change", recalc, "usLevel_change");
    ALLIANCE_EXTRA_OPTIONS.forEach(o => bindOnce($(`us_${o.key}`), "change", recalc, `us_${o.key}`));

    bindOnce($("maoriLevel"), "change", recalc, "maoriLevel_change");
    ALLIANCE_EXTRA_OPTIONS.forEach(o => bindOnce($(`maori_${o.key}`), "change", recalc, `maori_${o.key}`));

    bindOnce($("allGciResearchApply"), "change", (e) => {
      const on = !!e.target.checked;
      allGciResearchOn = on;
      applyAllGciResearchUI(on);
      recalc();
    }, "gci_all_change");

    bindOnce($("allSamResearchApply"), "change", (e) => {
      const on = !!e.target.checked;
      allSamResearchOn = on;
      applyAllSamResearchUI(on);
      recalc();
    }, "sam_all_change");

    bindOnce($("research_ransom_olds"), "change", recalc, "ransom_change");
    bindOnce($("research_fully_armed_attack"), "change", recalc, "fully_change");

    [
      "councilPlaneHpPct", "relicPlaneHpPct",
      "councilGciPct", "relicGciPct",
    ].forEach((id) => enablePctInput($(id), recalc));

    enableEnemyNegPct($("enemyInvasionPlaneHpNegPct"), recalc);

    // 사용자 선택에만 반응
    bindOnce($("gciAge"), "change", (e) => {
      const age = e.target.value;
      setCommaValue("baseGciDmg", GCI_BASE_DMG_BY_AGE[age] || 0);
      recalc();
    }, "gciAge_change");

    bindOnce($("samAge"), "change", (e) => {
      const age = e.target.value;
      setCommaValue("baseSamDmg", SAM_BASE_DMG_BY_AGE[age] || 0);
      recalc();
    }, "samAge_change");

    ["guild_gci_lv8", "guild_gci_lv13", "guild_gci_lv21"].forEach((id) =>
      bindOnce($(id), "change", recalc, `gci_${id}`)
    );

    [
      "lib_sam_deception", "lib_sam_aa", "lib_sam_early",
      "uni_amelia_sam", "law_defensive_interference",
      "guild_sam_lv13", "guild_sam_lv21",
    ].forEach((id) => bindOnce($(id), "change", recalc, `sam_${id}`));

    bindOnce($("manuEquip1"), "change", () => {
      manuSlot1.equip = $("manuEquip1")?.value || "";
      if (!manuSlot1.equip) {
        manuSlot1.level = 0;
        $("manuLevel1").value = "0";
      }
      syncManuDuplicateBlock();
      recalc();
    }, "manuEquip1_change");

    bindOnce($("manuEquip2"), "change", () => {
      manuSlot2.equip = $("manuEquip2")?.value || "";
      if (!manuSlot2.equip) {
        manuSlot2.level = 0;
        $("manuLevel2").value = "0";
      }
      syncManuDuplicateBlock();
      recalc();
    }, "manuEquip2_change");

    bindOnce($("manuLevel1"), "change", () => {
      manuSlot1.level = Number($("manuLevel1")?.value || 0);
      if (!manuSlot1.equip) {
        manuSlot1.level = 0;
        $("manuLevel1").value = "0";
      }
      recalc();
    }, "manuLevel1_change");

    bindOnce($("manuLevel2"), "change", () => {
      manuSlot2.level = Number($("manuLevel2")?.value || 0);
      if (!manuSlot2.equip) {
        manuSlot2.level = 0;
        $("manuLevel2").value = "0";
      }
      recalc();
    }, "manuLevel2_change");

    enableCommaFormatting($("basePlaneHp"), recalc);
    enableCommaFormatting($("baseGciDmg"), recalc);
    enableCommaFormatting($("baseSamDmg"), recalc);
  }

  function wirePlaneTypeRadios() {
    const radios = [
      $("planeType_transport"),
      $("planeType_bomber"),
      $("planeType_scout"),
    ].filter(Boolean);

    radios.forEach((r) => {
      bindOnce(r, "change", () => {
        if (!r.checked) return;

        planeType = r.value;

        buildPlaneSelectOptions(planeType);

        renderPlaneHpAutoBox();
        renderUsAllianceBox();
        renderManuBox();

        ["councilPlaneHpPct", "relicPlaneHpPct", "enemyInvasionPlaneHpNegPct"].forEach((id) => {
          if ($(id)) $(id).value = "0";
        });

        bindHandlers();
        restoreAllResearchCheckboxes();
        recalc();
      }, `radio_${r.id}`);
    });
  }

  /* -------------------------------
     Start
  ------------------------------- */
  (function start() {
    planeType = "transport";

    buildPlaneSelectOptions(planeType);
    initTrapSelects();

    renderPlaneHpAutoBox();
    renderUsAllianceBox();
    renderGciAllResearchBox();
    renderMaoriAllianceBox();
    renderGuildGciBlock();
    renderSamAllResearchBox();
    renderManuBox();

    setCommaValue("basePlaneHp", 0);
    setCommaValue("baseGciDmg", 0);
    setCommaValue("baseSamDmg", 0);

    wirePlaneTypeRadios();
    bindHandlers();
    restoreAllResearchCheckboxes();
    recalc();
  })();
})();
