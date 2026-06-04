/* detailView — mock dataset (realistic VN ecommerce, read-only insight)
   Money is VND (integer dong). Timestamps ICT (Asia/Ho_Chi_Minh).
   Cross-linked: customers.order_history[].code → orders[code].header.customer_id */
window.DV_DATA = (function () {

  /* ───────── CUSTOMERS ───────── */
  const customers = {
    "CUS-7781": {
      profile: {
        customer_id: "CUS-7781", full_name: "Nguyễn Minh Anh",
        customer_type: "RETAIL", value_group: "VIP", lifecycle_stage: "ACTIVE",
        phone: "0903 118 224", email: "minhanh.ng@gmail.com",
        address1: "27 Trần Hưng Đạo", ward: "P. Cầu Ông Lãnh", district: "Q.1",
        province: "TP. Hồ Chí Minh", country: "Việt Nam", geo_region: "HCMC",
        loyalty_points: 4820, birth_date: "1991-07-14", gender: "Nữ",
        first_order_date: "2024-02-09", last_order_date: "2026-05-18",
        lifespan_days: 829, created_at: "2024-01-22", recency_days: 12,
      },
      value: {
        ltv: 52_140_000, total_orders: 24, aov: 2_172_500, value_group: "VIP",
        total_gross_profit: 14_980_000, total_cogs: 28_640_000,
        avg_margin_pct: 30.6, cogs_coverage_pct: 83,
        returns_amount: 1_240_000, returns_count: 2,
        spend_trend: [1.1,1.4,0.9,1.6,2.1,1.8,2.4,2.0,2.6,2.2,3.0,2.8],
      },
      behavior: {
        recency_days: 12, frequency: 24, monetary: 52_140_000,
        lifecycle_stage: "ACTIVE", channel_preference: "SOCIAL",
        product_affinity: "FINE · JAPAN", payment_behavior: "COD",
        geo_region: "HCMC", customer_type: "RETAIL", cohort_month: "2024-02",
      },
      status_timeline: buildStrip("2024-06", 24, {
        churnTail: 0, atRiskAt: [11], newAt: 0, statusOverride: {},
      }),
      order_history: [
        { code: "HD00123", date: "2026-05-18 14:20", status: "COMPLETED", channel: "Shopee", seller: "Linh", total: 1_350_000, gp: 380_000, margin: 30.4, discount: 150_000, pay: "COD", ret: false, carrier: "GHN" },
        { code: "HD00251", date: "2026-05-09 22:10", status: "COMPLETED", channel: "Shopee", seller: "Linh", total: 442_800, gp: -42_000, margin: -10.2, discount: 150_000, pay: "COD", ret: false, carrier: "GHN" },
        { code: "HD00098", date: "2026-04-02 10:05", status: "COMPLETED", channel: "Facebook", seller: "Linh", total: 820_000, gp: 213_000, margin: 26.0, discount: 60_000, pay: "PREPAID", ret: true, carrier: "GHTK" },
        { code: "HD00210", date: "2026-03-19 21:48", status: "SHIPPED", channel: "TikTok US", seller: "Hà", total: 1_180_000, gp: 286_000, margin: 24.2, discount: 0, pay: "PREPAID", ret: false, carrier: "4PX", us: true },
        { code: "HD00071", date: "2026-02-08 09:12", status: "COMPLETED", channel: "Shopee", seller: "Linh", total: 2_640_000, gp: 712_000, margin: 28.1, discount: 220_000, pay: "COD", ret: false, carrier: "GHN" },
        { code: "HD00044", date: "2025-12-21 16:33", status: "COMPLETED", channel: "Website", seller: "Linh", total: 3_180_000, gp: 980_000, margin: 31.2, discount: 0, pay: "PREPAID", ret: false, carrier: "GHN" },
        { code: "HD00012", date: "2025-10-14 11:20", status: "RETURNED", channel: "Facebook", seller: "Hà", total: 540_000, gp: 120_000, margin: 22.0, discount: 40_000, pay: "COD", ret: true, carrier: "GHTK" },
      ],
      flags: { has_cogs: true, cogs_partial: true },
    },

    "CUS-4410": {
      profile: {
        customer_id: "CUS-4410", full_name: "Trần Bảo Long",
        customer_type: "RETAIL", value_group: "GOLD", lifecycle_stage: "AT_RISK",
        phone: "0938 552 017", email: "baolong.tran@outlook.com",
        address1: "112 Nguyễn Văn Cừ", ward: "P. An Hòa", district: "Q. Ninh Kiều",
        province: "Cần Thơ", country: "Việt Nam", geo_region: "Mekong Delta",
        loyalty_points: 1190, birth_date: "1986-03-02", gender: "Nam",
        first_order_date: "2024-08-30", last_order_date: "2026-02-11",
        lifespan_days: 530, created_at: "2024-08-12", recency_days: 108,
      },
      value: {
        ltv: 18_420_000, total_orders: 9, aov: 2_046_700, value_group: "GOLD",
        total_gross_profit: 4_510_000, total_cogs: 9_980_000,
        avg_margin_pct: 27.1, cogs_coverage_pct: 61,
        returns_amount: 1_240_000, returns_count: 2,
        spend_trend: [0.9,1.2,1.6,1.1,1.4,0.8,0.6,0.4,0.3,0.2,0.1,0.0],
      },
      behavior: {
        recency_days: 108, frequency: 9, monetary: 18_420_000,
        lifecycle_stage: "AT_RISK", channel_preference: "MARKETPLACE",
        product_affinity: "SERUM · KOREA", payment_behavior: "MIXED",
        geo_region: "Mekong Delta", customer_type: "RETAIL", cohort_month: "2024-08",
      },
      status_timeline: buildStrip("2024-06", 24, {
        churnTail: 2, atRiskAt: [18,19,20,21], newAt: 2, leadingNone: 2,
      }),
      order_history: [
        { code: "HD00076", date: "2026-02-11 13:40", status: "COMPLETED", channel: "Lazada", seller: "Trang", total: 1_690_000, gp: null, margin: null, discount: 90_000, pay: "COD", ret: true, carrier: "GHN", unverified: true },
        { code: "HD00059", date: "2025-11-03 19:22", status: "COMPLETED", channel: "Shopee", seller: "Trang", total: 2_240_000, gp: 604_000, margin: 27.0, discount: 120_000, pay: "PREPAID", ret: false, carrier: "GHTK" },
        { code: "HD00031", date: "2025-06-18 08:50", status: "COMPLETED", channel: "Shopee", seller: "Trang", total: 1_980_000, gp: 540_000, margin: 27.3, discount: 0, pay: "COD", ret: false, carrier: "GHN" },
      ],
      flags: { has_cogs: false, cogs_partial: true },
    },

    "CUS-9002": {
      profile: {
        customer_id: "CUS-9002", full_name: "Công ty TNHH Mỹ Phẩm Hồng Hà",
        customer_type: "WHOLESALE", value_group: "PLATINUM", lifecycle_stage: "ACTIVE",
        phone: "0287 305 990", email: "muahang@hongha-cosmetics.vn",
        address1: "Lô C12 KCN Tân Bình", ward: "P. Tây Thạnh", district: "Q. Tân Phú",
        province: "TP. Hồ Chí Minh", country: "Việt Nam", geo_region: "HCMC",
        loyalty_points: 0, birth_date: "—", gender: "—",
        first_order_date: "2023-05-04", last_order_date: "2026-05-26",
        lifespan_days: 1118, created_at: "2023-04-28", recency_days: 4,
      },
      value: {
        ltv: 486_200_000, total_orders: 142, aov: 3_424_000, value_group: "PLATINUM",
        total_gross_profit: 71_900_000, total_cogs: 392_400_000,
        avg_margin_pct: 17.4, cogs_coverage_pct: 94,
        returns_amount: 8_640_000, returns_count: 11,
        spend_trend: [3.0,3.4,3.1,3.8,4.2,3.9,4.4,4.0,4.6,4.2,5.0,4.8],
      },
      behavior: {
        recency_days: 4, frequency: 142, monetary: 486_200_000,
        lifecycle_stage: "ACTIVE", channel_preference: "DIRECT/B2B",
        product_affinity: "BULK · MIXED", payment_behavior: "PREPAID",
        geo_region: "HCMC", customer_type: "WHOLESALE", cohort_month: "2023-05",
      },
      status_timeline: null, // RETAIL only
      order_history: [
        { code: "HD09921", date: "2026-05-26 09:00", status: "PROCESSING", channel: "B2B Portal", seller: "Dũng", total: 42_800_000, gp: 7_120_000, margin: 16.6, discount: 1_200_000, pay: "PREPAID", ret: false, carrier: "Viettel Post" },
        { code: "HD09810", date: "2026-05-09 08:30", status: "COMPLETED", channel: "B2B Portal", seller: "Dũng", total: 38_400_000, gp: 6_900_000, margin: 17.9, discount: 0, pay: "PREPAID", ret: false, carrier: "Viettel Post" },
      ],
      flags: { has_cogs: true, cogs_partial: false },
    },
  };

  /* ───────── ORDERS ───────── */
  const orders = {
    "HD00123": order123(),
    "HD00098": order098(),
    "HD00210": order210US(),
    "HD00076": order076Unverified(),
    "HD00251": order251Loss(),
  };

  /* search index */
  const phoneIndex = {};
  Object.values(customers).forEach(c => {
    phoneIndex[norm(c.profile.phone)] = c.profile.customer_id;
    phoneIndex[c.profile.email.toLowerCase()] = c.profile.customer_id;
  });

  return { customers, orders, phoneIndex, norm };

  /* ===== helpers ===== */
  function norm(s){ return (s||"").replace(/[^0-9]/g,""); }

  function buildStrip(startMonth, n, opt){
    const out = []; let [y,m] = startMonth.split("-").map(Number);
    for (let i=0;i<n;i++){
      let st = "ACTIVE";
      if (opt.leadingNone && i < opt.leadingNone) st = "NONE";
      else if (opt.atRiskAt && opt.atRiskAt.includes(i)) st = "AT_RISK";
      if (opt.churnTail && i >= n - opt.churnTail) st = "CHURNED";
      const mm = String(m).padStart(2,"0");
      out.push({
        month: `${y}-${mm}`, status: st,
        is_new: i === (opt.newAt ?? -1),
        days_since: st==="NONE" ? null : (st==="CHURNED" ? 100 + (i)*3 : st==="AT_RISK" ? 55 + i : 8 + (i%20)),
        value_group: i > n*0.6 ? "VIP" : "GOLD",
      });
      m++; if (m>12){ m=1; y++; }
    }
    return out;
  }

  function order123(){
    return {
      header: {
        order_code: "HD00123", order_id: "4821",
        status: "COMPLETED", payment_status: "PAID", fulfillment_status: "SHIPPED",
        customer_id: "CUS-7781",
        created_at: "2026-05-18 14:20", first_shipped_at: "2026-05-19 09:40",
        completed_at: "2026-05-21 12:05", carrier: "GHN", cod_amount: 1_350_000,
        channel_name: "Shopee", seller: "Đỗ Mỹ Linh", creator: "Đỗ Mỹ Linh",
        team: "Online Sales A", branch: "Kho HCM — Tân Bình",
      },
      financial: {
        is_us: false,
        gross_revenue: 1_400_000, discount_amount: 150_000, net_revenue: 1_250_000,
        vat_amount: 100_000, total_collected: 1_350_000, cogs_amount: 870_000,
        gross_profit: 380_000, gross_margin_pct: 30.4,
        platform_fees: 60_000, channel_net_profit: 320_000, channel_net_margin_pct: 25.6,
        return_amount: 0,
        fees_breakdown: [
          { type: "service",      amount: 22_000 },
          { type: "payment",      amount: 15_000 },
          { type: "infra",        amount: 8_000  },
          { type: "voucher_xtra", amount: 10_000 },
          { type: "fee_tax",      amount: 5_000  },
        ],
      },
      flags: { is_us: false, has_cogs: true, has_platform_fees: true, has_returns: false },
      line_items: [
        { sku: "FN-CRM-050", name: "Kem dưỡng ẩm phục hồi", variant: "50ml", brand: "FINE", category: "Skincare", qty: 2, unit: 300_000, line: 600_000, disc: 60_000, dist: 72_000, weight: 180 },
        { sku: "FG-SRM-030", name: "Serum Vitamin C 12%", variant: "Large", brand: "FineGlow", category: "Skincare", qty: 1, unit: 650_000, line: 650_000, disc: 90_000, dist: 78_000, weight: 90 },
      ],
      cost_ledger: [
        { category: "COGS", subtotal: 870_000, rows: [
          { type: "cogs", amount: 870_000, source: "MISA", record: "voucher_no=HD00123", fee_source: "actual" },
        ]},
        { category: "PLATFORM_FEE", subtotal: 60_000, rows: [
          { type: "platform_service", amount: 22_000, source: "Shopee", record: "SF-9921", fee_source: "estimated" },
          { type: "platform_payment", amount: 15_000, source: "Shopee", record: "PF-2210", fee_source: "estimated" },
          { type: "platform_infra",   amount: 8_000,  source: "Shopee", record: "IF-0044", fee_source: "estimated" },
          { type: "voucher_xtra",      amount: 10_000, source: "Shopee", record: "VX-7781", fee_source: "actual" },
          { type: "fee_tax",           amount: 5_000,  source: "Shopee", record: "FT-0001", fee_source: "estimated" },
        ]},
        { category: "TAX", subtotal: 100_000, rows: [
          { type: "vat_output", amount: 100_000, source: "Sapo", record: "INV-44821", fee_source: "actual" },
        ]},
        { category: "SHIPPING", subtotal: 30_000, rows: [
          { type: "freight", amount: 30_000, source: "GHN", record: "GHN-558210", fee_source: "actual" },
        ]},
        { category: "DISCOUNT", subtotal: 150_000, rows: [
          { type: "bundle_discount", amount: 150_000, source: "Sapo", record: "PROMO-MAY15", fee_source: "actual" },
        ]},
      ],
      payments: [
        { method: "COD (GHN thu hộ)", type: "COD", amount: 1_350_000, status: "PAID", ts: "2026-05-21 12:05", paid_on: "2026-05-21" },
      ],
      fulfillment: {
        carrier: "GHN", cod_amount: 1_350_000, ttc_hours: 70,
        province: "TP. Hồ Chí Minh", district: "Q.1", ward: "P. Cầu Ông Lãnh", country: "Việt Nam",
      },
      shipments: [
        { status: "SHIPPING", tracking_code: "GHTK20260527X8821", carrier: "GHTK", shipping_service: "Express",
          fulfillment_code: "FUN18250", shipped_at: "2026-05-27 08:15", delivered_at: null, cod_amount: 0, created_at: "2026-05-26 17:30" },
        { status: "DELIVERED", tracking_code: "GHN05582104567", carrier: "GHN", shipping_service: "Standard",
          fulfillment_code: "FUN18213", shipped_at: "2026-05-19 09:40", delivered_at: "2026-05-21 11:50", cod_amount: 1_350_000, created_at: "2026-05-18 20:10" },
      ],
      parties: {
        buyer_id: "CUS-7781", same: true, relation: null,
        recipient: {
          name: "Nguyễn Minh Anh", phone: "0903 118 224",
          address1: "27 Trần Hưng Đạo", ward: "P. Cầu Ông Lãnh", district: "Q.1",
          province: "TP. Hồ Chí Minh", country: "Việt Nam", note: null,
        },
      },
      returns: [],
      channel: {
        name: "Shopee", code: "SHP-VN", category: "Marketplace", format: "Online",
        platform: "Shopee", brand: "FINE Official", market: "Domestic",
        promo_codes: ["MAY15"], max_discount_rate: 15, primary_discount_type: "Bundle",
      },
      timeline: [
        { kind: "good",  time: "2026-05-18 14:20", title: "Order created", meta: "afternoon · business hours · weekday" },
        { kind: "normal", time: "2026-05-19 09:40", title: "First shipped", meta: "carrier GHN · COD 1.350.000 ₫" },
        { kind: "normal", time: "2026-05-20 12:05", title: "Payment received", meta: "COD collected by GHN" },
        { kind: "good",  time: "2026-05-21 12:05", title: "Completed", meta: "time-to-complete 70h" },
      ],
    };
  }

  function order098(){
    return {
      header: {
        order_code: "HD00098", order_id: "4798",
        status: "COMPLETED", payment_status: "PAID", fulfillment_status: "DELIVERED",
        customer_id: "CUS-7781",
        created_at: "2026-04-02 10:05", first_shipped_at: "2026-04-02 18:10",
        completed_at: "2026-04-05 09:30", carrier: "GHTK", cod_amount: 0,
        channel_name: "Facebook", seller: "Đỗ Mỹ Linh", creator: "Đỗ Mỹ Linh",
        team: "Online Sales A", branch: "Kho HCM — Tân Bình",
      },
      financial: {
        is_us: false,
        gross_revenue: 880_000, discount_amount: 60_000, net_revenue: 820_000,
        vat_amount: 65_600, total_collected: 885_600, cogs_amount: 607_000,
        gross_profit: 213_000, gross_margin_pct: 26.0,
        platform_fees: 0, channel_net_profit: 213_000, channel_net_margin_pct: 26.0,
        return_amount: 180_000,
        fees_breakdown: [],
      },
      flags: { is_us: false, has_cogs: true, has_platform_fees: false, has_returns: true },
      line_items: [
        { sku: "FN-TON-200", name: "Nước hoa hồng cân bằng", variant: "200ml", brand: "FINE", category: "Skincare", qty: 1, unit: 420_000, line: 420_000, disc: 30_000, dist: 30_000, weight: 230 },
        { sku: "FG-MSK-005", name: "Mặt nạ ngủ dưỡng ẩm", variant: "Hộp 5", brand: "FineGlow", category: "Skincare", qty: 1, unit: 400_000, line: 400_000, disc: 30_000, dist: 30_000, weight: 120 },
      ],
      cost_ledger: [
        { category: "COGS", subtotal: 607_000, rows: [
          { type: "cogs", amount: 607_000, source: "MISA", record: "voucher_no=HD00098", fee_source: "actual" },
        ]},
        { category: "TAX", subtotal: 65_600, rows: [
          { type: "vat_output", amount: 65_600, source: "Sapo", record: "INV-44798", fee_source: "actual" },
        ]},
        { category: "SHIPPING", subtotal: 22_000, rows: [
          { type: "freight", amount: 22_000, source: "GHTK", record: "GHTK-220981", fee_source: "actual" },
        ]},
        { category: "DISCOUNT", subtotal: 60_000, rows: [
          { type: "voucher", amount: 60_000, source: "Sapo", record: "PROMO-APR", fee_source: "actual" },
        ]},
      ],
      payments: [
        { method: "Chuyển khoản (VCB)", type: "PREPAID", amount: 885_600, status: "PAID", ts: "2026-04-02 09:55", paid_on: "2026-04-02" },
      ],
      fulfillment: {
        carrier: "GHTK", cod_amount: 0, ttc_hours: 71,
        province: "TP. Hồ Chí Minh", district: "Q. Bình Thạnh", ward: "P. 22", country: "Việt Nam",
      },
      shipments: [
        { status: "DELIVERED", tracking_code: "S19884420SGN", carrier: "GHTK", shipping_service: "Standard",
          fulfillment_code: "FUN17988", shipped_at: "2026-04-02 18:10", delivered_at: "2026-04-05 09:30", cod_amount: 0, created_at: "2026-04-02 11:20" },
      ],
      parties: {
        buyer_id: "CUS-7781", same: false, relation: "GIFT",
        recipient: {
          name: "Phạm Thanh Tú", phone: "0907 442 318",
          address1: "85/3 Nguyễn Hữu Cảnh", ward: "P. 22", district: "Q. Bình Thạnh",
          province: "TP. Hồ Chí Minh", country: "Việt Nam",
          note: "Quà tặng — không kèm hóa đơn trong kiện hàng.",
        },
      },
      returns: [
        { refund_amount: 180_000, refund_status: "paid", return_status: "returned", return_date: "2026-04-08", return_quantity: 1, return_reason: "Sản phẩm khác mô tả" },
      ],
      channel: {
        name: "Facebook", code: "FB-SHOP", category: "Social", format: "Online",
        platform: "Facebook", brand: "FINE Official", market: "Domestic",
        promo_codes: ["APR"], max_discount_rate: 10, primary_discount_type: "Voucher",
      },
      timeline: [
        { kind: "good",  time: "2026-04-02 10:05", title: "Order created", meta: "morning · business hours · weekday" },
        { kind: "normal", time: "2026-04-02 09:55", title: "Payment received", meta: "bank transfer VCB · prepaid" },
        { kind: "normal", time: "2026-04-02 18:10", title: "First shipped", meta: "carrier GHTK" },
        { kind: "good",  time: "2026-04-05 09:30", title: "Completed", meta: "time-to-complete 71h" },
        { kind: "bad",   time: "2026-04-08 15:30", title: "Return accepted", meta: "refund 180.000 ₫ · 1 item · reference only" },
      ],
    };
  }

  function order210US(){
    return {
      header: {
        order_code: "HD00210", order_id: "5102",
        status: "SHIPPED", payment_status: "PAID", fulfillment_status: "IN_TRANSIT",
        customer_id: "CUS-7781",
        created_at: "2026-03-19 21:48", first_shipped_at: "2026-03-21 06:15",
        completed_at: null, carrier: "4PX", cod_amount: 0,
        channel_name: "TikTok Shop US", seller: "Phạm Thu Hà", creator: "Phạm Thu Hà",
        team: "CrossBorder", branch: "Kho HCM — Tân Bình",
      },
      financial: {
        is_us: true,
        us_revenue_excl_vat: 1_090_000, us_revenue_incl_vat: 1_180_000,
        us_line_item_count: 3, has_unpriced_sku: true,
        gross_revenue: 0, discount_amount: 0, net_revenue: 0,
        vat_amount: 90_000, total_collected: 1_180_000, cogs_amount: 804_000,
        gross_profit: 286_000, gross_margin_pct: 24.2,
        platform_fees: 0, channel_net_profit: 286_000, channel_net_margin_pct: 24.2,
        return_amount: 0,
        fees_breakdown: [],
      },
      flags: { is_us: true, has_cogs: true, has_platform_fees: false, has_returns: false },
      line_items: [
        { sku: "FN-CRM-050", name: "Recovery moisturizer", variant: "50ml", brand: "FINE", category: "Skincare", qty: 1, unit: 380_000, line: 380_000, disc: 0, dist: 0, weight: 180, us_price: "15.90 USD" },
        { sku: "FG-SRM-030", name: "Vitamin C serum 12%", variant: "Large", brand: "FineGlow", category: "Skincare", qty: 1, unit: 520_000, line: 520_000, disc: 0, dist: 0, weight: 90, us_price: "21.50 USD" },
        { sku: "FN-LIP-002", name: "Tinted lip balm", variant: "Rose", brand: "FINE", category: "Makeup", qty: 1, unit: 280_000, line: 280_000, disc: 0, dist: 0, weight: 30, us_price: null },
      ],
      cost_ledger: [
        { category: "COGS", subtotal: 804_000, rows: [
          { type: "cogs", amount: 804_000, source: "MISA", record: "voucher_no=HD00210", fee_source: "actual" },
        ]},
        { category: "TAX", subtotal: 90_000, rows: [
          { type: "us_sales_tax", amount: 90_000, source: "TikTok US", record: "TT-510201", fee_source: "estimated" },
        ]},
        { category: "SHIPPING", subtotal: 165_000, rows: [
          { type: "intl_freight", amount: 165_000, source: "4PX", record: "4PX-9920", fee_source: "actual" },
        ]},
      ],
      payments: [
        { method: "TikTok Wallet (USD)", type: "PREPAID", amount: 1_180_000, status: "PAID", ts: "2026-03-19 21:50", paid_on: "2026-03-20" },
      ],
      fulfillment: {
        carrier: "4PX", cod_amount: 0, ttc_hours: null,
        province: "California", district: "Alhambra", ward: "—", country: "United States",
      },
      shipments: [
        { status: "PACKED", tracking_code: "4PX9931US0012044", carrier: "4PX", shipping_service: "Intl · reship",
          fulfillment_code: "FUN51044", shipped_at: null, delivered_at: null, cod_amount: 0, created_at: "2026-05-22 10:05" },
        { status: "SHIPPING", tracking_code: "4PX9920US0011850", carrier: "4PX", shipping_service: "Intl · Standard",
          fulfillment_code: "FUN51021", shipped_at: "2026-03-21 06:15", delivered_at: null, cod_amount: 0, created_at: "2026-03-20 22:40" },
      ],
      parties: {
        buyer_id: "CUS-7781", same: false, relation: "CROSSBORDER",
        recipient: {
          name: "Jenny Pham", phone: "+1 (626) 555-0148",
          address1: "1240 S Garfield Ave", ward: "—", district: "Alhambra",
          province: "California", country: "United States",
          note: "Đơn xuyên biên — người nhận là khách cuối tại US.",
        },
      },
      returns: [],
      channel: {
        name: "TikTok Shop US", code: "TTS-US", category: "Marketplace", format: "Online · CrossBorder",
        platform: "TikTok", brand: "FINE Global", market: "Export",
        promo_codes: [], max_discount_rate: 0, primary_discount_type: "None",
      },
      timeline: [
        { kind: "good",  time: "2026-03-19 21:48", title: "Order created", meta: "night · off-hours · weekday" },
        { kind: "normal", time: "2026-03-19 21:50", title: "Payment received", meta: "TikTok Wallet · prepaid (USD)" },
        { kind: "normal", time: "2026-03-21 06:15", title: "First shipped", meta: "carrier 4PX · international" },
      ],
    };
  }

  function order076Unverified(){
    return {
      header: {
        order_code: "HD00076", order_id: "4690",
        status: "COMPLETED", payment_status: "PAID", fulfillment_status: "DELIVERED",
        customer_id: "CUS-4410",
        created_at: "2026-02-11 13:40", first_shipped_at: "2026-02-12 08:20",
        completed_at: "2026-02-15 17:10", carrier: "GHN", cod_amount: 1_690_000,
        channel_name: "Lazada", seller: "Vũ Thị Trang", creator: "Vũ Thị Trang",
        team: "Online Sales B", branch: "Kho Cần Thơ",
      },
      financial: {
        is_us: false,
        gross_revenue: 1_780_000, discount_amount: 90_000, net_revenue: 1_690_000,
        vat_amount: 135_200, total_collected: 1_825_200, cogs_amount: null,
        gross_profit: null, gross_margin_pct: null,
        platform_fees: 72_000, channel_net_profit: null, channel_net_margin_pct: null,
        return_amount: 0,
        fees_breakdown: [
          { type: "service", amount: 40_000 },
          { type: "payment", amount: 22_000 },
          { type: "infra",   amount: 10_000 },
        ],
      },
      flags: { is_us: false, has_cogs: false, has_platform_fees: true, has_returns: true },
      line_items: [
        { sku: "KR-SRM-100", name: "Serum dưỡng trắng Hàn Quốc", variant: "100ml", brand: "K-Beauty", category: "Skincare", qty: 2, unit: 890_000, line: 1_780_000, disc: 90_000, dist: 90_000, weight: 260 },
      ],
      cost_ledger: [
        { category: "PLATFORM_FEE", subtotal: 72_000, rows: [
          { type: "platform_service", amount: 40_000, source: "Lazada", record: "LZ-7711", fee_source: "estimated" },
          { type: "platform_payment", amount: 22_000, source: "Lazada", record: "LZP-2201", fee_source: "estimated" },
          { type: "platform_infra",   amount: 10_000, source: "Lazada", record: "LZI-0090", fee_source: "estimated" },
        ]},
        { category: "TAX", subtotal: 135_200, rows: [
          { type: "vat_output", amount: 135_200, source: "Sapo", record: "INV-44690", fee_source: "actual" },
        ]},
        { category: "SHIPPING", subtotal: 35_000, rows: [
          { type: "freight", amount: 35_000, source: "GHN", record: "GHN-447001", fee_source: "actual" },
        ]},
        { category: "DISCOUNT", subtotal: 90_000, rows: [
          { type: "voucher", amount: 90_000, source: "Sapo", record: "PROMO-FEB", fee_source: "actual" },
        ]},
      ],
      payments: [
        { method: "COD (GHN thu hộ)", type: "COD", amount: 1_690_000, status: "PAID", ts: "2026-02-15 17:10", paid_on: "2026-02-15" },
      ],
      fulfillment: {
        carrier: "GHN", cod_amount: 1_690_000, ttc_hours: 99,
        province: "Cần Thơ", district: "Q. Ninh Kiều", ward: "P. An Hòa", country: "Việt Nam",
      },
      shipments: [
        { status: "DELIVERED", tracking_code: "GHN04470012288", carrier: "GHN", shipping_service: "Standard",
          fulfillment_code: "FUN46901", shipped_at: "2026-02-12 08:20", delivered_at: "2026-02-15 17:10", cod_amount: 1_690_000, created_at: "2026-02-11 19:05" },
        { status: "CANCELLED", tracking_code: "GHTK20260211C0440", carrier: "GHTK", shipping_service: "Express",
          fulfillment_code: "FUN46870", shipped_at: null, delivered_at: null, cod_amount: 0, created_at: "2026-02-11 14:10" },
      ],
      parties: {
        buyer_id: "CUS-4410", same: true, relation: null,
        recipient: {
          name: "Trần Bảo Long", phone: "0938 552 017",
          address1: "112 Nguyễn Văn Cừ", ward: "P. An Hòa", district: "Q. Ninh Kiều",
          province: "Cần Thơ", country: "Việt Nam", note: null,
        },
      },
      returns: [
        { refund_amount: 901_309, refund_status: "unpaid", return_status: "cancelled", return_date: "2026-02-25", return_quantity: 1, return_reason: "" },
        { refund_amount: 1_240_000, refund_status: "paid", return_status: "returned", return_date: "2026-02-18", return_quantity: null, return_reason: "KHÁCH TRẢ HÀNG" },
      ],
      channel: {
        name: "Lazada", code: "LZD-VN", category: "Marketplace", format: "Online",
        platform: "Lazada", brand: "K-Beauty Store", market: "Domestic",
        promo_codes: ["FEB"], max_discount_rate: 8, primary_discount_type: "Voucher",
      },
      timeline: [
        { kind: "good",  time: "2026-02-11 13:40", title: "Order created", meta: "afternoon · business hours · weekday" },
        { kind: "normal", time: "2026-02-12 08:20", title: "First shipped", meta: "carrier GHN · COD 1.690.000 ₫" },
        { kind: "normal", time: "2026-02-15 17:10", title: "Payment received", meta: "COD collected" },
        { kind: "good",  time: "2026-02-15 17:10", title: "Completed", meta: "time-to-complete 99h" },
      ],
    };
  }

  /* A flash-sale order that looks fine at gross but loses money once
     platform fees land — the textbook reason the verdict anchors to
     channel NET profit, not gross. */
  function order251Loss(){
    return {
      header: {
        order_code: "HD00251", order_id: "5310",
        status: "COMPLETED", payment_status: "PAID", fulfillment_status: "DELIVERED",
        customer_id: "CUS-7781",
        created_at: "2026-05-09 22:10", first_shipped_at: "2026-05-10 11:05",
        completed_at: "2026-05-12 16:40", carrier: "GHN", cod_amount: 442_800,
        channel_name: "Shopee", seller: "Đỗ Mỹ Linh", creator: "Đỗ Mỹ Linh",
        team: "Online Sales A", branch: "Kho HCM — Tân Bình",
      },
      financial: {
        is_us: false,
        gross_revenue: 560_000, discount_amount: 150_000, net_revenue: 410_000,
        vat_amount: 32_800, total_collected: 442_800, cogs_amount: 380_000,
        gross_profit: 30_000, gross_margin_pct: 7.3,
        platform_fees: 72_000, channel_net_profit: -42_000, channel_net_margin_pct: -10.2,
        return_amount: 0,
        fees_breakdown: [
          { type: "service",      amount: 30_000 },
          { type: "payment",      amount: 13_000 },
          { type: "infra",        amount: 8_000  },
          { type: "voucher_xtra", amount: 18_000 },
          { type: "fee_tax",      amount: 3_000  },
        ],
      },
      flags: { is_us: false, has_cogs: true, has_platform_fees: true, has_returns: false },
      line_items: [
        { sku: "FN-CRM-050", name: "Kem dưỡng ẩm phục hồi", variant: "50ml", brand: "FINE", category: "Skincare", qty: 1, unit: 300_000, line: 300_000, disc: 80_000, dist: 80_000, weight: 180 },
        { sku: "FN-LIP-002", name: "Son dưỡng có màu", variant: "Rose", brand: "FINE", category: "Makeup", qty: 1, unit: 260_000, line: 260_000, disc: 70_000, dist: 70_000, weight: 30 },
      ],
      cost_ledger: [
        { category: "COGS", subtotal: 380_000, rows: [
          { type: "cogs", amount: 380_000, source: "MISA", record: "voucher_no=HD00251", fee_source: "actual" },
        ]},
        { category: "PLATFORM_FEE", subtotal: 72_000, rows: [
          { type: "platform_service", amount: 30_000, source: "Shopee", record: "SF-9988", fee_source: "estimated" },
          { type: "platform_payment", amount: 13_000, source: "Shopee", record: "PF-2255", fee_source: "estimated" },
          { type: "platform_infra",   amount: 8_000,  source: "Shopee", record: "IF-0051", fee_source: "estimated" },
          { type: "voucher_xtra",      amount: 18_000, source: "Shopee", record: "VX-8810", fee_source: "actual" },
          { type: "fee_tax",           amount: 3_000,  source: "Shopee", record: "FT-0099", fee_source: "estimated" },
        ]},
        { category: "TAX", subtotal: 32_800, rows: [
          { type: "vat_output", amount: 32_800, source: "Sapo", record: "INV-45310", fee_source: "actual" },
        ]},
        { category: "SHIPPING", subtotal: 28_000, rows: [
          { type: "freight", amount: 28_000, source: "GHN", record: "GHN-553102", fee_source: "actual" },
        ]},
        { category: "DISCOUNT", subtotal: 150_000, rows: [
          { type: "flash_discount", amount: 150_000, source: "Sapo", record: "PROMO-FLASH99", fee_source: "actual" },
        ]},
      ],
      payments: [
        { method: "COD (GHN thu hộ)", type: "COD", amount: 442_800, status: "PAID", ts: "2026-05-12 16:40", paid_on: "2026-05-12" },
      ],
      fulfillment: {
        carrier: "GHN", cod_amount: 442_800, ttc_hours: 66,
        province: "TP. Hồ Chí Minh", district: "Q.1", ward: "P. Cầu Ông Lãnh", country: "Việt Nam",
      },
      shipments: [
        { status: "DELIVERED", tracking_code: "GHN05531024891", carrier: "GHN", shipping_service: "Standard",
          fulfillment_code: "FUN53101", shipped_at: "2026-05-10 11:05", delivered_at: "2026-05-12 16:40", cod_amount: 442_800, created_at: "2026-05-09 22:40" },
      ],
      parties: {
        buyer_id: "CUS-7781", same: true, relation: null,
        recipient: {
          name: "Nguyễn Minh Anh", phone: "0903 118 224",
          address1: "27 Trần Hưng Đạo", ward: "P. Cầu Ông Lãnh", district: "Q.1",
          province: "TP. Hồ Chí Minh", country: "Việt Nam", note: null,
        },
      },
      returns: [],
      channel: {
        name: "Shopee", code: "SHP-VN", category: "Marketplace", format: "Online",
        platform: "Shopee", brand: "FINE Official", market: "Domestic",
        promo_codes: ["FLASH99"], max_discount_rate: 30, primary_discount_type: "Flash sale",
      },
      timeline: [
        { kind: "good",  time: "2026-05-09 22:10", title: "Order created", meta: "night · flash sale · weekday" },
        { kind: "normal", time: "2026-05-10 11:05", title: "First shipped", meta: "carrier GHN · COD 442.800 ₫" },
        { kind: "normal", time: "2026-05-12 16:40", title: "Payment received", meta: "COD collected by GHN" },
        { kind: "good",  time: "2026-05-12 16:40", title: "Completed", meta: "time-to-complete 66h" },
      ],
    };
  }
})();
