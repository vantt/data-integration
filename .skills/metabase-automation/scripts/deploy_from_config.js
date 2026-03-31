const MetabaseClient = require('./metabase_client');
const path = require('path');
const fs = require('fs');

/**
 * Generic Deployment Script
 * Usage: node deploy_from_config.js <path-to-config.js>
 * 
 * Config File Format (CommonJS):
 * module.exports = {
 *   database: "Sapo DuckDB",
 *   collection: "Sales Analytics",
 *   dashboard: {
 *     name: "Daily Sales Performance",
 *     description: "...",
 *     tabs: ["Overview", "Details"]  // optional — tab names
 *   },
 *   questions: [
 *     {
 *       name: "Total Orders",
 *       display: "scalar",
 *       sql: `SELECT ...`,
 *       pos: { row: 0, col: 0, size_x: 4, size_y: 4 },
 *       tab: "Overview"  // optional — assigns to tab
 *     }
 *   ]
 * };
 */

async function main() {
    // 1. Load Config
    const configPath = process.argv[2];
    if (!configPath) {
        console.error("Please provide a path to the config file.");
        console.error("Usage: node deploy_from_config.js <path-to-config.js>");
        process.exit(1);
    }

    const absPath = path.resolve(process.cwd(), configPath);
    if (!fs.existsSync(absPath)) {
        console.error(`Config file not found at: ${absPath}`);
        process.exit(1);
    }

    console.log(`📖 Loading configuration from: ${path.basename(absPath)}`);
    const config = require(absPath);

    // 2. Auth
    const METABASE_URL = process.env.METABASE_URL;
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
        client = new MetabaseClient(METABASE_URL, sessionToken, { authHeader: 'X-Metabase-Session' });
        console.log("ℹ️ Using Session Token.");
    } else if (apiKey) {
        // C. Use API Key
        console.log("ℹ️ Using provided API Key.");
        client = new MetabaseClient(METABASE_URL, apiKey);
    } else {
        console.error("❌ No Session Token, Credentials, or API Key provided.");
        process.exit(1);
    }

    try {
        const connected = await client.connect();
        if (!connected) throw new Error("Connection validation returned false");
        console.log("✅ Metabase Connected");
    } catch (err) {
        console.error("❌ Connection failed:", err.message);
        process.exit(1);
    }

    // 3. Resolve Database
    let dbId = null;
    if (config.database) {
        dbId = await client.findDatabaseId(config.database);
        if (!dbId) {
            console.error(`❌ Database '${config.database}' not found. Aborting.`);
            process.exit(1);
        }
        console.log(`✅ Targeted Database: ${config.database} (ID: ${dbId})`);
    }

    // 4. Ensure Collection
    let colId = null;
    if (config.collection) {
        const col = await client.collection.ensure(config.collection);
        colId = col.id;
    }

    // 5. Process Questions
    const cardMap = {};
    if (config.questions) {
        console.log(`🔄 Processing ${config.questions.length} questions...`);
        for (const q of config.questions) {
            if (!q.sql) {
                console.warn(`⚠️ Skipping question '${q.name}': No SQL provided.`);
                continue;
            }

            const card = await client.card.ensure(
                q.name,
                q.sql,
                dbId,
                colId,
                {
                    display: q.display,
                    visualization_settings: q.visualization_settings || {}
                }
            );
            cardMap[q.name] = { id: card.id, pos: q.pos };
        }
    }

    // 6. Ensure Dashboard
    if (config.dashboard) {
        const dashName = typeof config.dashboard === 'string' ? config.dashboard : config.dashboard.name;
        const dashDesc = config.dashboard.description || "";
        
        console.log(`🔄 Configuring Dashboard: ${dashName}...`);
        const dash = await client.dashboard.ensure(dashName, dashDesc, colId);

        // Collect tab names from config
        const tabNames = (config.dashboard.tabs) || [];
        if (tabNames.length > 0) {
            console.log(`📑 Dashboard has ${tabNames.length} tab(s): ${tabNames.join(', ')}`);
        }

        // Sync Cards
        const dashCards = [];
        for (const q of config.questions) {
            if (cardMap[q.name] && q.pos) {
                const cardConfig = {
                    id: cardMap[q.name].id,
                    ...q.pos
                };
                if (q.tab) cardConfig.tab = q.tab;
                dashCards.push(cardConfig);
            }
        }

        if (dashCards.length > 0) {
            await client.dashboard.syncCards(dash.id, dashCards, tabNames);
            console.log(`✅ Synced ${dashCards.length} cards to dashboard.`);
            console.log(`🔗 Dashboard Link: ${METABASE_URL}/dashboard/${dash.id}`);
        }
    }

    console.log("🚀 Deployment Complete.");
}

main().catch(console.error);
