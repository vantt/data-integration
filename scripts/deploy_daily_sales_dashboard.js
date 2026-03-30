// require('dotenv').config(); // Using node --env-file=.env instead
const MetabaseClient = require('../.skills/metabase-automation/scripts/metabase_client');

// Configuration
const METABASE_URL = process.env.METABASE_URL;
const METABASE_USERNAME = process.env.METABASE_USERNAME;
const METABASE_PASSWORD = process.env.METABASE_PASSWORD;
// If using Session ID directly:
const METABASE_SESSION_ID = process.env.METABASE_SESSION_TOKEN;
const API_KEY = process.env.METABASE_API_KEY; // Or whatever your auth uses

const DB_NAME = "Sapo DuckDB"; // Updated based on available DBs
const COLLECTION_NAME = "Sales Analytics";
const DASHBOARD_NAME = "Daily Sales Performance";

async function main() {
    console.log("🚀 Starting Daily Sales Dashboard Deployment...");

// 1. Initialize Client & Authenticate
    let sessionToken = process.env.METABASE_SESSION_ID || process.env.METABASE_SESSION_TOKEN;
    const username = process.env.METABASE_USERNAME || process.env.METABASE_USER;
    const password = process.env.METABASE_PASSWORD;
    const apiKey = process.env.METABASE_API_KEY;

    // A. Try Username/Password Login
    if (!sessionToken && username && password) {
        console.log(`🔄 Authenticating with Username/Password (${username})...`);
        try {
            const authRes = await fetch(`${METABASE_URL}/api/session`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ username, password })
            });
            
            if (!authRes.ok) {
                const errText = await authRes.text();
                throw new Error(`Authentication failed: ${authRes.status} ${errText}`);
            }

            const authData = await authRes.json();
            sessionToken = authData.id;
            console.log("✅ Successfully authenticated via User/Pass.");
        } catch (err) {
            console.error("❌ Auth Error:", err);
            process.exit(1);
        }
    }

    let client;
    if (sessionToken) {
        // B. Use Session Token
        client = new MetabaseClient(METABASE_URL, sessionToken);
        // Force Session Header
        delete client.core.headers['x-api-key'];
        client.core.headers['X-Metabase-Session'] = sessionToken;
        console.log("ℹ️ Using Session Token.");
    } else if (apiKey) {
        // C. Use API Key (Fall back to old behavior or try both headers?)
        console.log("ℹ️ Using provided API Key.");
        client = new MetabaseClient(METABASE_URL, apiKey);
        // Note: If this is an embedding key, it will fail.
        // If it's a session token labeled as API Key, let's try to be smart?
        // Let's assume standard behavior first (x-api-key).
        // If that fails, the user needs to fix config.
    } else {
        console.error("❌ No Session Token, Credentials, or API Key provided.");
        process.exit(1);
    }

    try {
        const connected = await client.connect();
        if (!connected) throw new Error("Connection validation returned false");
        console.log("✅ Connection Validated");
    } catch (err) {
        console.error("❌ Connection validation failed. If using API Key, ensure it is a valid API/Session key, not an Embedding key.", err);
        process.exit(1);
    }

    // 2. Resolve Database ID
    const databases = await client.core.request('/api/database');
    console.log("Databases response:", JSON.stringify(databases, null, 2));
    
    let dbList = databases;
    if (databases && databases.data && Array.isArray(databases.data)) {
         dbList = databases.data;
    } else if (!Array.isArray(databases)) {
         // It might be an object like { total: 1, data: [...] } or something else
         // For now, if we can't find an array, we default to empty to avoid crash
         dbList = [];
    }

    const db = dbList.find(d => d.name === DB_NAME);
    if (!db) {
        console.log("Databases available:", dbList.map(d => d.name).join(', '));
        console.error(`❌ Database '${DB_NAME}' not found.`);
        return;
    }
    const DB_ID = db.id;
    console.log(`✅ Found Database '${DB_NAME}' (ID: ${DB_ID})`);

    // 3. Ensure Collection
    const col = await client.collection.ensure(COLLECTION_NAME);

    // 4. Define Questions (Cards)
    const questions = [
        {
            name: "Total Orders (Today)",
            display: "scalar",
            sql: `
SELECT count(distinct o.order_id) as "Total Orders"
FROM fact_orders o
WHERE date(o.order_timestamp) = current_date
            `,
            pos: { row: 0, col: 0, size_x: 4, size_y: 4 }
        },
        {
            name: "Total Revenue (Today)",
            display: "scalar",
            sql: `
SELECT coalesce(sum(o.gmv), 0) as "Total Revenue"
FROM fact_orders o
WHERE date(o.order_timestamp) = current_date
            `,
            pos: { row: 0, col: 4, size_x: 4, size_y: 4 }
        },
        {
            name: "AOV (Today)",
            display: "scalar",
            sql: `
SELECT 
    case when count(distinct o.order_id) = 0 then 0
         else sum(o.gmv) / count(distinct o.order_id) end as "AOV"
FROM fact_orders o
WHERE date(o.order_timestamp) = current_date
            `,
            pos: { row: 0, col: 8, size_x: 4, size_y: 4 }
        },
        {
            name: "New vs Returning Customers (Today)",
            display: "row", // scalar with multiple values? Or table? The SQL returns two columns. 
            // The query in the doc returns "New Customers" and "Return Customers" as columns in one row.
            // "number" viz usually picks one. Let's make it a table or "smart number" if Metabase handles it.
            // Or split into two cards? The doc has them as one SQL. 
            // Let's use 'table' for safety or 'scalar' if it just shows the first one. 
            // Better: Split them? No, the SQL is one. 
            // One SQL returning multiple scalar metrics is often best shown as a Table or a "Smart Number" with multiple fields.
            // Let's stick to "table" effectively or "row" chart if valid. "smart scalar" isn't a strict display type key.
            // "table" is safe.
            display: "table", 
            sql: `
SELECT
    count(distinct case when date(c.first_order_date) = current_date then o.customer_key end) as "New Customers",
    count(distinct case when date(c.first_order_date) < current_date then o.customer_key end) as "Return Customers"
FROM fact_orders o
LEFT JOIN dim_customers c ON o.customer_key = c.customer_key
WHERE date(o.order_timestamp) = current_date
            `,
            pos: { row: 0, col: 12, size_x: 4, size_y: 4 }
        },
        {
            name: "Hourly Sales Performance (Today vs Yesterday)",
            display: "line",
            sql: `
WITH current_sales AS (
    SELECT
        EXTRACT(HOUR FROM order_timestamp) as hour_of_day,
        SUM(gmv) as sales_today
    FROM fact_orders
    WHERE date(order_timestamp) = current_date
    GROUP BY 1
),
previous_sales AS (
    SELECT
        EXTRACT(HOUR FROM order_timestamp) as hour_of_day,
        SUM(gmv) as sales_yesterday
    FROM fact_orders
    WHERE date(order_timestamp) = current_date - INTERVAL '1 day'
    GROUP BY 1
)
SELECT
    COALESCE(c.hour_of_day, p.hour_of_day) as hour_of_day,
    COALESCE(c.sales_today, 0) as sales_today,
    COALESCE(p.sales_yesterday, 0) as sales_yesterday
FROM current_sales c
FULL OUTER JOIN previous_sales p ON c.hour_of_day = p.hour_of_day
ORDER BY 1
            `,
            pos: { row: 4, col: 0, size_x: 16, size_y: 8 },
            viz_settings: {
                "graph.dimensions": ["hour_of_day"],
                "graph.metrics": ["sales_today", "sales_yesterday"]
            }
        },
        {
            name: "Top Selling Channels (Today)",
            display: "bar",
            sql: `
SELECT
    c.channel_name as "Channel",
    SUM(o.gmv) as "Revenue"
FROM fact_orders o
JOIN dim_channels c ON o.channel_key = c.channel_key
WHERE date(o.order_timestamp) = current_date
GROUP BY 1
ORDER BY 2 DESC
            `,
            pos: { row: 12, col: 0, size_x: 8, size_y: 6 }
        },
        {
            name: "Top Selling Products (Today)",
            display: "table",
            sql: `
SELECT
    p.product_name as "Product",
    SUM(s.revenue) as "Revenue"
FROM fact_sales s
JOIN dim_products p ON s.product_key = p.product_key
WHERE date(s.sol_timestamp) = current_date
GROUP BY 1
ORDER BY 2 DESC
LIMIT 20
            `,
            pos: { row: 12, col: 8, size_x: 8, size_y: 6 }
        }
    ];

    const cardMap = {};

    for (const q of questions) {
        console.log(`Processing card: ${q.name}...`);
        const card = await client.card.ensure(
            q.name,
            q.sql,
            DB_ID,
            col.id,
            {
                display: q.display,
                visualization_settings: q.viz_settings || {}
            }
        );
        cardMap[q.name] = { id: card.id, pos: q.pos };
    }

    // 5. Ensure Dashboard
    const dash = await client.dashboard.ensure(DASHBOARD_NAME, "Daily sales performance metrics", col.id);

    // 6. Sync Cards to Dashboard
    const dashCards = questions.map(q => ({
        id: cardMap[q.name].id,
        ...cardMap[q.name].pos
    }));

    await client.dashboard.syncCards(dash.id, dashCards);

    console.log("-----------------------------------------");
    console.log(`✅ Deployment Complete!`);
    console.log(`Dashboard Link: ${METABASE_URL}/dashboard/${dash.id}`);
    console.log("-----------------------------------------");
}

main().catch(console.error);
