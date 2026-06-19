// ==UserScript==
// @name         Sapo → Hug Claim button
// @namespace    fwg.hug
// @version      0.1.0
// @description  Inject a "Claim Hug" button on the Sapo order page that opens the Hug claim station pre-filled with the order code.
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
  // ⚠️ ORDER_CODE extraction is UNVERIFIED against the live Sapo DOM. Two
  //   strategies are tried in order; tune ORDER_CODE_SELECTORS / URL_ORDER_RE
  //   once you can inspect a real order page.
  //     1. From the page URL  (Sapo order URLs are typically /admin/orders/<id>
  //        — that id is the internal order id, which MAY differ from the human
  //        order CODE "SOxxxx". If so, prefer the DOM selector below.)
  //     2. From a DOM element  (the visible order code heading, e.g. "#SON1234").
  // ─────────────────────────────────────────────────────────────────────────
  const CONFIG = {
    CLAIM_BASE: "https://crm.lan.fwg.vn/hug/claim",  // CRM app via Caddy (https, *.lan.fwg.vn)
    // Regex to pull a human order code from the URL path, if present.
    URL_ORDER_RE: /\/orders\/([A-Za-z0-9_-]+)/,
    // DOM selectors to try for the visible order code (first match wins).
    ORDER_CODE_SELECTORS: [
      '[data-order-code]',
      '.order-code',
      'h1.page-title',
      '.s-page-title',
    ],
    // If the extracted text contains a leading '#', strip it.
    STRIP_HASH: true,
  };

  function extractOrderCode() {
    // Strategy 2 (preferred): visible DOM order code.
    for (const sel of CONFIG.ORDER_CODE_SELECTORS) {
      const el = document.querySelector(sel);
      if (!el) continue;
      const attr = el.getAttribute && el.getAttribute("data-order-code");
      let txt = (attr || el.textContent || "").trim();
      // Pull a token that looks like an order code (letters+digits).
      const m = txt.match(/#?\s*([A-Za-z]{1,4}\d{3,})/);
      if (m) return CONFIG.STRIP_HASH ? m[1] : m[0].trim();
    }
    // Strategy 1 (fallback): from the URL.
    const um = location.pathname.match(CONFIG.URL_ORDER_RE);
    if (um) return um[1];
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
