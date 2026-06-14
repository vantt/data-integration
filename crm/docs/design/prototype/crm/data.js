/* ============================================================
   CRM mock data — single source of truth for the prototype.
   Vietnamese retail CRM. All timestamps stored UTC; UI shows ICT.
   Exposed on window.DB.
   ============================================================ */
(function () {
  // ── App users ───────────────────────────────────────────
  const users = [
    { id: "u_nva", name: "NV A — Phạm Minh", short: "NV A", role: "sales", initials: "PM" },
    { id: "u_nvb", name: "NV B — Đỗ Hồng", short: "NV B", role: "sales", initials: "ĐH" },
    { id: "u_cska", name: "CSKH A — Lê Vy", short: "CSKH A", role: "care", initials: "LV" },
    { id: "u_cskb", name: "CSKH B — Vũ Thanh", short: "CSKH B", role: "care", initials: "VT" },
    { id: "u_mgr", name: "Manager C — Trần Quân", short: "Manager C", role: "manager", initials: "TQ" },
    { id: "u_admin", name: "Admin — Nguyễn Sơn", short: "Admin", role: "admin", initials: "NS" },
  ];
  const ME = "u_nva";

  // ── Tags ────────────────────────────────────────────────
  const tags = [
    { id: "t_vip", name: "vip", label: "VIP", category: "segment", tone: "amber" },
    { id: "t_repeat", name: "repeat", label: "repeat", category: "behavior", tone: "moss" },
    { id: "t_sens", name: "da-nhay-cam", label: "da nhạy cảm", category: "profile", tone: "coral" },
    { id: "t_skin", name: "skin-care", label: "skin-care", category: "interest", tone: "default" },
    { id: "t_whole", name: "wholesale", label: "wholesale", category: "channel", tone: "default" },
    { id: "t_gift", name: "gift-buyer", label: "gift-buyer", category: "behavior", tone: "default" },
    { id: "t_price", name: "price-sensitive", label: "price-sensitive", category: "behavior", tone: "honey" },
    { id: "t_gold", name: "gold-q3", label: "gold-q3", category: "campaign", tone: "amber" },
  ];

  // ── Parties (customers) ─────────────────────────────────
  // value_group: GOLD/VIP/SILVER/NEW ; status: active/at_risk/churned
  const parties = [
    {
      id: "p_001", code: "CUS-7781", name: "Nguyễn Văn A", phone: "+84901234567",
      email: null, sapo: "SP-12345", group: "GOLD", status: "active", owner: "u_nva",
      consent: true, last_order: "2026-06-12", tags: ["t_vip", "t_repeat", "t_sens"],
      custom: { da_nhay_cam: true, nguon_kh: "Facebook", ngay_sinh: "1990-04-22" },
      insight: {
        recency_days: 28, frequency: 8, monetary: 18400000, ltv: 18400000,
        next_signal: "IMMINENT", discount_sens: "LOW", affinity: "Sữa rửa mặt gentle",
        has_cogs: true, margin_pct: 34.2, refreshed_at: "2026-06-14T00:15:00Z",
      },
      actions: [
        { action_id: "aq_1", type: "CALL_NOW", rationale: "Sắp hết hàng yêu thích — gọi ngay", value: 2400000 },
        { action_id: "aq_2", type: "REORDER_NUDGE", rationale: "Chu kỳ mua ~30 ngày, đã 28 ngày", value: 900000 },
      ],
    },
    {
      id: "p_002", code: "CUS-7782", name: "Trần Thị B", phone: "+84912345678",
      email: "tranb@example.com", sapo: "SP-12346", group: "VIP", status: "at_risk", owner: "u_nvb",
      consent: true, last_order: "2026-03-14", tags: ["t_vip", "t_gift"],
      custom: { nguon_kh: "Zalo" },
      insight: {
        recency_days: 92, frequency: 12, monetary: 31200000, ltv: 31200000,
        next_signal: "WANING", discount_sens: "MEDIUM", affinity: "Serum dưỡng ẩm",
        has_cogs: true, margin_pct: 29.8, refreshed_at: "2026-06-14T00:15:00Z",
      },
      actions: [
        { action_id: "aq_3", type: "WIN_BACK", rationale: "Chưa mua 92 ngày, nhóm GOLD trước đây", value: 1800000 },
      ],
    },
    {
      id: "p_003", code: "CUS-7783", name: "Lê Văn C", phone: "+84923456789",
      email: null, sapo: "SP-12390", group: "NEW", status: "active", owner: null,
      consent: false, last_order: "2026-06-02", tags: ["t_skin"],
      custom: {},
      insight: {
        recency_days: 12, frequency: 1, monetary: 450000, ltv: 450000,
        next_signal: "UNKNOWN", discount_sens: "HIGH", affinity: "Kem chống nắng",
        has_cogs: false, margin_pct: null, refreshed_at: "2026-06-14T00:15:00Z",
      },
      actions: [],
    },
    {
      id: "p_004", code: "CUS-7790", name: "Phạm Thị D", phone: "+84908111222",
      email: "phamd@example.com", sapo: "SP-12410", group: "SILVER", status: "active", owner: "u_nva",
      consent: true, last_order: "2026-05-28", tags: ["t_repeat", "t_price"],
      custom: { nguon_kh: "Giới thiệu" },
      insight: {
        recency_days: 17, frequency: 5, monetary: 7300000, ltv: 7300000,
        next_signal: "STEADY", discount_sens: "HIGH", affinity: "Tẩy trang",
        has_cogs: true, margin_pct: 22.1, refreshed_at: "2026-06-14T00:15:00Z",
      },
      actions: [
        { action_id: "aq_4", type: "UPSELL", rationale: "Mua đều đặn — gợi ý combo cao cấp hơn", value: 600000 },
      ],
    },
    {
      id: "p_005", code: "CUS-7795", name: "Hoàng Minh E", phone: "+84934567890",
      email: null, sapo: "SP-12455", group: "GOLD", status: "active", owner: "u_nvb",
      consent: true, last_order: "2026-06-10", tags: ["t_vip", "t_whole"],
      custom: { nguon_kh: "Facebook", ghi_chu: "Mua sỉ cho spa" },
      insight: {
        recency_days: 4, frequency: 21, monetary: 54800000, ltv: 54800000,
        next_signal: "IMMINENT", discount_sens: "LOW", affinity: "Combo spa chuyên nghiệp",
        has_cogs: true, margin_pct: 38.6, refreshed_at: "2026-06-14T00:15:00Z",
      },
      actions: [
        { action_id: "aq_5", type: "CROSS_SELL", rationale: "Khách sỉ — gợi ý dòng máy hỗ trợ", value: 4200000 },
        { action_id: "aq_6", type: "LOYALTY_REWARD", rationale: "21 đơn — đề xuất ưu đãi thân thiết", value: 0 },
      ],
    },
    {
      id: "p_006", code: "CUS-7801", name: "Đặng Thị F", phone: "+84945678901",
      email: "dangf@example.com", sapo: "SP-12480", group: "SILVER", status: "churned", owner: null,
      consent: true, last_order: "2025-11-20", tags: ["t_price"],
      custom: {},
      insight: {
        recency_days: 206, frequency: 3, monetary: 3900000, ltv: 3900000,
        next_signal: "DORMANT", discount_sens: "HIGH", affinity: "Mặt nạ giấy",
        has_cogs: true, margin_pct: 19.4, refreshed_at: "2026-06-14T00:15:00Z",
      },
      actions: [
        { action_id: "aq_7", type: "WIN_BACK", rationale: "Churned 206 ngày — thử ưu đãi quay lại", value: 700000 },
      ],
    },
    {
      id: "p_007", code: "CUS-7808", name: "Bùi Văn G", phone: "+84956789012",
      email: null, sapo: "SP-12500", group: "NEW", status: "active", owner: "u_nva",
      consent: true, last_order: "2026-06-13", tags: [],
      custom: { nguon_kh: "Facebook Ads" },
      insight: {
        recency_days: 1, frequency: 1, monetary: 320000, ltv: 320000,
        next_signal: "UNKNOWN", discount_sens: "MEDIUM", affinity: "—",
        has_cogs: false, margin_pct: null, refreshed_at: "2026-06-14T00:15:00Z",
      },
      actions: [],
    },
    {
      id: "p_008", code: "CUS-7812", name: "Vũ Thị H", phone: "+84967890123",
      email: "vuh@example.com", sapo: "SP-12521", group: "VIP", status: "active", owner: "u_nvb",
      consent: true, last_order: "2026-06-09", tags: ["t_vip", "t_skin", "t_repeat"],
      custom: { nguon_kh: "Instagram", da_nhay_cam: false },
      insight: {
        recency_days: 5, frequency: 14, monetary: 27600000, ltv: 27600000,
        next_signal: "STEADY", discount_sens: "LOW", affinity: "Toner cấp ẩm",
        has_cogs: true, margin_pct: 31.5, refreshed_at: "2026-06-14T00:15:00Z",
      },
      actions: [
        { action_id: "aq_8", type: "REORDER_NUDGE", rationale: "Toner sắp hết theo chu kỳ", value: 480000 },
      ],
    },
    {
      id: "p_009", code: "CUS-7820", name: "Ngô Văn I", phone: "+84978901234",
      email: null, sapo: "SP-12544", group: "SILVER", status: "at_risk", owner: "u_nva",
      consent: false, last_order: "2026-04-01", tags: ["t_price"],
      custom: {},
      insight: {
        recency_days: 74, frequency: 4, monetary: 5100000, ltv: 5100000,
        next_signal: "WANING", discount_sens: "HIGH", affinity: "Sữa tắm",
        has_cogs: true, margin_pct: 20.7, refreshed_at: "2026-06-14T00:15:00Z",
      },
      actions: [],
    },
    {
      id: "p_010", code: "CUS-7833", name: "Dương Thị K", phone: "+84989012345",
      email: "duongk@example.com", sapo: "SP-12570", group: "GOLD", status: "active", owner: "u_nvb",
      consent: true, last_order: "2026-06-11", tags: ["t_vip", "t_gift", "t_gold"],
      custom: { nguon_kh: "Facebook", ngay_sinh: "1988-09-03" },
      insight: {
        recency_days: 3, frequency: 17, monetary: 42100000, ltv: 42100000,
        next_signal: "IMMINENT", discount_sens: "LOW", affinity: "Set quà cao cấp",
        has_cogs: true, margin_pct: 36.0, refreshed_at: "2026-06-14T00:15:00Z",
      },
      actions: [
        { action_id: "aq_9", type: "UPSELL", rationale: "Khách quà tặng — gợi ý set lễ giới hạn", value: 1500000 },
      ],
    },
  ];

  // ── Orders (cache.wh_order_hdr) keyed by customer ───────
  const orders = {
    p_001: [
      { code: "ORD-20060812", date: "2026-06-12", net: 1250000, status: "completed" },
      { code: "ORD-20060301", date: "2026-03-01", net: 2100000, status: "completed" },
      { code: "ORD-20051520", date: "2025-05-20", net: 850000, status: "completed" },
      { code: "ORD-20041210", date: "2025-04-12", net: 1640000, status: "completed" },
      { code: "ORD-20021118", date: "2025-02-11", net: 980000, status: "completed" },
    ],
    p_002: [
      { code: "ORD-20031412", date: "2026-03-14", net: 3200000, status: "completed" },
      { code: "ORD-20011820", date: "2026-01-18", net: 2800000, status: "completed" },
      { code: "ORD-19112210", date: "2025-11-22", net: 1900000, status: "completed" },
    ],
    p_005: [
      { code: "ORD-20061015", date: "2026-06-10", net: 8400000, status: "completed" },
      { code: "ORD-20052803", date: "2026-05-28", net: 6100000, status: "completed" },
      { code: "ORD-20050411", date: "2026-05-04", net: 7250000, status: "completed" },
      { code: "ORD-20041922", date: "2026-04-19", net: 5300000, status: "refunded" },
    ],
    p_010: [
      { code: "ORD-20061109", date: "2026-06-11", net: 4200000, status: "completed" },
      { code: "ORD-20050214", date: "2026-05-02", net: 3650000, status: "completed" },
    ],
  };

  // ── Activities / timeline (crm_activity) by customer ────
  const activities = {
    p_001: [
      { id: "a1", type: "call", at: "2026-06-13T03:32:00Z", user: "u_nva", text: "Khách xác nhận sẽ đặt tuần tới. Gợi ý SP mới dòng gentle.", order: null },
      { id: "a2", type: "chat", at: "2026-06-01T08:00:00Z", user: "u_cskb", text: "Đóng conversation PSID_abc — \"Đã giải quyết thắc mắc đơn hàng\"", conv: "c_001" },
      { id: "a3", type: "note", at: "2026-05-15T02:00:00Z", user: "u_nva", text: "Khách thích SP X, không thích chiết khấu thấp.", order: null },
      { id: "a4", type: "email", at: "2026-04-20T06:10:00Z", user: "u_nvb", text: "Gửi catalogue dòng mới qua email.", order: null },
    ],
    p_002: [
      { id: "a5", type: "call", at: "2026-03-15T07:00:00Z", user: "u_nvb", text: "Gọi nhắc đơn — khách bận, hẹn gọi lại.", order: null },
    ],
  };

  // ── Notes (crm_note) by customer ────────────────────────
  const notes = {
    p_001: [
      { id: "n1", user: "u_nva", at: "2026-06-13T03:45:00Z", text: "Khách da nhạy cảm, thích dòng gentle. Không dùng retinol." },
      { id: "n2", user: "u_cska", at: "2026-05-01T07:00:00Z", text: "Mua quà cho con gái — prefer gift wrap." },
    ],
    p_010: [
      { id: "n3", user: "u_nvb", at: "2026-06-11T04:10:00Z", text: "Khách quà tặng thường xuyên dịp lễ. Ưu tiên set giới hạn." },
    ],
  };

  // ── Tasks (crm_task) ────────────────────────────────────
  // status: open / doing / done / cancelled ; priority P1..P4
  const tasks = [
    { id: "tk_1", title: "Gọi ngay — sắp hết hàng yêu thích", party: "p_001", due: "2026-06-14T03:00:00Z", priority: "P1", assignee: "u_nva", status: "open", source: "action_queue", source_ref: "aq_1", note: "" },
    { id: "tk_2", title: "Win-back GOLD — chưa mua 92 ngày", party: "p_002", due: "2026-06-14T03:00:00Z", priority: "P2", assignee: "u_nvb", status: "open", source: "action_queue", source_ref: "aq_3", note: "" },
    { id: "tk_3", title: "Follow-up sau cuộc gọi", party: "p_001", due: "2026-06-20T03:00:00Z", priority: "P2", assignee: "u_nva", status: "open", source: "manual", source_ref: null, note: "Sau khi khách xác nhận đặt." },
    { id: "tk_4", title: "Gửi catalogue mới", party: "p_004", due: "2026-06-25T03:00:00Z", priority: "P3", assignee: "u_nva", status: "open", source: "manual", source_ref: null, note: "" },
    { id: "tk_5", title: "Follow-up A — combo cao cấp", party: "p_002", due: "2026-06-15T03:00:00Z", priority: "P2", assignee: "u_nvb", status: "doing", source: "manual", source_ref: null, note: "" },
    { id: "tk_6", title: "Gợi ý dòng máy cho khách sỉ", party: "p_005", due: "2026-06-16T03:00:00Z", priority: "P2", assignee: "u_nvb", status: "doing", source: "action_queue", source_ref: "aq_5", note: "" },
    { id: "tk_7", title: "Gọi giới thiệu SP X", party: "p_008", due: "2026-06-12T03:00:00Z", priority: "P3", assignee: "u_nvb", status: "done", source: "manual", source_ref: null, completed_at: "2026-06-12T08:00:00Z", note: "" },
    { id: "tk_8", title: "Gọi T. B nhắc lịch", party: "p_002", due: "2026-06-11T03:00:00Z", priority: "P3", assignee: "u_nvb", status: "done", source: "manual", source_ref: null, completed_at: "2026-06-11T09:30:00Z", note: "" },
    { id: "tk_9", title: "Nhắc đơn set quà giới hạn", party: "p_010", due: "2026-06-18T03:00:00Z", priority: "P2", assignee: "u_nvb", status: "open", source: "action_queue", source_ref: "aq_9", note: "" },
    { id: "tk_10", title: "Xác nhận địa chỉ giao spa", party: "p_005", due: "2026-06-19T03:00:00Z", priority: "P4", assignee: "u_nva", status: "open", source: "manual", source_ref: null, note: "" },
  ];

  // ── Conversations (crm_conversation) ────────────────────
  // status: open / pending / closed
  const conversations = [
    {
      id: "c_010", psid: "PSID_8f3a", party: null, status: "pending", assignee: "u_cskb",
      last_at: "2026-06-14T02:58:00Z", unread: 2, channel: "messenger",
      preview: "Cho mình hỏi đơn hàng hôm trước…",
      messages: [
        { from: "customer", at: "2026-06-14T02:55:00Z", text: "Chào shop, mình muốn hỏi về đơn đặt hôm trước ạ." },
        { from: "customer", at: "2026-06-14T02:58:00Z", text: "Đơn của mình bao giờ giao được shop nhỉ?" },
      ],
    },
    {
      id: "c_001", psid: "PSID_abc1", party: "p_001", status: "closed", assignee: "u_cskb",
      last_at: "2026-06-01T08:00:00Z", unread: 0, channel: "messenger",
      preview: "Cảm ơn shop nhiều ạ!",
      messages: [
        { from: "customer", at: "2026-06-01T07:40:00Z", text: "Tôi muốn hỏi về đơn ORD-20060812 ạ." },
        { from: "agent", at: "2026-06-01T07:45:00Z", text: "Dạ, đơn của anh đã giao thành công hôm 12/06. Anh kiểm tra giúp em nhé." },
        { from: "customer", at: "2026-06-01T07:58:00Z", text: "Ok shop, cảm ơn shop nhiều ạ!" },
      ],
    },
    {
      id: "c_002", psid: "PSID_kk22", party: "p_008", status: "open", assignee: "u_cska",
      last_at: "2026-06-13T10:20:00Z", unread: 1, channel: "messenger",
      preview: "Toner này còn hàng không shop?",
      messages: [
        { from: "customer", at: "2026-06-13T10:20:00Z", text: "Toner cấp ẩm còn hàng không shop?" },
      ],
    },
    {
      id: "c_003", psid: "PSID_zz09", party: null, status: "pending", assignee: null,
      last_at: "2026-06-13T06:05:00Z", unread: 3, channel: "messenger",
      preview: "Mình thấy quảng cáo trên Facebook…",
      messages: [
        { from: "customer", at: "2026-06-13T06:00:00Z", text: "Mình thấy quảng cáo trên Facebook về set chống nắng." },
        { from: "customer", at: "2026-06-13T06:03:00Z", text: "Giá bao nhiêu vậy shop?" },
        { from: "customer", at: "2026-06-13T06:05:00Z", text: "Có ship COD không ạ?" },
      ],
    },
    {
      id: "c_004", psid: "PSID_aa55", party: "p_010", status: "closed", assignee: "u_cska",
      last_at: "2026-05-02T07:15:00Z", unread: 0, channel: "messenger",
      preview: "Hỏi về chính sách đổi trả.",
      messages: [
        { from: "customer", at: "2026-05-02T07:10:00Z", text: "Shop cho hỏi chính sách đổi trả với ạ." },
        { from: "agent", at: "2026-05-02T07:14:00Z", text: "Dạ shop hỗ trợ đổi trả trong 7 ngày nếu còn nguyên seal ạ." },
      ],
    },
  ];

  // ── Dedup candidates (crm_dedup_candidate) ──────────────
  const dedup = [
    {
      id: "d_1", status: "pending", rule: "exact_phone",
      a: { id: "p_001", name: "Nguyễn Văn A", sapo: "SP-12345", phone: "+84901234567", email: null, orders: 5, activities: 4, tasks: 3 },
      b: { id: "p_x01", name: "NVA", sapo: "SP-19002", phone: "+84901234567", email: null, orders: 0, activities: 1, tasks: 0 },
    },
    {
      id: "d_2", status: "pending", rule: "fuzzy_name",
      a: { id: "p_002", name: "Trần Thị B", sapo: "SP-12346", phone: "+84912345678", email: "tranb@example.com", orders: 3, activities: 1, tasks: 2 },
      b: { id: "p_x02", name: "Tran B", sapo: "SP-18771", phone: "+84912340000", email: "tran.b@gmail.com", orders: 1, activities: 0, tasks: 0 },
    },
    {
      id: "d_3", status: "pending", rule: "fuzzy_name",
      a: { id: "p_008", name: "Vũ Thị H", sapo: "SP-12521", phone: "+84967890123", email: "vuh@example.com", orders: 6, activities: 2, tasks: 1 },
      b: { id: "p_x03", name: "Vu Thi Huong", sapo: "SP-17650", phone: "+84967890000", email: null, orders: 0, activities: 0, tasks: 0 },
    },
    {
      id: "d_4", status: "pending", rule: "exact_phone",
      a: { id: "p_005", name: "Hoàng Minh E", sapo: "SP-12455", phone: "+84934567890", email: null, orders: 4, activities: 0, tasks: 2 },
      b: { id: "p_x04", name: "Minh Hoàng (spa)", sapo: "SP-16001", phone: "+84934567890", email: "spa.minh@example.com", orders: 1, activities: 0, tasks: 0 },
    },
  ];

  // ── Segments (crm_segment) ──────────────────────────────
  const segments = [
    { id: "seg_1", name: "Win-back GOLD Q3", type: "dynamic", members: 87, excluded: 9, updated: "2026-06-14T00:20:00Z", status: "ready",
      rules: [{ field: "value_group", op: "=", val: "GOLD" }, { field: "customer_status", op: "=", val: "at_risk" }, { field: "recency_days", op: ">", val: "60" }] },
    { id: "seg_2", name: "Reactivation tháng 7", type: "dynamic", members: 34, excluded: 3, updated: "2026-06-14T00:20:00Z", status: "ready",
      rules: [{ field: "customer_status", op: "=", val: "churned" }, { field: "monetary_vnd", op: ">", val: "3000000" }] },
    { id: "seg_3", name: "VIP tặng quà — tháng 6", type: "static", members: 12, excluded: 0, updated: "2026-06-12T03:00:00Z", status: "ready",
      rules: [{ field: "tag", op: "=", val: "gift-buyer" }] },
    { id: "seg_4", name: "Upsell khách sỉ", type: "dynamic", members: 0, excluded: 5, updated: "2026-06-13T22:00:00Z", status: "empty",
      rules: [{ field: "tag", op: "=", val: "wholesale" }, { field: "next_purchase_signal", op: "=", val: "IMMINENT" }] },
    { id: "seg_5", name: "Khách mới — nuôi dưỡng", type: "dynamic", members: 56, excluded: 12, updated: "2026-06-14T00:20:00Z", status: "materializing",
      rules: [{ field: "value_group", op: "=", val: "NEW" }, { field: "consent_contact", op: "=", val: "true" }] },
  ];

  // ── Campaigns (crm_campaign) ────────────────────────────
  // objective: winback/reactivation/upsell/crosssell ; status: draft/active/done
  const campaigns = [
    {
      id: "cmp_1", name: "Win-back Q3", objective: "winback", channel: "messenger", segment: "seg_1",
      assignees: ["u_nva", "u_nvb"], scheduled: "2026-06-10T01:00:00Z", status: "active",
      targets_total: 87, sent: 43, responded: 21, converted: 13, revenue: 28500000,
    },
    {
      id: "cmp_2", name: "React-Jul-2026", objective: "reactivation", channel: "messenger", segment: "seg_2",
      assignees: ["u_nva"], scheduled: "2026-07-01T01:00:00Z", status: "draft",
      targets_total: 34, sent: 0, responded: 0, converted: 0, revenue: 0,
    },
    {
      id: "cmp_3", name: "Upsell VIP tháng 6", objective: "upsell", channel: "call", segment: "seg_3",
      assignees: ["u_nvb"], scheduled: "2026-06-05T01:00:00Z", status: "active",
      targets_total: 22, sent: 22, responded: 9, converted: 5, revenue: 11200000,
    },
  ];

  // ── Campaign targets (crm_campaign_target) by campaign ──
  // status: queued/sent/responded/converted/skipped
  const targets = {
    cmp_1: [
      { id: "tg_1", party: "p_002", status: "converted", assignee: "u_nva", order: "ORD-20060901", revenue: 3200000 },
      { id: "tg_2", party: "p_006", status: "queued", assignee: "u_nvb", order: null, revenue: 0 },
      { id: "tg_3", party: "p_009", status: "sent", assignee: "u_nva", order: null, revenue: 0 },
      { id: "tg_4", party: "p_001", status: "responded", assignee: "u_nva", order: null, revenue: 0 },
      { id: "tg_5", party: "p_010", status: "converted", assignee: "u_nvb", order: "ORD-20061109", revenue: 4200000 },
      { id: "tg_6", party: "p_004", status: "skipped", assignee: "u_nva", order: null, revenue: 0 },
    ],
    cmp_3: [
      { id: "tg_7", party: "p_008", status: "converted", assignee: "u_nvb", order: "ORD-20060702", revenue: 2400000 },
      { id: "tg_8", party: "p_005", status: "responded", assignee: "u_nvb", order: null, revenue: 0 },
      { id: "tg_9", party: "p_010", status: "sent", assignee: "u_nvb", order: null, revenue: 0 },
    ],
  };

  // ── Ad campaigns (crm_ad_spend / lead / attribution) ────
  const ads = [
    { id: "ad_1", name: "Summer-2026", platform: "facebook", spend: 5200000, leads: 42, converted: 8, cpc: 123800, cpl: 238000, revenue: 24000000,
      leadList: [
        { party: "p_007", name: "Bùi Văn G", at: "2026-06-13", converted: false },
        { party: "p_003", name: "Lê Văn C", at: "2026-06-02", converted: true },
      ] },
    { id: "ad_2", name: "Brand-June-2026", platform: "facebook", spend: 7100000, leads: 45, converted: 12, cpc: 98500, cpl: 157000, revenue: 24000000,
      leadList: [
        { party: null, name: "PSID_zz09 (chưa link)", at: "2026-06-13", converted: false },
      ] },
  ];

  // ── Custom field definitions (crm_custom_field_def) ─────
  const fieldDefs = [
    { id: "fd_1", name: "da_nhay_cam", label: "Da nhạy cảm", type: "bool", required: false },
    { id: "fd_2", name: "nguon_kh", label: "Nguồn khách hàng", type: "select", required: false, options: ["Facebook", "Zalo", "Instagram", "Giới thiệu", "Facebook Ads"] },
    { id: "fd_3", name: "ngay_sinh", label: "Ngày sinh", type: "date", required: false },
    { id: "fd_4", name: "ghi_chu", label: "Ghi chú nội bộ", type: "text", required: false },
  ];

  // ── Spark / trend helpers (worklist + dashboard) ────────
  const adSpendTrend = [3.1, 3.6, 4.2, 3.9, 4.8, 5.2, 5.0, 6.1, 5.8, 7.1];

  window.DB = {
    users, ME, tags, parties, orders, activities, notes, tasks, conversations,
    dedup, segments, campaigns, targets, ads, fieldDefs, adSpendTrend,
    // lookups
    userById: (id) => users.find((u) => u.id === id) || null,
    partyById: (id) => parties.find((p) => p.id === id) || null,
    tagById: (id) => tags.find((t) => t.id === id) || null,
    segById: (id) => segments.find((s) => s.id === id) || null,
    campaignById: (id) => campaigns.find((c) => c.id === id) || null,
    convById: (id) => conversations.find((c) => c.id === id) || null,
  };
})();
