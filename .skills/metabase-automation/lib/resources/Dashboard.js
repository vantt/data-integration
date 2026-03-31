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

    /**
     * Build tabs payload for a dashboard. Returns { tabsPayload, tabMap }.
     * tabMap maps tab names to IDs (negative temp IDs for new tabs).
     * IMPORTANT: Metabase requires tabs and dashcards in the same PUT request.
     */
    buildTabsPayload(existingTabs, tabNames) {
        const tabsPayload = [];
        const tabMap = new Map();

        // Reuse existing tabs by name
        for (const tab of existingTabs) {
            if (tabNames.includes(tab.name)) {
                tabsPayload.push({ id: tab.id, name: tab.name });
                tabMap.set(tab.name, tab.id);
            }
        }

        // Add new tabs with negative temp IDs
        let tempId = -1;
        for (const name of tabNames) {
            if (!tabMap.has(name)) {
                tabsPayload.push({ id: tempId, name });
                tabMap.set(name, tempId);
                tempId--;
            }
        }

        return { tabsPayload, tabMap };
    }

    async syncCards(dashboardId, cardConfigs, tabNames = []) {
        // Version Check
        const isModern = this.core.isVersionAtLeast("v0.58.0");
        console.log(`ℹ️ Metabase Version: ${this.core.version} (Strategy: ${isModern ? 'Modern/Dashcards' : 'Legacy/OrderedCards'})`);

        // cardConfigs: [{ id, row, col, size_x, size_y, parameter_mappings }]
        
        const dashboard = await this.core.request(`/api/dashboard/${dashboardId}`);
        // Support both property names if Metabase version varies, but v0.58+ uses dashcards
        let currentCards = dashboard.dashcards || dashboard.ordered_cards || [];
        const existingTabs = dashboard.tabs || [];

        // Build tabs payload if tab names are provided
        let tabsPayload = null;
        let tabMap = new Map();
        if (tabNames.length > 0) {
            const result = this.buildTabsPayload(existingTabs, tabNames);
            tabsPayload = result.tabsPayload;
            tabMap = result.tabMap;
            console.log(`📑 Tab payload: ${tabsPayload.map(t => `${t.name}(${t.id})`).join(', ')}`);
        }

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

            // Assign to tab: use tab name to look up ID from tabMap
            if (config.tab && tabMap.has(config.tab)) {
                cardObj.dashboard_tab_id = tabMap.get(config.tab);
            } else if (config.dashboard_tab_id) {
                cardObj.dashboard_tab_id = config.dashboard_tab_id;
            }
            
            // Only add 'id' if modern or if existing
            if (dashCardId !== undefined) {
                cardObj.id = dashCardId;
            }

            return cardObj;
        });

        try {
            let payload;
            
            if (isModern) {
                payload = { dashcards: cardPayload };
            } else {
                payload = { ordered_cards: cardPayload };
            }

            // Include tabs in the same PUT (Metabase requires tabs+cards together)
            if (tabsPayload) {
                payload.tabs = tabsPayload;
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
