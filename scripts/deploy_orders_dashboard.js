#!/usr/bin/env node
/**
 * Deploy enhanced "Orders" dashboard with 3 tabs (Today/Yesterday/By Date)
 * Each tab: 6 KPIs + 3 breakdowns + Flagged Orders + Detail List = 11 cards
 *
 * Usage: DASH_ID=23 node scripts/deploy_orders_dashboard.js
 * Set DASH_ID to target an existing dashboard, otherwise creates new.
 */
const http = require('http');

const METABASE_URL = process.env.METABASE_URL;
const API_KEY = process.env.METABASE_API_KEY;
const DB_ID = 2;
const DAILY_MON = 48;

function api(method, apiPath, body) {
  return new Promise((resolve, reject) => {
    const url = new URL(METABASE_URL + apiPath);
    const data = body ? JSON.stringify(body) : null;
    const opts = {
      hostname: url.hostname, port: url.port, path: url.pathname, method,
      headers: { 'x-api-key': API_KEY, 'Content-Type': 'application/json' }
    };
    if (data) opts.headers['Content-Length'] = Buffer.byteLength(data);
    const req = http.request(opts, res => {
      let d = ''; res.on('data', c => d += c);
      res.on('end', () => {
        if (res.statusCode >= 400) { reject(new Error(`${method} ${apiPath}: ${res.statusCode} ${d.substring(0,200)}`)); return; }
        try { resolve(JSON.parse(d)); } catch (e) { resolve(d); }
      });
    });
    req.on('error', reject);
    if (data) req.write(data);
    req.end();
  });
}

const DATE_TAG = { date: { id: 'date_tag', name: 'date', 'display-name': 'Date', type: 'date', required: true } };
const VND = { number_style: 'currency', currency: 'VND' };

function sql(template, dateExpr) { return template.replace(/{{DATE}}/g, dateExpr); }

