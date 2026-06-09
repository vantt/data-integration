import re

VALID = {'All', 'Retail', 'B2B', 'Cross', 'US', 'Internal'}

def extract_suffix(name):
    m = re.search(r'\[([A-Za-z0-9]+)\]', name)
    return m.group(1) if m else None

def has_valid_suffix(name):
    s = extract_suffix(name)
    return s in VALID if s else False

blueprints = [
    ('b2b_orders_tracking.md', '# B2B Orders Tracking Blueprint [B2B]', '### Dashboard: B2B Orders Tracking [B2B]'),
    ('b2b_sales_daily.md', '# B2B Daily Sales Blueprint [B2B]', '### Dashboard: B2B Daily Sales [B2B]'),
    ('ceo_monthly_scorecard.md', '# Blueprint: CEO Monthly Scorecard [All]', '### Dashboard: CEO Monthly Scorecard [All]'),
    ('ceo_weekly_pulse.md', '# CEO Weekly Pulse Blueprint [All]', '### Dashboard: CEO Weekly Pulse [All]'),
    ('channel_profitability_monthly.md', '# Channel Profitability Monthly [Cross] Blueprint', '### Dashboard: Channel Profitability Monthly [Cross]'),
    ('customer_intelligence_monthly.md', '# Blueprint: Customer Intelligence Monthly [Cross]', '### Dashboard: Customer Intelligence Monthly [Cross]'),
    ('customer_operational_dashboard.md', '# Customer Operational Dashboard Blueprint [Retail]', '### Dashboard: Customer Operational [Retail]'),
    ('customer_retention_dashboard.md', '# Blueprint: Customer Retention & Lifecycle [Retail]', '### Dashboard: Customer Retention & Lifecycle [Retail]'),
    ('customer_support_social_commerce.md', '# Social Commerce Operations [Retail] Blueprint', '### Dashboard: Social Commerce Operations [Retail]'),
    ('finance_accounting_recon.md', '# Blueprint: Accounting Reconciliation Cockpit [Internal]', '### Dashboard: Accounting Reconciliation Cockpit [Internal]'),
    ('finance_channel_pl.md', '# Blueprint: Channel P&L Deep Dive [Cross]', '### Dashboard: Channel P&L Deep Dive [Cross]'),
    ('finance_cost_ledger.md', '# Blueprint: Cost Ledger Analyzer [All]', '### Dashboard: Cost Ledger Analyzer [All]'),
    ('finance_pl.md', '# Finance P&L [All] Blueprint', '### Dashboard: Finance P&L [All]'),
    ('finance_product_cost_margin.md', '# Blueprint: Product Cost-to-Margin Heatmap [Cross]', '### Dashboard: Product Cost-to-Margin Heatmap [Cross]'),
    ('finance_return_impact.md', '# Return Impact Analysis [All] Blueprint', '### Dashboard: Return Impact Analysis [All]'),
    ('finance_services_revenue.md', '# Blueprint: Finance Services Revenue [All]', '### Dashboard: Finance Services Revenue [All]'),
    ('ingestion_health.md', '# Blueprint: Ingestion Health Monitor [Internal]', '### Dashboard: Ingestion Health Monitor [Internal]'),
    ('logistics_operations.md', '# Logistics Operations Center Blueprint [All]', '### Dashboard: Logistics Operations Center [All]'),
    ('marketing_monthly_analysis.md', '# Blueprint: Marketing Monthly Analysis', '### Dashboard: Marketing Monthly Analysis [Retail]'),
    ('marketing_roi.md', '# Marketing ROI Blueprint', '### Dashboard: Marketing ROI [Retail]'),
    ('marketing_weekly_tracker.md', '# Blueprint: Marketing Weekly Tracker [Retail]', '### Dashboard: Marketing Weekly Tracker [Retail]'),
    ('order_detail.md', '# Order Detail Blueprint [Retail]', '### Dashboard: Order Detail [Retail]'),
    ('order_listing.md', '# Blueprint: Order Listing [Retail]', '### Dashboard: Order Listing [Retail]'),
    ('order_profitability_all.md', '# Order Profitability [All] Blueprint', '### Dashboard: Order Profitability [All]'),
    ('product_inventory.md', '# Product Inventory Health [All] Blueprint', '### Dashboard: Product Inventory Health [All]'),
    ('product_performance.md', '# Product Performance Blueprint', '### Dashboard: Product Performance [Cross]'),
    ('product_profitability.md', '# Product Profitability Blueprint [All]', '### Dashboard: Product Profitability [All]'),
    ('sales_daily_operation.md', '# Daily Sales Performance Blueprint [Retail]', '### Dashboard: Daily Sales [Retail]'),
    ('sales_monthly_review.md', '# Blueprint: Sales Monthly Business Review [All]', '### Dashboard: Sales Monthly Business Review [All]'),
    ('sales_ops_monthly_summary.md', '# Sales Ops Monthly Summary Blueprint (Redesign)', '### Dashboard: Sales Ops Monthly Summary [Retail]'),
    ('sales_ops_weekly_review.md', '# Sales Ops Weekly Review Blueprint (Redesign)', '### Dashboard: Sales Ops Weekly Review [Retail]'),
    ('sales_promotion_analysis.md', '# Blueprint: Sales Promotion & Discount Analysis [Retail]', '### Dashboard: Promotion Analysis [Retail]'),
    ('sales_yesterday_operation.md', "# Yesterday's Sales Performance Blueprint [Retail]", "### Dashboard: Yesterday's Sales [Retail]"),
    ('shopee_channel_economics.md', '# Shopee Channel Economics Blueprint', '### Dashboard: Shopee Channel Economics [Cross]'),
    ('us_crossborder_operations.md', '# US CrossBorder Operations Blueprint [US]', '### Dashboard: US CrossBorder Daily [US]'),
]

