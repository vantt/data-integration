/* ============================================================
   Surface registry — single source of truth for navigation.
   Mirrors ui-spec/generated/surface-registry.yaml (id · type ·
   name · hosts). The C01 sidebar is GENERATED from REG.GROUPS;
   REG.launch[id] tells the app how to reach each surface
   (screen route · panel tab · component host · modal-on-host).
   Loaded after data.js (window.DB ready), before the JSX.
   ============================================================ */
(function () {
  // ── Raw registry rows (id → {type, name, hosts}) ──────────
  // Verbatim from surface-registry.yaml; screen labels localized.
  const SURF = {
    // screens
    S01: { type: "screen", name: "Worklist / Dashboard", vi: "Worklist", icon: "worklist", rules: ["R2", "R6", "R8"] },
    S02: { type: "screen", name: "Customer List & Search", vi: "Khách hàng", icon: "customers", rules: ["R5"] },
    S03: { type: "screen", name: "Customer 360 Detail", vi: "Hồ sơ 360", icon: "user", hosts: ["P01", "P02", "P03", "P04", "P05", "P06"], rules: ["R2", "R3", "R6", "R7"] },
    S04: { type: "screen", name: "Dedup Review", vi: "Dedup", icon: "dedup", rules: ["R4", "R5", "R9"] },
    S05: { type: "screen", name: "Inbox (Conversations)", vi: "Inbox", icon: "inbox", rules: ["R6", "R12"] },
    S06: { type: "screen", name: "Conversation Detail", vi: "Hội thoại", icon: "doc", rules: ["R6", "R12"] },
    S07: { type: "screen", name: "Tasks Board", vi: "Tasks", icon: "tasks", rules: ["R8", "R11"] },
    S08: { type: "screen", name: "Segments List", vi: "Segments", icon: "segments", rules: ["R1", "R10"] },
    S09: { type: "screen", name: "Segment Builder", vi: "Segment Builder", icon: "filter", rules: ["R1", "R10"] },
    S10: { type: "screen", name: "Campaigns List", vi: "Chiến dịch", icon: "campaigns", rules: ["R1", "R10"] },
    S11: { type: "screen", name: "Campaign Detail / Targets", vi: "Chi tiết chiến dịch", icon: "bolt", rules: ["R1", "R3", "R6", "R11"] },
    S12: { type: "screen", name: "Ads Tracking", vi: "Ads", icon: "ads", rules: ["R2", "R6"] },
    S13: { type: "screen", name: "Settings", vi: "Cài đặt", icon: "settings", rules: [] },
    // panels (hosted in S03)
    P01: { type: "panel", name: "Insight Panel", vi: "Insight", hosts: ["S03"] },
    P02: { type: "panel", name: "Order History Panel", vi: "Đơn hàng", hosts: ["S03"] },
    P03: { type: "panel", name: "Activity Timeline Panel", vi: "Timeline", hosts: ["S03"] },
    P04: { type: "panel", name: "Tasks Panel", vi: "Tasks", hosts: ["S03"] },
    P05: { type: "panel", name: "Notes Panel", vi: "Ghi chú", hosts: ["S03"] },
    P06: { type: "panel", name: "Conversations Panel", vi: "Chat", hosts: ["S03"] },
    // modals
    M01: { type: "modal", name: "Merge Confirm", hosts: ["S04"] },
    M02: { type: "modal", name: "Create Party", hosts: ["S02"] },
    M03: { type: "modal", name: "Tag Management", hosts: ["S03"] },
    M04: { type: "modal", name: "Assign Owner", hosts: ["S03"] },
    M05: { type: "modal", name: "Create / Edit Task", hosts: ["S01", "S03", "S07", "P04"] },
    M06: { type: "modal", name: "Custom Fields Edit", hosts: ["S03"] },
    M07: { type: "modal", name: "Create / Edit Campaign", hosts: ["S10", "S11"] },
    M08: { type: "modal", name: "Log Activity", hosts: ["S03", "S06", "P02", "P03", "P05"] },
    M09: { type: "modal", name: "Assign Conversation", hosts: ["S05", "S06"] },
    M10: { type: "modal", name: "Close Conversation", hosts: ["S06"] },
    M11: { type: "modal", name: "Link Party to Conversation", hosts: ["S06"] },
    M12: { type: "modal", name: "Record Conversion", hosts: ["S11"] },
    M13: { type: "modal", name: "Custom Field Definition", hosts: ["S13"] },
    M14: { type: "modal", name: "Create Tag", hosts: ["S13", "M03"] },
    // overlays
    O01: { type: "overlay", name: "Confirm / Toast", hosts: ["S03", "S05", "S13", "P05"] },
    O02: { type: "overlay", name: "Quick Customer Preview", hosts: ["S01", "S07"] },
    // components
    C01: { type: "component", name: "Sidebar Nav", hosts: ["S01"] },
    C02: { type: "component", name: "Global Customer Search", hosts: ["S02", "S03"] },
    C03: { type: "component", name: "Action Queue Card", hosts: ["P01", "S01"] },
    C04: { type: "component", name: "Tag Chips", hosts: ["S02", "S03", "S04"] },
    C05: { type: "component", name: "Filter Bar", hosts: ["S01", "S02", "S05", "S07", "S10", "S11"] },
    C06: { type: "component", name: "Freshness Badge", hosts: ["S01", "S03", "S12", "P01", "P02"] },
  };

  // ── 8-group taxonomy (the order the sidebar renders) ──────
  // Each group draws its members straight from the registry ids.
  const GROUPS = [
    { key: "onboarding", label: "Onboarding", items: [] },
    { key: "workspace", label: "Workspace", items: ["S01", "S02", "S03", "S05", "S06", "S07"] },
    { key: "secondary", label: "Secondary views", subs: [
      { label: "Màn hình", items: ["S04", "S08", "S09", "S10", "S11", "S12"] },
      { label: "Panels · Customer 360", items: ["P01", "P02", "P03", "P04", "P05", "P06"] },
    ] },
    { key: "settings", label: "Settings", items: ["S13"] },
    { key: "mobile", label: "Mobile PWA", items: [] },
    { key: "modals", label: "Modals", items: ["M01", "M02", "M03", "M04", "M05", "M06", "M07", "M08", "M09", "M10", "M11", "M12", "M13", "M14"] },
    { key: "overlays", label: "Overlays", items: ["O01", "O02"] },
    { key: "components", label: "Components", items: ["C01", "C02", "C03", "C04", "C05", "C06"] },
  ];

  // ── Launch spec: how the sidebar reaches each surface ─────
  // kind: screen | panel | comp | modal | overlay | preview
  const DB = window.DB;
  const launch = {
    // screens
    S01: { kind: "screen", route: { screen: "S01" } },
    S02: { kind: "screen", route: { screen: "S02" } },
    S03: { kind: "screen", route: { screen: "S03", party: "p_001" } },
    S04: { kind: "screen", route: { screen: "S04" } },
    S05: { kind: "screen", route: { screen: "S05" } },
    S06: { kind: "screen", route: { screen: "S06", conversation: "c_010" } },
    S07: { kind: "screen", route: { screen: "S07" } },
    S08: { kind: "screen", route: { screen: "S08" } },
    S09: { kind: "screen", route: { screen: "S09" } },
    S10: { kind: "screen", route: { screen: "S10" } },
    S11: { kind: "screen", route: { screen: "S11", campaign: "cmp_1" } },
    S12: { kind: "screen", route: { screen: "S12" } },
    S13: { kind: "screen", route: { screen: "S13" } },
    // panels → S03, open that tab
    P01: { kind: "panel", route: { screen: "S03", party: "p_001", tab: "P01" } },
    P02: { kind: "panel", route: { screen: "S03", party: "p_001", tab: "P02" } },
    P03: { kind: "panel", route: { screen: "S03", party: "p_001", tab: "P03" } },
    P04: { kind: "panel", route: { screen: "S03", party: "p_001", tab: "P04" } },
    P05: { kind: "panel", route: { screen: "S03", party: "p_001", tab: "P05" } },
    P06: { kind: "panel", route: { screen: "S03", party: "p_001", tab: "P06" } },
    // modals → navigate to host screen, then open
    M01: { kind: "modal", route: { screen: "S04" }, type: "M01", ctx: () => ({ candidate: DB.dedup[0] }) },
    M02: { kind: "modal", route: { screen: "S02" }, type: "M02", ctx: () => ({}) },
    M03: { kind: "modal", route: { screen: "S03", party: "p_001" }, type: "M03", ctx: () => ({ party: "p_001" }) },
    M04: { kind: "modal", route: { screen: "S03", party: "p_001" }, type: "M04", ctx: () => ({ party: "p_001" }) },
    M05: { kind: "modal", route: { screen: "S07" }, type: "M05", ctx: () => ({ party: "p_001" }) },
    M06: { kind: "modal", route: { screen: "S03", party: "p_001" }, type: "M06", ctx: () => ({ party: "p_001" }) },
    M07: { kind: "modal", route: { screen: "S10" }, type: "M07", ctx: () => ({}) },
    M08: { kind: "modal", route: { screen: "S03", party: "p_001" }, type: "M08", ctx: () => ({ party: "p_001" }) },
    M09: { kind: "modal", route: { screen: "S05" }, type: "M09", ctx: () => ({ conversation: "c_010" }) },
    M10: { kind: "modal", route: { screen: "S06", conversation: "c_002" }, type: "M10", ctx: () => ({ conversation: "c_002" }) },
    M11: { kind: "modal", route: { screen: "S06", conversation: "c_010" }, type: "M11", ctx: () => ({ conversation: "c_010" }) },
    M12: { kind: "modal", route: { screen: "S11", campaign: "cmp_1" }, type: "M12", ctx: () => ({ target: (DB.targets.cmp_1 || [])[1] || DB.targets.cmp_1[0], campaignName: "Win-back Q3" }) },
    M13: { kind: "modal", route: { screen: "S13" }, type: "M13", ctx: () => ({}) },
    M14: { kind: "modal", route: { screen: "S13" }, type: "M14", ctx: () => ({}) },
    // overlays
    O01: { kind: "modal", route: { screen: "S03", party: "p_001" }, type: "O01", ctx: () => ({ confirm_type: "delete_note" }) },
    O02: { kind: "preview", route: { screen: "S01" }, party: "p_001" },
    // components → navigate to a host screen that shows the component
    C01: { kind: "comp", route: { screen: "S01" }, where: "Worklist" },
    C02: { kind: "comp", route: { screen: "S02" }, where: "Khách hàng" },
    C03: { kind: "comp", route: { screen: "S01" }, where: "Worklist" },
    C04: { kind: "comp", route: { screen: "S03", party: "p_001" }, where: "Hồ sơ 360" },
    C05: { kind: "comp", route: { screen: "S01" }, where: "Worklist" },
    C06: { kind: "comp", route: { screen: "S03", party: "p_001" }, where: "Hồ sơ 360" },
  };

  // counts for group eyebrows
  const count = (g) => g.subs ? g.subs.reduce((s, x) => s + x.items.length, 0) : (g.items ? g.items.length : 0);

  window.REG = { SURF, GROUPS, launch, count };
})();
