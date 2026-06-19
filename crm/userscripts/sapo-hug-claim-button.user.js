// ==UserScript==
// @name         Sapo → Hug Claim button
// @namespace    fwg.hug
// @version      0.2.0
// @description  Inject a "Claim Hug" button on the Sapo order page that opens the Hug claim station pre-filled with the order code.
// @match        https://*.mysapogo.com/admin/orders/*
// @match        https://*.mysapo.net/admin/orders/*
// @match        https://*.sapo.vn/admin/orders/*
// @match        https://*.sapogo.com/admin/orders/*
// @run-at       document-idle
// @grant        none
// ==/UserScript==

(function () {
  "use strict";

  // ─────────────────────────────────────────────────────────────────────────
  // CONFIG — adjust these to your environment.
  //
  // CLAIM_BASE: LAN URL of the Hug claim station (the CRM app). The button opens
  //   `${CLAIM_BASE}?order=<orderCode>`. Change to your CRM host/port.
  //
  // ORDER_CODE extraction: primary selector `.detail_order h4` (confirmed on the
  //   live Sapo order page = the visible order-code heading). Other selectors +
  //   the URL are kept as fallbacks. The code must match fact_orders.order_code.
  // ─────────────────────────────────────────────────────────────────────────
  const CONFIG = {
    CLAIM_BASE: "https://crm.lan.fwg.vn/hug/claim",  // CRM app via Caddy (https, *.lan.fwg.vn)
    // DOM selectors to try for the visible order code (first match wins).
    ORDER_CODE_SELECTORS: [
      '.detail_order h4',   // ← confirmed: order-code heading on the Sapo order page
      '[data-order-code]',
      '.order-code',
      'h1.page-title',
      '.s-page-title',
    ],
    // Fallback only: pull an order code from the URL path if the DOM misses.
    URL_ORDER_RE: /\/orders\/([A-Za-z0-9_-]+)/,
  };

  function extractOrderCode() {
    for (const sel of CONFIG.ORDER_CODE_SELECTORS) {
      const el = document.querySelector(sel);
      if (!el) continue;
      const attr = el.getAttribute && el.getAttribute("data-order-code");
      // Take the heading text, strip a leading '#', collapse whitespace.
      let txt = (attr || el.textContent || "").trim().replace(/^#\s*/, "");
      if (!txt) continue;
      // Single token (no spaces) → it IS the order code (e.g. "SON00123").
      if (!/\s/.test(txt)) return txt;
      // Mixed text (e.g. "Đơn hàng SON00123") → first token containing a digit.
      const m = txt.match(/([A-Za-z0-9._-]*\d[A-Za-z0-9._-]*)/);
      if (m) return m[1];
    }
    // URL fallback ONLY if it looks like a human code (contains a letter).
    // This Sapo's /admin/orders/<id> is a numeric INTERNAL id (≠ order_code),
    // so pure digits are skipped → button shows blank, staff types the code.
    const um = location.pathname.match(CONFIG.URL_ORDER_RE);
    if (um && /[A-Za-z]/.test(um[1])) return um[1];
    return "";
  }

  function injectButton() {
    if (document.getElementById("hug-claim-btn")) return; // already injected
    const orderCode = extractOrderCode();

    const btn = document.createElement("a");
    btn.id = "hug-claim-btn";
    btn.textContent = orderCode ? `Claim Hug · ${orderCode}` : "Claim Hug";
    btn.href = `${CONFIG.CLAIM_BASE}?order=${encodeURIComponent(orderCode)}`;
    btn.target = "_blank";
    btn.rel = "noopener";
    Object.assign(btn.style, {
      position: "fixed",
      right: "20px",
      bottom: "20px",
      zIndex: 99999,
      padding: "12px 18px",
      background: "#0ea5e9",
      color: "#fff",
      fontFamily: "system-ui, sans-serif",
      fontSize: "14px",
      fontWeight: "600",
      borderRadius: "10px",
      boxShadow: "0 6px 20px rgba(2,132,199,.4)",
      textDecoration: "none",
      cursor: "pointer",
    });
    if (!orderCode) {
      btn.title = "Order code not detected — adjust ORDER_CODE_SELECTORS in the userscript.";
      btn.style.background = "#94a3b8";
    }
    document.body.appendChild(btn);
  }

  // Sapo admin is an SPA — re-inject when navigating between orders.
  injectButton();
  let lastPath = location.pathname;
  setInterval(() => {
    if (location.pathname !== lastPath) {
      lastPath = location.pathname;
      const old = document.getElementById("hug-claim-btn");
      if (old) old.remove();
      setTimeout(injectButton, 600); // let the SPA render the new order
    }
  }, 800);
})();
