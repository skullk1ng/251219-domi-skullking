/* =========================================================
   Dominations Calculator - Crown Value / Package Efficiency
   file: crown.js
   ========================================================= */
(() => {
  "use strict";

  const $ = (id) => document.getElementById(id);

  /* -------------------------------
     Utils
  ------------------------------- */
  function safeNum(v) {
    const s = String(v ?? "").trim().replace(/,/g, "");
    const n = Number(s);
    return Number.isFinite(n) ? n : 0;
  }

  function fmtInt(n) {
    if (!Number.isFinite(n)) return "-";
    return Math.round(n).toLocaleString("ko-KR");
  }

  function fmtFloat(n, digits = 2) {
    if (!Number.isFinite(n)) return "-";
    return n.toLocaleString("ko-KR", {
      maximumFractionDigits: digits,
      minimumFractionDigits: digits,
    });
  }

  function bindOnce(el, evt, handler, key) {
    if (!el) return;
    const k = `bound_${evt}_${key || "1"}`;
    if (el.dataset[k] === "1") return;
    el.dataset[k] = "1";
    el.addEventListener(evt, handler);
  }

  function enableCommaInt(inputEl, onCommit) {
    if (!inputEl) return;

    bindOnce(inputEl, "focus", () => {
      inputEl.value = String(inputEl.value ?? "").replace(/,/g, "");
    }, "comma_focus");

    bindOnce(inputEl, "input", () => {
      inputEl.value = String(inputEl.value ?? "").replace(/[^\d]/g, "");
      onCommit?.();
    }, "comma_input");

    bindOnce(inputEl, "blur", () => {
      const raw = String(inputEl.value ?? "").replace(/,/g, "");
      inputEl.value = raw === "" ? "0" : Number(raw).toLocaleString("ko-KR");
      onCommit?.();
    }, "comma_blur");
  }

  /* -------------------------------
     Read-only base data (관리자 고정)
  ------------------------------- */
  const BASE = {
    web: {
      crowns: 180000,
      crownsUsd: 199.99,
      token: 420,
      tokenUsd: 99.99,
    },
    ingame: {
      token: 120,
      tokenCrowns: 8500,
    },
  };

  /* -------------------------------
     Speedup policy (고정)
     - 시간당 크라운 10 기준
  ------------------------------- */
  const SPEED_CROWNS_PER_HOUR = 10;

  /* -------------------------------
     Exchange rate (USD->KRW) + cache
  ------------------------------- */
  const RATE_CACHE_KEY = "crownCalc_usdKrw_cache_v1";
  const RATE_CACHE_MS = 60 * 60 * 1000;

  function setRateLoading(isLoading) {
    const row = $("rateRow");
    if (!row) return;
    row.classList.toggle("rate-loading", !!isLoading);
  }

  function setRateBtnDisabled(disabled) {
    const btn = $("btnRefreshRate");
    if (!btn) return;
    btn.disabled = !!disabled;
    btn.style.pointerEvents = disabled ? "none" : "";
    btn.style.opacity = disabled ? "0.6" : "";
  }

  function loadRateCache() {
    try {
      const raw = localStorage.getItem(RATE_CACHE_KEY);
      if (!raw) return null;
      const obj = JSON.parse(raw);
      if (!obj || !Number.isFinite(obj.rate) || !Number.isFinite(obj.ts)) return null;
      if (Date.now() - obj.ts > RATE_CACHE_MS) return null;
      return obj.rate;
    } catch {
      return null;
    }
  }

  function saveRateCache(rate) {
    try {
      localStorage.setItem(RATE_CACHE_KEY, JSON.stringify({ rate, ts: Date.now() }));
    } catch {}
  }

  async function fetchUsdKrwRate() {
    // 1) Frankfurter
    try {
      const url1 = "https://api.frankfurter.app/latest?from=USD&to=KRW";
      const res1 = await fetch(url1, { cache: "no-store" });
      if (res1.ok) {
        const data1 = await res1.json();
        const rate1 = Number(data1?.rates?.KRW);
        if (Number.isFinite(rate1) && rate1 > 0) return rate1;
      }
    } catch {}

    // 2) exchangerate.host fallback
    const url2 = "https://api.exchangerate.host/latest?base=USD&symbols=KRW";
    const res2 = await fetch(url2, { cache: "no-store" });
    if (!res2.ok) throw new Error("rate fetch failed");
    const data2 = await res2.json();
    const rate2 = Number(data2?.rates?.KRW);
    if (!Number.isFinite(rate2) || rate2 <= 0) throw new Error("rate invalid");
    return rate2;
  }

  async function applyAutoRate({ force = false } = {}) {
    const rateOut = $("outUsdKrwRate");
    if (!rateOut) return;

    if (!force) {
      const cached = loadRateCache();
      if (Number.isFinite(cached) && cached > 0) {
        rateOut.textContent = fmtFloat(cached, 2);
        recalc();
        return;
      }
    }

    // 로딩 모션 시작
    setRateLoading(true);
    setRateBtnDisabled(true);

    try {
      const rate = await fetchUsdKrwRate();
      rateOut.textContent = fmtFloat(rate, 2);
      saveRateCache(rate);
    } catch {
      // 실패하면 기존 값 유지, 없으면 "-"
      if (!rateOut.textContent) rateOut.textContent = "-";
    } finally {
      setRateLoading(false);
      setRateBtnDisabled(false);
      recalc();
    }
  }

  /* -------------------------------
     Recommend badge
     - 손익(%) 0 이상: 추천 / 미만: 비추천
  ------------------------------- */
  function setRecommendBadgeByPct(pct) {
    const el = $("outRecommendBadge");
    if (!el) return;

    const isGood = Number.isFinite(pct) && pct >= 0;

    el.classList.remove("is-good", "is-bad");
    el.classList.add(isGood ? "is-good" : "is-bad");
    el.textContent = isGood ? "추천" : "비추천";
  }

  /* -------------------------------
     Core recalculation
  ------------------------------- */
  function recalc() {
    // (A) 고정 기준값 출력
    if ($("outWebCrownUsd")) $("outWebCrownUsd").textContent = `${BASE.web.crownsUsd.toFixed(2)} USD`;

    if ($("outIngameTokenCrowns")) {
      $("outIngameTokenCrowns").textContent = `${BASE.ingame.tokenCrowns.toLocaleString("ko-KR")} 크라운`;
    }

    // 웹사이트 기준: crowns per USD
    const crownsPerUsd = BASE.web.crownsUsd > 0 ? BASE.web.crowns / BASE.web.crownsUsd : 0;

    // 인게임 기준: 토큰 1개당 크라운 가치
    const crownPerToken = BASE.ingame.token > 0 ? BASE.ingame.tokenCrowns / BASE.ingame.token : 0;

    // (환율)
    const usdKrw = safeNum($("outUsdKrwRate")?.textContent);

    // 인게임 토큰팩 USD 환산: (8,500 크라운) / (크라운/USD)
    const ingameTokenPackUsd = crownsPerUsd > 0 ? BASE.ingame.tokenCrowns / crownsPerUsd : 0;
    if ($("outIngameTokenUsd")) {
      $("outIngameTokenUsd").textContent = ingameTokenPackUsd > 0 ? `${fmtFloat(ingameTokenPackUsd, 2)} USD` : "-";
    }

    // (B) 입력값 읽기
    const priceKrw = safeNum($("pkgPriceKrw")?.value);
    const pkgCrowns = safeNum($("pkgCrowns")?.value);
    const pkgTokens = safeNum($("pkgTokens")?.value);
    const spdDays = safeNum($("pkgSpeedDays")?.value);
    const spdHours = safeNum($("pkgSpeedHours")?.value);

    // 가격 USD 자동환산
    const priceUsd = (usdKrw > 0) ? (priceKrw / usdKrw) : 0;
    if ($("outPkgPriceUsd")) {
      $("outPkgPriceUsd").textContent = (priceUsd > 0) ? `${fmtFloat(priceUsd, 2)} USD` : "-";
    }

    // 스피드업 총 시간
    const totalSpeedHours = Math.max(0, spdDays) * 24 + Math.max(0, spdHours);
    if ($("outSpeedTotalHours")) $("outSpeedTotalHours").textContent = `${fmtFloat(totalSpeedHours, 2)}h`;

    // (C) 패키지 가치(크라운) 계산
    const valueCrownsPart = Math.max(0, pkgCrowns);
    const valueTokenPart = Math.max(0, pkgTokens) * Math.max(0, crownPerToken);
    const valueSpeedPart = Math.max(0, totalSpeedHours) * SPEED_CROWNS_PER_HOUR;

    const pkgValueCrowns = valueCrownsPart + valueTokenPart + valueSpeedPart;

    if ($("outPkgValueCrowns")) $("outPkgValueCrowns").innerHTML =
  `${fmtInt(pkgValueCrowns)} <img src="./image/icon/crown.png" class="crown-icon" alt="crown">`;
    if ($("outValueCrownsPart")) $("outValueCrownsPart").innerHTML =
  `${fmtInt(pkgValueCrowns)} <img src="./image/icon/crown.png" class="crown-icon" alt="crown">`;
    if ($("outValueTokenPart")) $("outValueTokenPart").innerHTML =
  `${fmtInt(pkgValueCrowns)} <img src="./image/icon/crown.png" class="crown-icon" alt="crown">`;
    if ($("outValueSpeedPart")) $("outValueSpeedPart").innerHTML =
  `${fmtInt(pkgValueCrowns)} <img src="./image/icon/crown.png" class="crown-icon" alt="crown">`;

    // (D) 손익(%) 계산
    // baseline = 같은 돈으로(웹사이트 크라운 기준) 살 수 있는 크라운
    const baselineCrowns = (usdKrw > 0 && crownsPerUsd > 0 && priceKrw > 0)
      ? (priceKrw / usdKrw) * crownsPerUsd
      : 0;

    let diffPct = NaN;
    if (baselineCrowns > 0) {
      diffPct = ((pkgValueCrowns - baselineCrowns) / baselineCrowns) * 100;
    }

    if ($("outDiffPct")) {
      $("outDiffPct").textContent = Number.isFinite(diffPct) ? `${fmtFloat(diffPct, 2)}%` : "-";
    }

    // (E) 추천/비추천 캡슐
    // 손익(%) 기준: 0 이상 추천, 0 미만 비추천
    setRecommendBadgeByPct(diffPct);
  }

  /* -------------------------------
     Reset
  ------------------------------- */
  function resetAll() {
    if ($("pkgPriceKrw")) $("pkgPriceKrw").value = "0";
    if ($("pkgCrowns")) $("pkgCrowns").value = "0";
    if ($("pkgTokens")) $("pkgTokens").value = "0";
    if ($("pkgSpeedDays")) $("pkgSpeedDays").value = "0";
    if ($("pkgSpeedHours")) $("pkgSpeedHours").value = "0";
    recalc();
  }

  /* -------------------------------
     Wiring
  ------------------------------- */
  function bindHandlers() {
    enableCommaInt($("pkgPriceKrw"), recalc);
    enableCommaInt($("pkgCrowns"), recalc);
    enableCommaInt($("pkgTokens"), recalc);
    enableCommaInt($("pkgSpeedDays"), recalc);
    enableCommaInt($("pkgSpeedHours"), recalc);

    bindOnce($("btnResetAll"), "click", resetAll, "resetAll");

    bindOnce($("btnRefreshRate"), "click", () => applyAutoRate({ force: true }), "refreshRate");
  }

  /* -------------------------------
     Start
  ------------------------------- */
  (function start() {
    bindHandlers();
    applyAutoRate({ force: false });
    recalc();
  })();
})();