live_dashboards = {
    1: 'E-commerce Insights',
    8: 'Sales Ops Weekly Review [Retail]',
    9: 'Sales Ops Monthly Summary [Retail]',
    13: 'Marketing Monthly Analysis [Retail]',
    14: 'Customer Retention & Lifecycle [Retail]',
    15: 'Customer Intelligence Monthly [Cross]',
    26: 'Order Listing [Retail]',
    27: 'Social Commerce Operations [Retail]',
    28: 'Logistics Operations Center [All]',
    30: 'Product Performance [Cross]',
    31: 'Sales Monthly Business Review [All]',
    32: 'Shopee Channel Economics [Cross]',
    33: 'Channel Profitability Monthly [Cross]',
    34: 'Finance P&L [All]',
    35: 'Order Profitability [All]',
    36: 'Product Profitability [All]',
    37: 'Marketing ROI [Retail]',
    38: 'Order Detail [Retail]',
    40: 'Ingestion Health Monitor [Internal]',
    41: 'Daily Sales [Retail]',
    42: "Yesterday's Sales [Retail]",
    43: 'CEO Weekly Pulse [All]',
    44: 'CEO Monthly Scorecard [All]',
    46: 'Promotion Analysis [Retail]',
    47: 'Marketing Weekly Tracker [Retail]',
    48: 'Customer Operational [Retail]',
    49: 'B2B Daily Sales [B2B]',
    50: 'B2B Orders Tracking [B2B]',
    51: 'US CrossBorder Daily [US]',
    73: 'Welcome to ChPulse BI',
    74: 'Cost Ledger Analyzer [All]',
    75: 'Return Impact Analysis [All]',
    76: 'Product Cost-to-Margin Heatmap [Cross]',
    77: 'Channel P&L Deep Dive [Cross]',
    78: 'Accounting Reconciliation Cockpit [Internal]',
    94: 'Product Inventory Health [All]',
    95: 'Finance Services Revenue [All]',
}

live_set = set(live_dashboards.values())
exempt_dashboards = {'E-commerce Insights', 'Welcome to ChPulse BI'}

print('=== BLUEPRINT ANALYSIS ===')
issues_bp = []
passed = 0
for bp_file, line1, dash_line in blueprints:
    t1_raw = re.sub(r'^#+\s*', '', line1).strip()
    # Remove emoji chars
    t1_raw = re.sub(r'[^\x00-\x7F]+', '', t1_raw).strip()
    l1_suffix = extract_suffix(t1_raw)
    l1_has_suffix = l1_suffix in VALID if l1_suffix else False

    dash_name_raw = re.sub(r'^###\s*', '', dash_line).strip()
    dash_name_raw = re.sub(r'[^\x00-\x7F]+', '', dash_name_raw).strip()
    dash_name_raw = re.sub(r'^Dashboard:\s*', '', dash_name_raw).strip()

    d_suffix = extract_suffix(dash_name_raw)
    d_has_suffix = d_suffix in VALID if d_suffix else False
    suffix_match = (l1_suffix == d_suffix)
    live_match = dash_name_raw in live_set

    bp_issues = []
    if not l1_has_suffix:
        bp_issues.append('MISSING_SUFFIX_TITLE')
    if not d_has_suffix:
        bp_issues.append('MISSING_SUFFIX_BLUEPRINT')
    if l1_has_suffix and d_has_suffix and not suffix_match:
        bp_issues.append('INCONSISTENT_SUFFIX (title=[%s] vs target=[%s])' % (l1_suffix, d_suffix))
    if not live_match:
        bp_issues.append('ORPHAN_BLUEPRINT (target="%s")' % dash_name_raw)

    if bp_issues:
        print('  ISSUE | %s' % bp_file)
        print('    L1 title: %s' % t1_raw[:90])
        print('    Target:   %s' % dash_name_raw)
        for i in bp_issues:
            print('    -> %s' % i)
        issues_bp.append((bp_file, bp_issues))
    else:
        passed += 1

print('\nBlueprints PASS: %d/35' % passed)
print('Blueprints with issues: %d/35' % len(issues_bp))

print('\n=== DASHBOARD ANALYSIS ===')
bp_targets = set()
for _, _, dash_line in blueprints:
    d = re.sub(r'^###\s*', '', dash_line).strip()
    d = re.sub(r'[^\x00-\x7F]+', '', d).strip()
    d = re.sub(r'^Dashboard:\s*', '', d).strip()
    bp_targets.add(d)

dash_issues = []
dash_passed = 0
for did, dname in sorted(live_dashboards.items()):
    has_suf = has_valid_suffix(dname)
    is_exempt = dname in exempt_dashboards
    has_bp = dname in bp_targets

    d_issues = []
    if not has_suf and not is_exempt:
        d_issues.append('MISSING_SUFFIX_DASHBOARD')
    if not has_bp and not is_exempt:
        d_issues.append('ORPHAN_DASHBOARD')

    if d_issues:
        print('  ISSUE | D%d | %s' % (did, dname))
        for i in d_issues:
            print('    -> %s' % i)
        dash_issues.append((did, dname, d_issues))
    else:
        dash_passed += 1

print('\nDashboards PASS: %d/37 (incl 2 exempt)' % dash_passed)
print('Dashboards with issues: %d/37' % len(dash_issues))

print('\n=== REGISTRY ANOMALY ===')
print('collection_registry.yml: "- Ingestion Health Monitor" (missing [Internal])')
print('Blueprint target + Metabase: "Ingestion Health Monitor [Internal]"')
print('-> REGISTRY_MISSING_SUFFIX in collection_registry.yml line ~151')