const Q = {
  totalOrders:    `SELECT COUNT(DISTINCT order_id) as "Total Orders" FROM fact_orders WHERE date(order_timestamp) = {{DATE}}`,
  netRevenue:     `SELECT COALESCE(SUM(net_revenue), 0) as "Net Revenue" FROM fact_orders WHERE date(order_timestamp) = {{DATE}} AND status NOT IN ('CANCELLED', 'Voided')`,
  totalCollected: `SELECT COALESCE(SUM(total_collected), 0) as "Total Collected" FROM fact_orders WHERE date(order_timestamp) = {{DATE}} AND status NOT IN ('CANCELLED', 'Voided')`,
  totalDiscount:  `SELECT COALESCE(SUM(discount_amount), 0) as "Total Discount" FROM fact_orders WHERE date(order_timestamp) = {{DATE}} AND status NOT IN ('CANCELLED', 'Voided')`,
  cancelled:      `SELECT COUNT(DISTINCT order_id) as "Cancelled" FROM fact_orders WHERE date(order_timestamp) = {{DATE}} AND status = 'CANCELLED'`,
  returns:        `SELECT COUNT(CASE WHEN fulfillment_status = 'RETURNED' THEN 1 END) as "Returns" FROM fact_orders WHERE date(order_timestamp) = {{DATE}}`,
  byStatus:       `SELECT status as "Status", COUNT(DISTINCT order_id) as "Orders", COALESCE(SUM(total_collected), 0) as "Amount" FROM fact_orders WHERE date(order_timestamp) = {{DATE}} GROUP BY 1 ORDER BY 2 DESC`,
  byPayment:      `SELECT payment_status as "Payment Status", COUNT(DISTINCT order_id) as "Orders", COALESCE(SUM(total_collected), 0) as "Amount" FROM fact_orders WHERE date(order_timestamp) = {{DATE}} GROUP BY 1 ORDER BY 2 DESC`,
  byChannel:      `SELECT c.channel_name as "Channel", COUNT(DISTINCT o.order_id) as "Orders", COALESCE(SUM(o.net_revenue), 0) as "Revenue" FROM fact_orders o JOIN dim_channels c ON o.channel_key = c.channel_key WHERE date(o.order_timestamp) = {{DATE}} AND o.status NOT IN ('CANCELLED', 'Voided') GROUP BY 1 ORDER BY 2 DESC`,
  flagged:        `SELECT o.order_id as "Order ID", o.status as "Status", ch.channel_name as "Channel", o.gross_revenue as "Gross", o.discount_amount as "Discount", o.net_revenue as "Net Revenue", o.total_collected as "Collected", CASE WHEN o.total_collected = 0 AND o.discount_amount > 0 THEN '100% Discount' WHEN o.net_revenue < 0 THEN 'Negative Revenue' WHEN o.discount_amount > o.gross_revenue THEN 'Discount > Gross' WHEN o.status = 'COMPLETED' AND o.payment_status != 'PAID' THEN 'Completed but Unpaid' WHEN o.payment_status = 'REFUNDED' THEN 'Refunded' END as "Flag" FROM fact_orders o LEFT JOIN dim_channels ch ON o.channel_key = ch.channel_key WHERE date(o.order_timestamp) = {{DATE}} AND ((o.total_collected = 0 AND o.discount_amount > 0) OR o.net_revenue < 0 OR o.discount_amount > o.gross_revenue OR (o.status = 'COMPLETED' AND o.payment_status != 'PAID') OR o.payment_status = 'REFUNDED') ORDER BY o.discount_amount DESC`,
  detail:         `SELECT o.order_id as "Order ID", strftime(o.order_timestamp, '%H:%M') as "Time", o.status as "Status", o.payment_status as "Payment", o.fulfillment_status as "Fulfillment", o.gross_revenue as "Gross", o.discount_amount as "Discount", o.net_revenue as "Net Revenue", o.tax_amount as "Tax", o.total_collected as "Collected", ch.channel_name as "Channel", c.full_name as "Customer", c.phone as "Phone", bl.branch_location_name as "Store" FROM fact_orders o LEFT JOIN dim_customers c ON o.customer_key = c.customer_key LEFT JOIN dim_channels ch ON o.channel_key = ch.channel_key LEFT JOIN dim_branch_location bl ON o.branch_location_key = bl.branch_location_key WHERE date(o.order_timestamp) = {{DATE}} ORDER BY o.order_timestamp DESC`
};

const CARDS = [
  { q: 'totalOrders',    name: 'Total Orders',      disp: 'scalar', viz: {},                                      pos: {row:0,col:0,size_x:3,size_y:3} },
  { q: 'netRevenue',     name: 'Net Revenue',        disp: 'scalar', viz: {column_settings:{'Net Revenue':VND}},   pos: {row:0,col:3,size_x:3,size_y:3} },
  { q: 'totalCollected', name: 'Total Collected',    disp: 'scalar', viz: {column_settings:{'Total Collected':VND}},pos: {row:0,col:6,size_x:3,size_y:3} },
  { q: 'totalDiscount',  name: 'Total Discount',     disp: 'scalar', viz: {column_settings:{'Total Discount':VND}},pos: {row:0,col:9,size_x:3,size_y:3} },
  { q: 'cancelled',      name: 'Cancelled Orders',   disp: 'scalar', viz: {},                                      pos: {row:0,col:12,size_x:3,size_y:3} },
  { q: 'returns',        name: 'Returns',            disp: 'scalar', viz: {},                                      pos: {row:0,col:15,size_x:3,size_y:3} },
  { q: 'byStatus',       name: 'Orders by Status',   disp: 'table',  viz: {column_settings:{Amount:VND}},          pos: {row:3,col:0,size_x:6,size_y:5} },
  { q: 'byPayment',      name: 'Orders by Payment',  disp: 'table',  viz: {column_settings:{Amount:VND}},          pos: {row:3,col:6,size_x:6,size_y:5} },
  { q: 'byChannel',      name: 'Orders by Channel',  disp: 'table',  viz: {column_settings:{Revenue:VND}},         pos: {row:3,col:12,size_x:6,size_y:5} },
  { q: 'flagged',        name: 'Flagged Orders',     disp: 'table',  viz: {column_settings:{Gross:VND,Discount:VND,'Net Revenue':VND,Collected:VND}}, pos: {row:8,col:0,size_x:18,size_y:5} },
  { q: 'detail',         name: 'Order Detail List',  disp: 'table',  viz: {column_settings:{Gross:VND,Discount:VND,'Net Revenue':VND,Tax:VND,Collected:VND}}, pos: {row:13,col:0,size_x:18,size_y:12} },
];

