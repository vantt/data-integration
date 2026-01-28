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
    
    // 2. Question
    const q = await client.card.ensure(
        "Test Question Modular", 
        "SELECT 1 as test", 
        2, 
        col.id, 
        { display: "scalar" }
    );

    // 3. Dashboard
    const dash = await client.dashboard.ensure("Test Dashboard Modular", "Created via Skill", col.id);

    // 4. Update
    await client.dashboard.syncCards(dash.id, [
        { id: q.id, row: 0, col: 0, size_x: 6, size_y: 4 }
    ]);
}

if (require.main === module) {
    main();
}
