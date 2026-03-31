const MetabaseClient = require('./metabase_client');

async function main() {
    const METABASE_URL = "http://127.0.0.1:3000";
    // Ensure you use your valid API Key
    const API_KEY = "mb_2r9ndMDpVIkzTLIaBnLofX+mgXxpvfyudQSNaCF6jJw=";

    const client = new MetabaseClient(METABASE_URL, API_KEY);

    if (!await client.connect()) return;

    console.log("🚀 Starting Modular Automation...");

    // 1. Collection
    const col = await client.collection.ensure("Sales Analytics");

    // 2. Questions
    const q1 = await client.card.ensure(
        "Revenue",
        "SELECT sum(net_revenue) as revenue FROM fact_orders WHERE date(order_timestamp) = current_date",
        2,
        col.id,
        { display: "scalar" }
    );

    const q2 = await client.card.ensure(
        "Order Detail",
        "SELECT * FROM fact_orders WHERE date(order_timestamp) = current_date LIMIT 50",
        2,
        col.id,
        { display: "table" }
    );

    // 3. Dashboard
    const dash = await client.dashboard.ensure("Test Dashboard Modular", "Created via Skill", col.id);

    // 4. Sync cards with tabs (tabs + dashcards in one PUT)
    await client.dashboard.syncCards(dash.id, [
        { id: q1.id, row: 0, col: 0, size_x: 6, size_y: 4, tab: "Overview" },
        { id: q2.id, row: 0, col: 0, size_x: 18, size_y: 8, tab: "Details" }
    ], ["Overview", "Details"]);

    // Without tabs (flat layout):
    // await client.dashboard.syncCards(dash.id, [
    //     { id: q1.id, row: 0, col: 0, size_x: 6, size_y: 4 }
    // ]);
}

if (require.main === module) {
    main();
}