const TABS = [
  { tabId: -1, name: 'Today',     dateExpr: 'current_date', hasParam: false },
  { tabId: -2, name: 'Yesterday', dateExpr: "current_date - INTERVAL '1 day'", hasParam: false },
  { tabId: -3, name: 'By Date',   dateExpr: '{{date}}', hasParam: true },
];

(async () => {
  try {
    // Get or create dashboard
    let dashId = process.env.DASH_ID ? parseInt(process.env.DASH_ID) : null;
    if (!dashId) {
      const dash = await api('POST', 'api/dashboard', {
        name: 'Orders',
        description: 'Đối soát đơn hàng — so khớp, phát hiện bất thường, kiểm tra kênh/thanh toán/trạng thái.',
        collection_id: DAILY_MON,
        parameters: [{ id: 'date_param', name: 'Date', slug: 'date', type: 'date/single', sectionId: 'date' }]
      });
      dashId = dash.id;
      console.log('Created dashboard:', dashId);
    } else {
      console.log('Using dashboard:', dashId);
    }

    // Create cards and build dashcards
    const tabs = TABS.map(t => ({ id: t.tabId, name: t.name }));
    const dashcards = [];
    let dcId = -1;

    for (const tab of TABS) {
      for (const def of CARDS) {
        const querySql = sql(Q[def.q], tab.dateExpr);
        const query = tab.hasParam
          ? { database: DB_ID, type: 'native', native: { query: querySql, 'template-tags': DATE_TAG } }
          : { database: DB_ID, type: 'native', native: { query: querySql } };

        const card = await api('POST', 'api/card', {
          name: def.name, dataset_query: query, display: def.disp,
          visualization_settings: {}, collection_id: DAILY_MON
        });
        // Viz settings go on the dashcard, not the saved card

        dashcards.push({
          id: dcId--, card_id: card.id, ...def.pos,
          dashboard_tab_id: tab.tabId, visualization_settings: {},
          parameter_mappings: tab.hasParam ? [{
            parameter_id: 'date_param', card_id: card.id,
            target: ['variable', ['template-tag', 'date']]
          }] : []
        });
      }
      console.log(tab.name + ': 11 cards');
    }

    // Write payload and use curl (Node http.request has issues with large JSON bodies)
    const payloadPath = require('path').join(require('os').tmpdir(), 'orders_payload.json');
    require('fs').writeFileSync(payloadPath, JSON.stringify({ tabs, dashcards }));
    console.log('Payload written to:', payloadPath, '(' + require('fs').statSync(payloadPath).size + ' bytes)');

    const { execSync } = require('child_process');
    const curlCmd = `curl -s -X PUT -H "x-api-key: ${API_KEY}" -H "Content-Type: application/json" "${METABASE_URL}api/dashboard/${dashId}" -d @${payloadPath}`;
    const curlResult = execSync(curlCmd, { encoding: 'utf-8' });
    const result = JSON.parse(curlResult);
    const rTabs = result.tabs || [];
    const rCards = result.dashcards || [];
    console.log('\nDashboard ' + dashId + ': ' + rTabs.length + ' tabs, ' + rCards.length + ' cards');
    rTabs.forEach(t => {
      const tc = rCards.filter(dc => dc.dashboard_tab_id === t.id);
      console.log('  ' + t.name + ': ' + tc.length + ' cards');
    });
  } catch (e) {
    console.error('ERROR:', e.message);
  }
})();
