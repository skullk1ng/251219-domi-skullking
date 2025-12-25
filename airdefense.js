/* =========================================================
   Dominations Calculator - 방공시설 & 파괴전술 계산기
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
  function clamp(n, min, max) {
    return Math.max(min, Math.min(max, n));
  }

  // ✅ 이벤트 중복 방지
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
      inputEl.value = String(inputEl.value ?? "").replace(/[^\d\-]/g, "");
      onCommit?.();
    }, "pct_input");

    bindOnce(inputEl, "blur", () => {
      if (String(inputEl.value ?? "") === "" || String(inputEl.value ?? "") === "-") inputEl.value = "0";
      onCommit?.();
    }, "pct_blur");
  }

  // ✅ -85 ~ 0 강제(양수 입력해도 blur에서 음수로)
  function enableNegPctRange(inputEl, minNeg, maxNeg, onCommit) {
    if (!inputEl) return;

    bindOnce(inputEl, "input", () => {
      // 입력 중에는 숫자/마이너스만 허용
      inputEl.value = String(inputEl.value ?? "").replace(/[^0-9\-]/g, "");
      onCommit?.();
    }, "neg_input");

    bindOnce(inputEl, "blur", () => {
      let raw = String(inputEl.value ?? "").replace(/[^0-9\-]/g, "");
      if (raw === "" || raw === "-") raw = "0";

      let n = Number(raw);
      if (!Number.isFinite(n)) n = 0;

      if (n !== 0) n = -Math.abs(n);
      n = clamp(n, minNeg, maxNeg);

      inputEl.value = String(n);
      onCommit?.();
    }, "neg_blur");
  }

  function setCommaInputValue(id, valueNumber) {
    const el = $(id);
    if (!el) return;
    el.value = Number(valueNumber || 0).toLocaleString("ko-KR");
  }

  function makeUserBonusId(prefix) {
    return `${prefix}_user_${Date.now()}_${Math.random().toString(16).slice(2)}`;
  }

  /* -------------------------------
     Base tables
  ------------------------------- */
  const AIRDEF_BASE_HP_BY_AGE = {
    "디지털": 18360,
    "정보화": 23750,
    "드론": 27787,
    "자동화": 32100,
    "로봇공학": 38570,
  };

  const TACTIC_BASE_DMG_BY_LEVEL = {
    1: 4334, 2: 6535, 3: 6518, 4: 7178, 5: 9350, 6: 12155, 7: 24151, 8: 27071,
  };

  // 러시아/이집트 HP+ (레벨 동일 테이블)
  const ALLIANCE_HP_PCT_BY_LEVEL = { 1: 10, 2: 15, 3: 20, 4: 25, 5: 30, 6: 35, 7: 40, 8: 45 };
  // 몽골 파괴전술 DMG+ (레벨 동일 테이블)
  const ALLIANCE_TACTIC_PCT_BY_LEVEL = { 1: 10, 2: 15, 3: 20, 4: 25, 5: 30, 6: 35, 7: 40, 8: 45 };

  const ALLIANCE_EXTRA_OPTIONS = [
    { key: "lib", name: "[도서관] 연구:연맹 병력", pct: 10 },
    { key: "uni", name: "[유니버시티] 몬테수마 황제", pct: 30 },
    { key: "law", name: "[의회] 연맹훈련", pct: 30 },
  ];

  // 고정 HP 체크(방공시설)
  const FIXED_HP_CHECK_ITEMS = [
    { id: "hp_lib_airdef", pct: 20, name: "[도서관] 방공 HP +20%" },
    { id: "hp_uni_amelia", pct: 30, name: "[유니버시티] 아멜리아 에어하트 HP +30%" },
    { id: "hp_law_overwhelm", pct: 5, name: "[의회] 압도적인 사격 HP +5%" },
  ];

  const GUILD_LEVEL_HP_PARTS = [
    { id: "g2",  label: "길드 레벨 2 (HP +10%)",  pct: 10 },
    { id: "g13", label: "길드 레벨 13 (HP +5%)", pct: 5 },
    { id: "g21", label: "길드 레벨 21 (HP +5%)", pct: 5 },
  ];

  // 고정 DMG 체크(파괴전술)
  const FIXED_DMG_CHECK_ITEMS = [
    { id: "dmg_lib_tactic", pct: 10, name: "[도서관] 연구:전술" },
    { id: "dmg_uni_suleiman", pct: 10, name: "[유니버시티] 쉘레이만 대제: 파괴 데미지" },
  ];

  /* -------------------------------
     Scout scan
  ------------------------------- */
  const SCOUT_PLANE_SCAN_OPTIONS = [
    { key: "scout_mk1_digital",  age: "디지털",  name: "정찰기 Mk 1",  pct: 230 },
    { key: "scout_mk2_digital",  age: "디지털",  name: "정찰기 Mk 2",  pct: 232 },
    { key: "scout_mk3_digital",  age: "디지털",  name: "정찰기 Mk 3",  pct: 234 },
    { key: "scout_mk4_digital",  age: "디지털",  name: "정찰기 Mk 4",  pct: 236 },
    { key: "scout_mk5_digital",  age: "디지털",  name: "정찰기 Mk 5",  pct: 238 },
    { key: "scout_mk6_digital",  age: "디지털",  name: "정찰기 Mk 6",  pct: 240 },

    { key: "supersonic_mk1_info", age: "정보화", name: "초음속 정찰기 Mk 1", pct: 240 },
    { key: "supersonic_mk2_info", age: "정보화", name: "초음속 정찰기 Mk 2", pct: 242 },
    { key: "supersonic_mk3_info", age: "정보화", name: "초음속 정찰기 Mk 3", pct: 244 },
    { key: "supersonic_mk4_info", age: "정보화", name: "초음속 정찰기 Mk 4", pct: 246 },
    { key: "supersonic_mk5_info", age: "정보화", name: "초음속 정찰기 Mk 5", pct: 248 },
    { key: "supersonic_mk6_info", age: "정보화", name: "초음속 정찰기 Mk 6", pct: 250 },

    { key: "spearhead_mk1_drone", age: "드론", name: "스피어헤드 정찰기 Mk 1", pct: 250 },
    { key: "spearhead_mk2_drone", age: "드론", name: "스피어헤드 정찰기 Mk 2", pct: 250 },
    { key: "spearhead_mk3_drone", age: "드론", name: "스피어헤드 정찰기 Mk 3", pct: 250 },
    { key: "spearhead_mk4_drone", age: "드론", name: "스피어헤드 정찰기 Mk 4", pct: 250 },
    { key: "spearhead_mk5_drone", age: "드론", name: "스피어헤드 정찰기 Mk 5", pct: 250 },
    { key: "spearhead_mk6_drone", age: "드론", name: "스피어헤드 정찰기 Mk 6", pct: 250 },

    { key: "captains_mk1_auto", age: "자동화", name: "캡틴스 정찰기 Mk 1", pct: 250 },
    { key: "captains_mk2_auto", age: "자동화", name: "캡틴스 정찰기 Mk 2", pct: 250 },
    { key: "captains_mk3_auto", age: "자동화", name: "캡틴스 정찰기 Mk 3", pct: 250 },
    { key: "captains_mk4_auto", age: "자동화", name: "캡틴스 정찰기 Mk 4", pct: 250 },
    { key: "captains_mk5_auto", age: "자동화", name: "캡틴스 정찰기 Mk 5", pct: 250 },
    { key: "captains_mk6_auto", age: "자동화", name: "캡틴스 정찰기 Mk 6", pct: 250 },

    { key: "majors_mk1_robot",  age: "로봇공학", name: "메이저스 정찰기 Mk 1",  pct: 252 },
    { key: "majors_mk2_robot",  age: "로봇공학", name: "메이저스 정찰기 Mk 2",  pct: 252 },
    { key: "majors_mk3_robot",  age: "로봇공학", name: "메이저스 정찰기 Mk 3",  pct: 252 },
    { key: "majors_mk4_robot",  age: "로봇공학", name: "메이저스 정찰기 Mk 4",  pct: 252 },
    { key: "majors_mk5_robot",  age: "로봇공학", name: "메이저스 정찰기 Mk 5",  pct: 252 },
    { key: "majors_mk6_robot",  age: "로봇공학", name: "메이저스 정찰기 Mk 6",  pct: 252 },
    { key: "majors_mk7_robot",  age: "로봇공학", name: "메이저스 정찰기 Mk 7",  pct: 252 },
    { key: "majors_mk8_robot",  age: "로봇공학", name: "메이저스 정찰기 Mk 8",  pct: 252 },
    { key: "majors_mk9_robot",  age: "로봇공학", name: "메이저스 정찰기 Mk 9",  pct: 252 },
    { key: "majors_mk10_robot", age: "로봇공학", name: "메이저스 정찰기 Mk 10", pct: 252 },
  ];
  const SCOUT_PLANE_SCAN_MAP = Object.fromEntries(SCOUT_PLANE_SCAN_OPTIONS.map(o => [o.key, o]));
  const SCOUT_ALL_RESEARCH_PICK = "majors_mk10_robot"; // ✅ 일괄적용 시 최고값(252%)로 고정

  /* -------------------------------
     Manufacturing (방공시설)
  ------------------------------- */
  const MANU_EQUIP = {
    lre: {
      name: "L.R.E. 광학 장치",
      hpPctByLevel: { 3:4, 4:4, 7:6, 13:5, 15:5, 16:5, 18:5 },
      tacticReduceByLevel: {},
    },
    plating: {
      name: "강화 도금",
      hpPctByLevel: {
        2:3, 3:3, 4:3, 5:3,
        7:5, 8:5, 9:5,
        12:5, 13:5, 14:5, 15:5, 16:5, 17:5, 18:5, 19:5
      },
      tacticReduceByLevel: { 10: 5, 11: 7 },
    },
    bdar: {
      name: "B.D.A.R. 도구",
      hpPctByLevel: {
        2:5, 3:5, 4:5,
        8:7, 9:7,
        12:6, 14:6, 15:6, 17:6, 18:6
      },
      tacticReduceByLevel: { 20: 7 },
    },
  };

  let manuSlot1 = { equip: "", level: 0 };
  let manuSlot2 = { equip: "", level: 0 };

  /* -------------------------------
     "모든 연구 완료" 상태
  ------------------------------- */
  let allHpResearchOn = false;
  let allDmgResearchOn = false;

  /* -------------------------------
     Bonus lists (사용자 추가)
  ------------------------------- */
  let hpBonuses = [];
  let dmgBonuses = [];

  /* -------------------------------
     Recalc scheduler (포커스 끊김 방지)
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

  function renderBonusList(containerEl, bonuses, onChange) {
    if (!containerEl) return;
    containerEl.innerHTML = "";

    bonuses.forEach((b, idx) => {
      const row = document.createElement("div");
      row.className = "bonus-item";

      const name = document.createElement("input");
      name.type = "text";
      name.className = "input";
      name.value = b.name;

      const pct = document.createElement("input");
      pct.type = "text";
      pct.className = "input";
      pct.value = String(b.pct ?? "0");
      pct.inputMode = "numeric";
      pct.setAttribute("autocomplete", "off");

      row.appendChild(name);
      row.appendChild(pct);

      bindOnce(name, "input", () => {
        bonuses[idx].name = name.value;
        onChange(false);
      }, `bonus_name_${b.id}`);

      bindOnce(pct, "input", () => {
        pct.value = String(pct.value ?? "").replace(/[^\d\-]/g, "");
        bonuses[idx].pct = pct.value === "" ? "0" : pct.value;
        onChange(false);
      }, `bonus_pct_in_${b.id}`);

      bindOnce(pct, "blur", () => {
        const raw = String(pct.value ?? "").replace(/[^\d\-]/g, "");
        pct.value = raw === "" ? "0" : String(Math.max(-999, Math.min(999, Number(raw) || 0)));
        bonuses[idx].pct = pct.value;
        onChange(false);
      }, `bonus_pct_blur_${b.id}`);

      const del = document.createElement("button");
      del.className = "icon-btn";
      del.type = "button";
      del.textContent = "×";
      del.title = "삭제";

      bindOnce(del, "click", () => {
        bonuses.splice(idx, 1);
        onChange(true);
      }, `bonus_del_${b.id}`);

      row.appendChild(del);
      containerEl.appendChild(row);
    });
  }

  function sumBonusPct(bonuses) {
    return bonuses.reduce((acc, b) => acc + safeNum(b.pct), 0);
  }

  /* -------------------------------
     AUTO Mounts
  ------------------------------- */
  function mountHpAutoBoxes() {
    const mount = $("hpAutoMount");
    if (!mount) return;
    if (mount.dataset.mounted === "1") return;
    mount.dataset.mounted = "1";

    mount.innerHTML = `
      <!-- ✅ 모든 연구 완료(일괄 적용): 초록 텍스트 스타일은 .all-research-box로 통일 -->
      <div class="auto-box all-research-box" id="allHpResearchBox">
        <div class="auto-checks">
          <label class="check-item">
            <input type="checkbox" id="allHpResearchApply" />
            <span>모든 연구 완료 (일괄 적용)</span>
          </label>
        </div>
      </div>

      <div class="auto-box" id="fixedHpBox">
        <div class="auto-title">[AUTO] 연구/의회 HP+</div>
        <div class="auto-checks">
          ${FIXED_HP_CHECK_ITEMS.map(it => `
            <label class="check-item">
              <input type="checkbox" id="${it.id}" />
              <span>${it.name}</span>
            </label>
          `).join("")}
        </div>
        <div class="auto-sum">
          <span>합계</span>
          <b id="fixedHpAutoOut">0%</b>
        </div>
      </div>

      <div class="auto-box" id="guildHpBox">
        <div class="auto-title">[AUTO] 길드 레벨 HP+</div>
        <div class="auto-sub">달성한 길드레벨 모두 체크 (예시: 길드레벨 21 → 3개 모두 체크)</div>
        <div class="auto-checks">
          ${GUILD_LEVEL_HP_PARTS.map(p => `
            <label class="check-item">
              <input type="checkbox" id="guild_${p.id}" />
              <span>${p.label}</span>
            </label>
          `).join("")}
        </div>
        <div class="auto-sum">
          <span>합계</span>
          <b id="guildHpAutoOut">0%</b>
        </div>
      </div>

      <div class="auto-box" id="defAllianceHpBox">
        <div class="auto-title">[AUTO] 연맹(HP+)</div>

        <div class="auto-checks" style="display:grid; gap:10px;">
          <div>
            <label class="label">이집트 레벨</label>
            <select id="defEgyptLevel" class="input"></select>
          </div>

          <div>
            <label class="label">러시아 레벨</label>
            <select id="defRussiaLevel" class="input"></select>
          </div>

          <div class="auto-sub" style="margin-top:10px;">[AUTO] 연맹 추가 연구</div>
          <div class="auto-checks">
            ${ALLIANCE_EXTRA_OPTIONS.map(o => `
              <label class="check-item">
                <input type="checkbox" id="defhp_${o.key}" />
                <span>${o.name}</span>
              </label>
            `).join("")}
          </div>

          <!-- ✅ 요청사항: 합계 수치는 박스 최하단(추가 연구 아래) -->
          <div class="auto-sum" style="margin-top:10px;">
            <span>이집트 합계</span>
            <b id="defEgyptOut">0%</b>
          </div>
          <div class="auto-sum" style="margin-top:6px;">
            <span>러시아 합계</span>
            <b id="defRussiaOut">0%</b>
          </div>
        </div>
      </div>
    `;

    // 레벨 옵션 채우기
    const fillAllianceLevelSelect = (selId) => {
      const sel = $(selId);
      if (!sel) return;
      sel.innerHTML = "";
      sel.appendChild(new Option("적용 안함 (0%)", "0"));
      Object.keys(ALLIANCE_HP_PCT_BY_LEVEL).forEach(lvl => {
        sel.appendChild(new Option(`레벨 ${lvl}`, String(lvl)));
      });
      sel.value = "0";
    };
    fillAllianceLevelSelect("defEgyptLevel");
    fillAllianceLevelSelect("defRussiaLevel");
  }

  function mountHpCouncilRelicRows() {
    const mount = $("hpCouncilRelicMount");
    if (!mount) return;
    if (mount.dataset.mounted === "1") return;
    mount.dataset.mounted = "1";

    mount.innerHTML = `
      <div class="hp-rows">
        <div class="hp-rowbox hp-yellow">
          <div class="hp-rowbox-left">[수비수 협의회] 방공시설 HP</div>
          <input id="hp_def_council_airdef" class="hp-rowbox-right" value="0" />
        </div>

        <div class="hp-rowbox hp-yellow">
          <div class="hp-rowbox-left">[수비수 유물] 방공시설 HP</div>
          <input id="hp_def_relic_airdef" class="hp-rowbox-right" value="0" />
        </div>

        <div class="hp-rowbox hp-red">
          <div class="hp-rowbox-left">[공격수 유물] 모든 적 방어타워 -HP</div>
          <input id="hp_att_relic_enemy_tower" class="hp-rowbox-right" value="0" />
        </div>

        <div class="hp-rowbox-subdesc">[공격수 유물 허용 범위: 0 ~ -85]</div>
      </div>
    `;

    enablePctInput($("hp_def_council_airdef"), () => scheduleRecalc(false));
    enablePctInput($("hp_def_relic_airdef"), () => scheduleRecalc(false));
    enableNegPctRange($("hp_att_relic_enemy_tower"), -85, 0, () => scheduleRecalc(false));
  }

  function mountDmgAutoBoxes() {
    const mount = $("dmgAutoMount");
    if (!mount) return;
    if (mount.dataset.mounted === "1") return;
    mount.dataset.mounted = "1";

    mount.innerHTML = `
      <!-- ✅ 모든 연구 완료(일괄 적용) -->
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
              <input type="checkbox" id="${it.id}" />
              <span>${it.name}</span>
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
        <div class="auto-sum">
          <span>수치</span>
          <b id="scoutAutoOut">0%</b>
        </div>

        <div class="hp-rows" style="margin-top:10px;">
          <div class="hp-rowbox hp-yellow">
            <div class="hp-rowbox-left">[공격수 협의회] 정찰 스캔 데미지 보너스</div>
            <input id="dmg_att_council_scan" class="hp-rowbox-right" value="0" />
          </div>
        </div>
      </div>
    `;

    // mongol levels
    const mongolSel = $("mongolLevel");
    if (mongolSel) {
      mongolSel.innerHTML = "";
      mongolSel.appendChild(new Option("적용 안함 (0%)", "0"));
      Object.keys(ALLIANCE_TACTIC_PCT_BY_LEVEL).forEach((lvl) =>
        mongolSel.appendChild(new Option(`레벨 ${lvl}`, String(lvl)))
      );
      mongolSel.value = "0";
    }

    // scout select
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
          .filter(o => o.age === age)
          .forEach(o => scoutSel.appendChild(new Option(`${o.name} - ${o.age}`, o.key)));
      });
      scoutSel.value = "";
    }

    enablePctInput($("dmg_att_council_scan"), () => scheduleRecalc(false));
  }

  /* -------------------------------
     제조소 UI Mount
  ------------------------------- */
  function populateLevelSelect(id) {
    const sel = $(id);
    if (!sel) return;
    sel.innerHTML = "";
    sel.appendChild(new Option("없음", "0"));
    for (let i = 1; i <= 20; i++) sel.appendChild(new Option(`Lv ${i}`, String(i)));
    sel.value = "0";
  }

  function populateManuEquipSelects() {
    const build = (selId) => {
      const sel = $(selId);
      if (!sel) return;
      sel.innerHTML = "";
      sel.appendChild(new Option("없음", ""));
      Object.keys(MANU_EQUIP).forEach(key => sel.appendChild(new Option(MANU_EQUIP[key].name, key)));
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

    [...sel1.options].forEach(opt => {
      if (!opt.value) { opt.disabled = false; return; }
      opt.disabled = (opt.value === v2);
    });
    [...sel2.options].forEach(opt => {
      if (!opt.value) { opt.disabled = false; return; }
      opt.disabled = (opt.value === v1);
    });
  }

  function mountManuBox() {
    const mount = $("manuMount");
    if (!mount) return;
    if (mount.dataset.mounted === "1") return;
    mount.dataset.mounted = "1";

    mount.innerHTML = `
      <div class="auto-box" id="manuOuterBox">
        <div class="auto-title">제조소 장비 (최대 2개 / 중복 장착 불가)</div>

        <div class="grid2" style="grid-template-columns:minmax(0,1fr) 120px; gap:10px;">
          <div>
            <label class="label">슬롯 1 장비</label>
            <select id="manuEquip1" class="input"></select>
          </div>
          <div>
            <label class="label">장비 레벨</label>
            <select id="manuLevel1" class="input"></select>
          </div>
        </div>

        <div class="grid2" style="grid-template-columns:minmax(0,1fr) 120px; gap:10px; margin-top:10px;">
          <div>
            <label class="label">슬롯 2 장비</label>
            <select id="manuEquip2" class="input"></select>
          </div>
          <div>
            <label class="label">장비 레벨</label>
            <select id="manuLevel2" class="input"></select>
          </div>
        </div>

        <div class="auto-box" style="margin-top:12px;">
          <div class="auto-title">[AUTO] 파괴전술 피격 감소(제조소)</div>
          <div class="auto-sum">
            <span>합계</span>
            <b id="manuTacticReduceOut">0%</b>
          </div>
          <div class="hint">※ 정지 상태 관련 효과는 파괴전술 사용 시 항상 정지로 간주하여 자동 적용</div>
        </div>

        <div class="auto-box" style="margin-top:12px;">
          <div class="auto-title">연구 완료 여부</div>
          <div class="auto-checks">
            <label class="check-item">
              <input type="checkbox" id="research_ransom_olds" />
              <span>[유니버시티] 랜섬 E. 올즈 '건물 군수품 HP 보너스' 연구</span>
            </label>

            <label class="check-item">
              <input type="checkbox" id="research_fully_armed_defense" />
              <span>[도서관] '완전 무장된 방어' 연구</span>
            </label>
          </div>
        </div>

        <div class="auto-box" style="margin-top:12px;">
          <div class="auto-title">[AUTO] 제조소 조건 보너스</div>

          <div class="auto-checks" style="gap:10px;">
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
      </div>
    `;

    populateManuEquipSelects();
    populateLevelSelect("manuLevel1");
    populateLevelSelect("manuLevel2");

    manuSlot1 = { equip: "", level: 0 };
    manuSlot2 = { equip: "", level: 0 };

    bindOnce($("manuEquip1"), "change", () => {
      manuSlot1.equip = $("manuEquip1")?.value || "";
      if (!manuSlot1.equip) {
        manuSlot1.level = 0;
        $("manuLevel1").value = "0";
      }
      syncManuDuplicateBlock();
      scheduleRecalc(false);
    }, "manuEquip1_change");

    bindOnce($("manuEquip2"), "change", () => {
      manuSlot2.equip = $("manuEquip2")?.value || "";
      if (!manuSlot2.equip) {
        manuSlot2.level = 0;
        $("manuLevel2").value = "0";
      }
      syncManuDuplicateBlock();
      scheduleRecalc(false);
    }, "manuEquip2_change");

    bindOnce($("manuLevel1"), "change", () => {
      manuSlot1.level = Number($("manuLevel1")?.value || 0);
      if (!manuSlot1.equip) {
        manuSlot1.level = 0;
        $("manuLevel1").value = "0";
      }
      scheduleRecalc(false);
    }, "manuLevel1_change");

    bindOnce($("manuLevel2"), "change", () => {
      manuSlot2.level = Number($("manuLevel2")?.value || 0);
      if (!manuSlot2.equip) {
        manuSlot2.level = 0;
        $("manuLevel2").value = "0";
      }
      scheduleRecalc(false);
    }, "manuLevel2_change");

    bindOnce($("research_ransom_olds"), "change", () => scheduleRecalc(false), "ransom_change");
    bindOnce($("research_fully_armed_defense"), "change", () => scheduleRecalc(false), "fully_change");
  }

  /* -------------------------------
     제조소 계산
  ------------------------------- */
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

  function calcManuEffects() {
    const slots = [manuSlot1, manuSlot2];

    let hpPctSum = 0;
    let tacticReduce = 0;

    let equippedCount = 0;
    let lvl20Count = 0;

    slots.forEach((s) => {
      if (!s.equip || !s.level) return;
      equippedCount += 1;
      if (s.level === 20) lvl20Count += 1;

      const def = MANU_EQUIP[s.equip];
      if (!def) return;

      hpPctSum += (def.hpPctByLevel[s.level] || 0);
      tacticReduce += (def.tacticReduceByLevel[s.level] || 0);
    });

    const ransomResearchDone = !!$("research_ransom_olds")?.checked;
    const fullyArmedResearchDone = !!$("research_fully_armed_defense")?.checked;

    const ransomOk = ransomResearchDone && (lvl20Count > 0);
    const fullyArmedOk = fullyArmedResearchDone && (equippedCount === 2);

    if (ransomOk) hpPctSum += (lvl20Count * 10);
    if (fullyArmedOk) hpPctSum += 16;

    return { hpPctSum, tacticReduce, equippedCount, lvl20Count, ransomResearchDone, fullyArmedResearchDone };
  }

  function updateManuConditionUI(manu) {
    setCondRansomStatus($("cond_ransom_status"), manu?.lvl20Count || 0, !!manu?.ransomResearchDone);
    setCondStatus($("cond_fullyarmed_status"), !!(manu?.fullyArmedResearchDone && (manu?.equippedCount === 2)));

    const out = $("manuTacticReduceOut");
    if (out) out.textContent = `${manu?.tacticReduce || 0}%`;
  }

  /* -------------------------------
     Select options & reference
  ------------------------------- */
  function initSelectOptions() {
    const ageSel = $("enemyAgeHp");
    if (ageSel) {
      ageSel.innerHTML = "";
      ageSel.appendChild(new Option("— 선택 또는 직접 입력 —", ""));
      Object.keys(AIRDEF_BASE_HP_BY_AGE).forEach(age => ageSel.appendChild(new Option(age, age)));
      ageSel.value = "";
    }

    const levelSel = $("tacticLevel");
    if (levelSel) {
      levelSel.innerHTML = "";
      levelSel.appendChild(new Option("— 선택 안함 —", ""));
      Object.keys(TACTIC_BASE_DMG_BY_LEVEL).forEach(lvl => levelSel.appendChild(new Option(`레벨 ${lvl}`, String(lvl))));
      levelSel.value = "";
    }
  }

  function renderReferenceTables() {
    const el = $("tableAdvisorsAirdefHp");
    if (el) {
      el.textContent = [
        "로버트 더 브루스 +6%",
        "선덕여왕 +16%",
        "함무라비 +18%",
        "마리 퀴리 +20%",
        "미야모토 무사시 +6%",
        "부디카 +6%",
      ].join("\n");
    }
  }

  /* -------------------------------
     AUTO 합산
  ------------------------------- */
  function calcFixedHpSum() {
    let sum = 0;
    FIXED_HP_CHECK_ITEMS.forEach(it => { if ($(it.id)?.checked) sum += it.pct; });
    const out = $("fixedHpAutoOut");
    if (out) out.textContent = `${sum}%`;
    return sum;
  }

  function calcGuildHpSum() {
    const sum = GUILD_LEVEL_HP_PARTS.reduce((acc, p) => acc + ($(`guild_${p.id}`)?.checked ? p.pct : 0), 0);
    const out = $("guildHpAutoOut");
    if (out) out.textContent = `${sum}%`;
    return sum;
  }

  function calcAllianceFinalPctFromLevel(lvlStr, prefix) {
    const lvl = Number(lvlStr || 0);
    if (!lvl) return 0;

    const base = ALLIANCE_HP_PCT_BY_LEVEL[lvl] || 0;
    const extraSum = ALLIANCE_EXTRA_OPTIONS.reduce(
      (acc, o) => acc + ($(`${prefix}_${o.key}`)?.checked ? o.pct : 0),
      0
    );
    return Math.floor(base * (1 + extraSum / 100));
  }

  function calcDefAllianceHpSum() {
    const egyptPct  = calcAllianceFinalPctFromLevel($("defEgyptLevel")?.value, "defhp");
    const russiaPct = calcAllianceFinalPctFromLevel($("defRussiaLevel")?.value, "defhp");

    const eOut = $("defEgyptOut");
    if (eOut) eOut.textContent = `${egyptPct}%`;

    const rOut = $("defRussiaOut");
    if (rOut) rOut.textContent = `${russiaPct}%`;

    return egyptPct + russiaPct;
  }

  function calcCouncilRelicEnemyTowerSum() {
    const council = safeNum($("hp_def_council_airdef")?.value);
    const relic   = safeNum($("hp_def_relic_airdef")?.value);

    let attRelic = safeNum($("hp_att_relic_enemy_tower")?.value);
    if (attRelic !== 0) attRelic = -Math.abs(attRelic);
    attRelic = clamp(attRelic, -85, 0);

    return council + relic + attRelic;
  }

  function calcFixedDmgSum() {
    let sum = 0;
    FIXED_DMG_CHECK_ITEMS.forEach(it => { if ($(it.id)?.checked) sum += it.pct; });
    const out = $("fixedDmgAutoOut");
    if (out) out.textContent = `${sum}%`;
    return sum;
  }

  function calcMongolDmgSum() {
    const lvl = Number($("mongolLevel")?.value || 0);
    if (!lvl) {
      const out = $("mongolAutoOut");
      if (out) out.textContent = `0%`;
      return 0;
    }

    const base = ALLIANCE_TACTIC_PCT_BY_LEVEL[lvl] || 0;
    const extraSum = ALLIANCE_EXTRA_OPTIONS.reduce(
      (acc, o) => acc + ($(`mongol_${o.key}`)?.checked ? o.pct : 0),
      0
    );
    const pct = Math.floor(base * (1 + extraSum / 100));

    const out = $("mongolAutoOut");
    if (out) out.textContent = `${pct}%`;
    return pct;
  }

  function calcScoutScanSum() {
    const key = $("scoutPlane")?.value || "";
    const picked = key && key !== "__sep__" ? SCOUT_PLANE_SCAN_MAP[key] : null;
    const pct = picked ? picked.pct : 0;

    const out = $("scoutAutoOut");
    if (out) out.textContent = `${pct}%`;
    return pct;
  }

  /* -------------------------------
     모든 연구 완료 적용
  ------------------------------- */
  function applyAllHpResearchUI(on) {
    // ✅ 제조소 드롭다운 4개는 절대 건드리지 않음

    // 1) 고정 HP 체크
    FIXED_HP_CHECK_ITEMS.forEach(it => {
      const cb = $(it.id);
      if (cb) cb.checked = on;
    });

    // 2) 길드 체크
    GUILD_LEVEL_HP_PARTS.forEach(p => {
      const cb = $(`guild_${p.id}`);
      if (cb) cb.checked = on;
    });

    // 3) 연맹 레벨: 이집트/러시아 8 또는 0
    if ($("defEgyptLevel"))  $("defEgyptLevel").value  = on ? "8" : "0";
    if ($("defRussiaLevel")) $("defRussiaLevel").value = on ? "8" : "0";

    // 4) 연맹 추가 연구(3개)
    ALLIANCE_EXTRA_OPTIONS.forEach(o => {
      const cb = $(`defhp_${o.key}`);
      if (cb) cb.checked = on;
    });

    // 협의회/유물 입력칸 + 사용자 보너스는 일괄 적용 대상에서 제외
  }

  function applyAllDmgResearchUI(on) {
    // 1) 고정 DMG 체크
    FIXED_DMG_CHECK_ITEMS.forEach(it => {
      const cb = $(it.id);
      if (cb) cb.checked = on;
    });

    // 2) 몽골 레벨 8 또는 0
    if ($("mongolLevel")) $("mongolLevel").value = on ? "8" : "0";

    // 3) 몽골 추가 연구 3개
    ALLIANCE_EXTRA_OPTIONS.forEach(o => {
      const cb = $(`mongol_${o.key}`);
      if (cb) cb.checked = on;
    });

    // 4) 정찰기 스캔: 최고값(252%) 또는 해제
    if ($("scoutPlane")) $("scoutPlane").value = on ? SCOUT_ALL_RESEARCH_PICK : "";

    // 5) 정찰 스캔 협의회 입력칸은 일괄 적용 대상에서 제외 (원하면 여기서 처리)
  }

  function restoreAllResearchCheckboxes() {
    const hpAll = $("allHpResearchApply");
    if (hpAll) {
      hpAll.checked = !!allHpResearchOn;
      if (hpAll.checked) applyAllHpResearchUI(true);
    }

    const dmgAll = $("allDmgResearchApply");
    if (dmgAll) {
      dmgAll.checked = !!allDmgResearchOn;
      if (dmgAll.checked) applyAllDmgResearchUI(true);
    }
  }

  /* -------------------------------
     recalc (단일 소스)
  ------------------------------- */
  function recalc(rerenderBonuses) {
    if (rerenderBonuses) {
      const onChange = (needRerender) => scheduleRecalc(!!needRerender);
      renderBonusList($("hpBonusList"), hpBonuses, onChange);
      renderBonusList($("dmgBonusList"), dmgBonuses, onChange);
    }

    const baseHp = safeNum($("baseHp")?.value);
    const baseDmg = safeNum($("baseDmg")?.value);

    const manu = calcManuEffects();
    updateManuConditionUI(manu);

    // HP
    const hpAuto =
      calcFixedHpSum()
      + calcGuildHpSum()
      + calcDefAllianceHpSum()
      + calcCouncilRelicEnemyTowerSum()
      + (manu?.hpPctSum || 0);

    const hpUser = sumBonusPct(hpBonuses);
    const hpSumPct = hpAuto + hpUser;

    const totalHp = baseHp * (1 + hpSumPct / 100);
    if ($("hpBonusSum")) $("hpBonusSum").textContent = fmtPctInt(hpSumPct);
    if ($("totalHp")) $("totalHp").textContent = fmtInt(totalHp);

    // DMG
    const dmgAuto =
      calcFixedDmgSum()
      + calcMongolDmgSum()
      + calcScoutScanSum()
      + safeNum($("dmg_att_council_scan")?.value);

    const dmgUser = sumBonusPct(dmgBonuses);
    const dmgSumPct = dmgAuto + dmgUser;

    const totalDmg = baseDmg * (1 + dmgSumPct / 100);

    // 제조소 “피격 감소”는 파괴전술에만 적용
    const tacticReduce = (manu?.tacticReduce || 0);
    const dmgAfterReduce = totalDmg * (1 - tacticReduce / 100);

    if ($("dmgBonusSum")) $("dmgBonusSum").textContent = fmtPctInt(dmgSumPct);
    if ($("totalDmg")) $("totalDmg").textContent = fmtInt(totalDmg);

    // Need count
    const raw = dmgAfterReduce > 0 ? (totalHp / dmgAfterReduce) : NaN;
    if ($("needCountRaw")) $("needCountRaw").textContent = Number.isFinite(raw) ? raw.toFixed(2) : "-";
    if ($("needCountCeil")) $("needCountCeil").textContent = Number.isFinite(raw) ? Math.ceil(raw).toLocaleString("ko-KR") : "-";
  }

  /* -------------------------------
     Reset
  ------------------------------- */
  function resetHpSectionToZero() {
    setCommaInputValue("baseHp", 0);
    if ($("enemyAgeHp")) $("enemyAgeHp").value = "";

    // ✅ 모든 연구 완료 해제
    allHpResearchOn = false;
    if ($("allHpResearchApply")) $("allHpResearchApply").checked = false;

    // 연구/의회, 길드
    FIXED_HP_CHECK_ITEMS.forEach(it => { const cb = $(it.id); if (cb) cb.checked = false; });
    GUILD_LEVEL_HP_PARTS.forEach(p => { const cb = $(`guild_${p.id}`); if (cb) cb.checked = false; });

    // 연맹(HP+)
    if ($("defEgyptLevel"))  $("defEgyptLevel").value  = "0";
    if ($("defRussiaLevel")) $("defRussiaLevel").value = "0";
    ALLIANCE_EXTRA_OPTIONS.forEach(o => { const cb = $(`defhp_${o.key}`); if (cb) cb.checked = false; });

    // 협의회/유물/공격유물
    if ($("hp_def_council_airdef")) $("hp_def_council_airdef").value = "0";
    if ($("hp_def_relic_airdef"))   $("hp_def_relic_airdef").value = "0";
    if ($("hp_att_relic_enemy_tower")) $("hp_att_relic_enemy_tower").value = "0";

    // 제조소(요청사항대로 일괄적용에서도 제외, 초기화는 기존대로 0)
    manuSlot1 = { equip: "", level: 0 };
    manuSlot2 = { equip: "", level: 0 };
    if ($("manuEquip1")) $("manuEquip1").value = "";
    if ($("manuEquip2")) $("manuEquip2").value = "";
    if ($("manuLevel1")) $("manuLevel1").value = "0";
    if ($("manuLevel2")) $("manuLevel2").value = "0";
    if ($("research_ransom_olds")) $("research_ransom_olds").checked = false;
    if ($("research_fully_armed_defense")) $("research_fully_armed_defense").checked = false;

    hpBonuses = [];
    scheduleRecalc(true);
  }

  function resetDmgSectionToZero() {
    setCommaInputValue("baseDmg", 0);
    if ($("tacticLevel")) $("tacticLevel").value = "";

    // ✅ 모든 연구 완료 해제
    allDmgResearchOn = false;
    if ($("allDmgResearchApply")) $("allDmgResearchApply").checked = false;

    FIXED_DMG_CHECK_ITEMS.forEach(it => { const cb = $(it.id); if (cb) cb.checked = false; });

    if ($("mongolLevel")) $("mongolLevel").value = "0";
    ALLIANCE_EXTRA_OPTIONS.forEach(o => { const cb = $(`mongol_${o.key}`); if (cb) cb.checked = false; });

    if ($("scoutPlane")) $("scoutPlane").value = "";
    if ($("dmg_att_council_scan")) $("dmg_att_council_scan").value = "0";

    dmgBonuses = [];
    scheduleRecalc(true);
  }

  /* -------------------------------
     Events
  ------------------------------- */
  function wireEvents() {
    enableCommaFormatting($("baseHp"), () => scheduleRecalc(false));
    enableCommaFormatting($("baseDmg"), () => scheduleRecalc(false));

    bindOnce($("enemyAgeHp"), "change", (e) => {
      const age = e.target.value;
      setCommaInputValue("baseHp", age && AIRDEF_BASE_HP_BY_AGE[age] ? AIRDEF_BASE_HP_BY_AGE[age] : 0);
      scheduleRecalc(false);
    }, "enemyAgeHp_change");

    bindOnce($("tacticLevel"), "change", (e) => {
      const lvl = e.target.value;
      setCommaInputValue("baseDmg", (lvl && TACTIC_BASE_DMG_BY_LEVEL[lvl]) ? TACTIC_BASE_DMG_BY_LEVEL[lvl] : 0);
      scheduleRecalc(false);
    }, "tacticLevel_change");

    // ✅ 모든 연구 완료(HP)
    bindOnce($("allHpResearchApply"), "change", (e) => {
      const on = !!e.target.checked;
      allHpResearchOn = on;
      applyAllHpResearchUI(on);
      scheduleRecalc(false);
    }, "allHpResearchApply_change");

    // ✅ 모든 연구 완료(DMG)
    bindOnce($("allDmgResearchApply"), "change", (e) => {
      const on = !!e.target.checked;
      allDmgResearchOn = on;
      applyAllDmgResearchUI(on);
      scheduleRecalc(false);
    }, "allDmgResearchApply_change");

    // HP: 고정 체크
    FIXED_HP_CHECK_ITEMS.forEach(it => bindOnce($(it.id), "change", () => scheduleRecalc(false), `hp_fixed_${it.id}`));
    // HP: 길드 체크
    GUILD_LEVEL_HP_PARTS.forEach(p => bindOnce($(`guild_${p.id}`), "change", () => scheduleRecalc(false), `hp_guild_${p.id}`));
    // HP: 연맹
    bindOnce($("defEgyptLevel"), "change", () => scheduleRecalc(false), "defEgyptLevel_change");
    bindOnce($("defRussiaLevel"), "change", () => scheduleRecalc(false), "defRussiaLevel_change");
    ALLIANCE_EXTRA_OPTIONS.forEach(o => bindOnce($(`defhp_${o.key}`), "change", () => scheduleRecalc(false), `defhp_${o.key}`));

    // DMG: 고정 체크
    FIXED_DMG_CHECK_ITEMS.forEach(it => bindOnce($(it.id), "change", () => scheduleRecalc(false), `dmg_fixed_${it.id}`));
    // DMG: 몽골
    bindOnce($("mongolLevel"), "change", () => scheduleRecalc(false), "mongolLevel_change");
    ALLIANCE_EXTRA_OPTIONS.forEach(o => bindOnce($(`mongol_${o.key}`), "change", () => scheduleRecalc(false), `mongol_${o.key}`));
    // DMG: 정찰기 선택
    bindOnce($("scoutPlane"), "change", () => scheduleRecalc(false), "scoutPlane_change");

    // + 항목 추가
    bindOnce($("addHpBonus"), "click", () => {
      hpBonuses.push({ id: makeUserBonusId("hp"), name: "새 HP 보너스", pct: "0" });
      scheduleRecalc(true);
    }, "addHpBonus_click");

    bindOnce($("addDmgBonus"), "click", () => {
      dmgBonuses.push({ id: makeUserBonusId("dmg"), name: "새 DMG 보너스", pct: "0" });
      scheduleRecalc(true);
    }, "addDmgBonus_click");

    // 초기화
    bindOnce($("resetHpBonuses"), "click", resetHpSectionToZero, "resetHp_click");
    bindOnce($("resetDmgBonuses"), "click", resetDmgSectionToZero, "resetDmg_click");
  }

  /* -------------------------------
     Start
  ------------------------------- */
  (function start() {
    initSelectOptions();
    renderReferenceTables();

    mountHpAutoBoxes();
    mountHpCouncilRelicRows();
    mountManuBox();
    mountDmgAutoBoxes();

    setCommaInputValue("baseHp", 0);
    setCommaInputValue("baseDmg", 0);

    wireEvents();
    restoreAllResearchCheckboxes();
    scheduleRecalc(true);
  })();
})();
