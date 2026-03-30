class Dashboard {
    constructor(core) {
        this.core = core;
    }

    async find(name) {
        const dbs = await this.core.request('/api/dashboard');
        return dbs.find(d => d.name === name) || null;
    }

    async ensure(name, description, collectionId, parameters = []) {
        const existing = await this.find(name);
        if (existing) {
             console.log(`ℹ️ Dashboard '${name}' exists (ID: ${existing.id})`);
             
             // If archived, unarchive it
             if (existing.archived) {
                 console.log(`♻️ Unarchiving Dashboard '${name}'...`);
                 await this.core.request(`/api/dashboard/${existing.id}`, 'PUT', { archived: false });
             }
             
             // Ensure it's in the right collection (fix potential mismatch)
             if (existing.collection_id !== collectionId) {
                  console.log(`📦 Moving Dashboard '${name}' to collection ${collectionId}...`);
                  await this.core.request(`/api/dashboard/${existing.id}`, 'PUT', { collection_id: collectionId });
             }

             return existing;
        }

        const created = await this.core.request('/api/dashboard', 'POST', {
            name,
            description,
            collection_id: collectionId,
            parameters: parameters // e.g., [{ name: "Date", slug: "date", id: "...", type: "date/all-options" }]
        });
        console.log(`✅ Created Dashboard '${name}' (ID: ${created.id})`);
        return created;
    }

    async syncCards(dashboardId, cardConfigs) {
        // Version Check
        const isModern = this.core.isVersionAtLeast("v0.58.0");
        console.log(`ℹ️ Metabase Version: ${this.core.version} (Strategy: ${isModern ? 'Modern/Dashcards' : 'Legacy/OrderedCards'})`);

        // cardConfigs: [{ id, row, col, size_x, size_y, parameter_mappings }]
        
        const dashboard = await this.core.request(`/api/dashboard/${dashboardId}`);
        // Support both property names if Metabase version varies, but v0.58+ uses dashcards
        let currentCards = dashboard.dashcards || dashboard.ordered_cards || [];
        
        let tempIdCounter = -1;

        const cardPayload = cardConfigs.map(config => {
            // Match by card_id (the Question ID)
            const existing = currentCards.find(dc => dc.card_id === config.id);
            
            // Modern Logic: Negative IDs for new cards
            // Legacy Logic: Usually just card_id is enough, but passing id doesn't hurt if we have it.
            // If legacy and new, we don't *need* negative ID, but let's stick to standard unless it breaks legacy.
            // Legacy `ordered_cards` usually ignores `id` for new cards and relies on `card_id`.
            
            let dashCardId;
            if (existing) {
                dashCardId = existing.id;
            } else {
                dashCardId = isModern ? tempIdCounter-- : undefined; // Legacy might prefer undefined or ignore it
            }

            const cardObj = {
                card_id: config.id,      // The Question ID
                row: config.row,
                col: config.col,
                size_x: config.size_x,
                size_y: config.size_y,
                visualization_settings: {}, // Required
                parameter_mappings: config.parameter_mappings || [], // Required
                series: [] 
            };
            
            // Only add 'id' if modern or if existing
            if (dashCardId !== undefined) {
                cardObj.id = dashCardId;
            }

            return cardObj;
        });

        try {
            let payload;
            
            if (isModern) {
                // v0.58+: Use 'dashcards'
                payload = { 
                    dashcards: cardPayload 
                };
            } else {
                // Legacy: Use 'ordered_cards'
                // Note: Legacy created new cards via POST /cards, but ordered_cards PUT also worked for reordering.
                // Pure creation via ordered_cards might be risky on very old versions, but generally works for updates.
                // If strict legacy support needed, we might re-introduce POST logic here.
                // For now, assuming PUT ordered_cards is sufficient for v0.40+ updates.
                payload = { 
                    ordered_cards: cardPayload 
                };
            }

            console.log(`Using '${isModern ? 'dashcards' : 'ordered_cards'}' payload...`);

            const updatedDashboard = await this.core.request(`/api/dashboard/${dashboardId}`, 'PUT', payload);
            
            // Response might use differing keys
            const count = (updatedDashboard.dashcards ? updatedDashboard.dashcards.length : 0) || 
                          (updatedDashboard.ordered_cards ? updatedDashboard.ordered_cards.length : 0);
            
            console.log(`✅ Synced cards. Dashboard now has ${count} cards.`);
            
            if (count === 0 && cardPayload.length > 0) {
                 console.warn("⚠️ Warning: Dashboard returned 0 cards. Payload might be rejected.", JSON.stringify(payload));
            }

        } catch (e) {
            console.error(`❌ Failed syncCards (PUT /api/dashboard/${dashboardId}): ${e.message}`);
            if (e.data) console.error("Error Data:", JSON.stringify(e.data));
        }
    }
}

module.exports = Dashboard;
