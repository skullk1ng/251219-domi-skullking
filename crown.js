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

    bindOnce(
      inputEl,
      "focus",
      () => {
        inputEl.value = String(inputEl.value ?? "").replace(/,/g, "");
      },
      "comma_focus"
    );

    bindOnce(
      inputEl,
      "input",
      () => {
        inputEl.value = String(inputEl.value ?? "").replace(/[^\d]/g, "");
        onCommit?.();
      },
      "comma_input"
    );

    bindOnce(
      inputEl,
      "blur",
      () => {
        const raw = String(inputEl.value ?? "").replace(/,/g, "");
        inputEl.value = raw === "" ? "0" : Number(raw).toLocaleString("ko-KR");
        onCommit?.();
      },
      "comma_blur"
    );
  }

  /* -------------------------------
     Read-only base data (관리자 고정)
  ------------------------------- */
  const BASE = {
    web: {
      crowns: 225000,
      crownsUsd: 199.99,
    },
    ingame: {
      token: 120,
      tokenCrowns: 8500,
    },
  };

  /* -------------------------------
     Speedup policy (고정)
  ------------------------------- */
  const SPEED_CROWNS_PER_HOUR = 10;

  /* -------------------------------
     Exchange rate cache
  ------------------------------- */
  const RATE_CACHE_KEY = "crownCalc_fx_cache_v3";
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
      if (!obj || !Number.isFinite(obj.ts)) return null;
      if (Date.now() - obj.ts > RATE_CACHE_MS) return null;

      const usdKrw = Number(obj.usdKrw);
      const usdCny = Number(obj.usdCny);
      if (!Number.isFinite(usdKrw) || usdKrw <= 0) return null;
      if (!Number.isFinite(usdCny) || usdCny <= 0) return null;

      return { usdKrw, usdCny };
    } catch {
      return null;
    }
  }

  function saveRateCache({ usdKrw, usdCny }) {
    try {
      localStorage.setItem(
        RATE_CACHE_KEY,
        JSON.stringify({ usdKrw, usdCny, ts: Date.now() })
      );
    } catch {}
  }

  async function fetchFxRates() {
    // 1) Frankfurter (USD -> KRW,CNY)
    try {
      const url1 = "https://api.frankfurter.app/latest?from=USD&to=KRW,CNY";
      const res1 = await fetch(url1, { cache: "no-store" });
      if (res1.ok) {
        const data1 = await res1.json();
        const krw = Number(data1?.rates?.KRW);
        const cny = Number(data1?.rates?.CNY);
        if (Number.isFinite(krw) && krw > 0 && Number.isFinite(cny) && cny > 0) {
          return { usdKrw: krw, usdCny: cny };
        }
      }
    } catch {}

    // 2) fallback: exchangerate.host
    const url2 = "https://api.exchangerate.host/latest?base=USD&symbols=KRW,CNY";
    const res2 = await fetch(url2, { cache: "no-store" });
    if (!res2.ok) throw new Error("rate fetch failed");
    const data2 = await res2.json();
    const krw = Number(data2?.rates?.KRW);
    const cny = Number(data2?.rates?.CNY);
    if (!Number.isFinite(krw) || krw <= 0 || !Number.isFinite(cny) || cny <= 0) {
      throw new Error("rate invalid");
    }
    return { usdKrw: krw, usdCny: cny };
  }

  // FX: USD 기준 환율
  let FX = { usdKrw: 0, usdCny: 0 };

  // ✅ HTML 구조 유지: "1 USD =" + "KRW/CNY"는 고정, 숫자만 변경
  function renderRateTexts() {
    const krwNum = $("outUsdKrwNum");
    const cnyNum = $("outUsdCnyNum");
    if (krwNum) krwNum.textContent = FX.usdKrw > 0 ? fmtFloat(FX.usdKrw, 2) : "-";
    if (cnyNum) cnyNum.textContent = FX.usdCny > 0 ? fmtFloat(FX.usdCny, 4) : "-";
  }

  async function applyAutoRate({ force = false } = {}) {
    // ✅ 현재 HTML의 숫자 요소 존재 체크
    if (!($("outUsdKrwNum") && $("outUsdCnyNum"))) return;

    if (!force) {
      const cached = loadRateCache();
      if (cached?.usdKrw && cached?.usdCny) {
        FX = cached;
        renderRateTexts();
        recalc();
        return;
      }
    }

    setRateLoading(true);
    setRateBtnDisabled(true);

    try {
      const rates = await fetchFxRates();
      FX = rates;
      saveRateCache(rates);
      renderRateTexts();
    } catch {
      // 실패 시 기존 표시 유지
    } finally {
      setRateLoading(false);
      setRateBtnDisabled(false);
      recalc();
    }
  }

  /* -------------------------------
     Recommend badge
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
     value-with-icon 업데이트 헬퍼
  ------------------------------- */
  function setValueWithIcon(id, n) {
    const root = $(id);
    if (!root) return;

    const t = root.querySelector(".value-text");
    if (!t) {
      root.textContent = fmtInt(n);
      return;
    }
    t.textContent = fmtInt(n);
  }

  /* -------------------------------
     Core recalculation
  ------------------------------- */
  function recalc() {
    // (A) Standard
    if ($("outWebCrowns")) {
      $("outWebCrowns").textContent = `크라운 ${BASE.web.crowns.toLocaleString("ko-KR")}개`;
    }
    if ($("outWebCrownUsd")) {
      $("outWebCrownUsd").textContent = `${fmtFloat(BASE.web.crownsUsd, 2)} USD`;
    }

    if ($("outIngameTokenLabel")) {
      $("outIngameTokenLabel").textContent =
        `전설토큰 ${BASE.ingame.token.toLocaleString("ko-KR")}개`;
    }
    if ($("outIngameTokenCrowns")) {
      $("outIngameTokenCrowns").textContent =
        `${BASE.ingame.tokenCrowns.toLocaleString("ko-KR")} 크라운`;
    }

    const crownsPerUsd = BASE.web.crownsUsd > 0 ? BASE.web.crowns / BASE.web.crownsUsd : 0;
    const crownPerToken = BASE.ingame.token > 0 ? BASE.ingame.tokenCrowns / BASE.ingame.token : 0;

    const ingameTokenPackUsd = crownsPerUsd > 0 ? BASE.ingame.tokenCrowns / crownsPerUsd : 0;
    if ($("outIngameTokenUsd")) {
      $("outIngameTokenUsd").textContent =
        ingameTokenPackUsd > 0 ? `${fmtFloat(ingameTokenPackUsd, 2)} USD` : "-";
    }

    // (B) 가격 -> USD 자동 환산
    const price = safeNum($("pkgPrice")?.value);
    const cur = $("pkgCurrency")?.value || "KRW";

    let priceUsdFromInput = 0;
    if (price > 0) {
      if (cur === "USD") priceUsdFromInput = price;
      else if (cur === "KRW") priceUsdFromInput = FX.usdKrw > 0 ? price / FX.usdKrw : 0;
      else if (cur === "CNY") priceUsdFromInput = FX.usdCny > 0 ? price / FX.usdCny : 0;
    }

    if ($("outPkgPriceUsd")) {
      $("outPkgPriceUsd").textContent =
        priceUsdFromInput > 0 ? `${fmtFloat(priceUsdFromInput, 2)} USD` : "-";
    }

    // (C) 구성품 입력
    const pkgCrowns = safeNum($("pkgCrowns")?.value);
    const pkgTokens = safeNum($("pkgTokens")?.value);
    const spdDays = safeNum($("pkgSpeedDays")?.value);
    const spdHours = safeNum($("pkgSpeedHours")?.value);

    const totalSpeedHours = Math.max(0, spdDays) * 24 + Math.max(0, spdHours);
    if ($("outSpeedTotalHours")) {
      $("outSpeedTotalHours").textContent = `${fmtFloat(totalSpeedHours, 2)}h`;
    }

    // (D) 가치(크라운)
    const valueCrownsPart = Math.max(0, pkgCrowns);
    const valueTokenPart = Math.max(0, pkgTokens) * Math.max(0, crownPerToken);
    const valueSpeedPart = Math.max(0, totalSpeedHours) * SPEED_CROWNS_PER_HOUR;
    const pkgValueCrowns = valueCrownsPart + valueTokenPart + valueSpeedPart;

    setValueWithIcon("outPkgValueCrowns", pkgValueCrowns);
    setValueWithIcon("outValueCrownsPart", valueCrownsPart);
    setValueWithIcon("outValueTokenPart", valueTokenPart);
    setValueWithIcon("outValueSpeedPart", valueSpeedPart);

    // (E) 손익(%)
    const baselineCrowns =
      priceUsdFromInput > 0 && crownsPerUsd > 0 ? priceUsdFromInput * crownsPerUsd : 0;

    let diffPct = NaN;
    if (baselineCrowns > 0) {
      diffPct = ((pkgValueCrowns - baselineCrowns) / baselineCrowns) * 100;
    }

    if ($("outDiffPct")) {
      $("outDiffPct").textContent = Number.isFinite(diffPct) ? `${fmtFloat(diffPct, 2)}%` : "-";
    }

    setRecommendBadgeByPct(diffPct);
  }

  /* -------------------------------
     Reset
  ------------------------------- */
  function resetAll() {
    if ($("pkgPrice")) $("pkgPrice").value = "0";
    if ($("pkgCurrency")) $("pkgCurrency").value = "KRW";
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
    enableCommaInt($("pkgPrice"), recalc);
    bindOnce($("pkgCurrency"), "change", recalc, "pkgCurrency");

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
    renderRateTexts();              // 초기 표기(숫자만)
    applyAutoRate({ force: false }); // 캐시/실시간 환율
    recalc();
  })();
})();
