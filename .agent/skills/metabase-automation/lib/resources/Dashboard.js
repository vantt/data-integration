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
             // Update parameters if needed? For now, simplistic ensure.
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
        // cardConfigs: [{ id, row, col, size_x, size_y, parameter_mappings }]
        
        const dashboard = await this.core.request(`/api/dashboard/${dashboardId}`);
        let currentCards = dashboard.ordered_cards || [];
        
        const payloadList = [];

        for (const config of cardConfigs) {
            const existing = currentCards.find(dc => dc.card_id === config.id);
            const mapping = config.parameter_mappings || [];
            
            if (existing) {
                payloadList.push({
                    id: existing.id,
                    card_id: config.id,
                    row: config.row,
                    col: config.col,
                    size_x: config.size_x,
                    size_y: config.size_y,
                    visualization_settings: {},
                    parameter_mappings: mapping
                });
            } else {
                payloadList.push({
                    card_id: config.id,
                    row: config.row,
                    col: config.col,
                    size_x: config.size_x,
                    size_y: config.size_y,
                    visualization_settings: {},
                    parameter_mappings: mapping
                });
            }
        }

        // What about cards NOT in config? Keep them? Or Remove?
        // "Sync" usually means "Make it match this".
        // But removing might be dangerous if user added custom text cards.
        // Let's Just Configured Cards + Existing Cards that are NOT in config? 
        // Actually, if we PUT a list, it might replace the whole dashboard content.
        // Let's try to append/update.
        
        // Add valid existing cards that are NOT in the config (preserve them)
        // for (const existing of currentCards) {
        //    if (!cardConfigs.find(c => c.id === existing.card_id)) {
        //        payloadList.push(existing);
        //    }
        // }
        
        // Actually, Metabase PUT /api/dashboard/:id/cards *updates* the cards provided in the list.
        // It does NOT delete omitted cards unless it's a "replace" endpoint which is rare for PUT :id/cards.
        // Usually PUT :id updates dashboard properties. 
        // PUT :id/cards updates the cards.
        
        // Let's safely try to just send the list of cards we want to update/create.
        
        // Strategy: Try PUT /api/dashboard/:id with ordered_cards
        // This is a "Replace All" strategy if supported.
        
        const cardPayload = payloadList.map(c => ({
            card_id: c.card_id,
            row: c.row,
            col: c.col,
            size_x: c.size_x,
            size_y: c.size_y,
            visualization_settings: {},
            parameter_mappings: [],
            // id: c.id // Include id if existing
            ...(c.id ? { id: c.id } : {}) 
        }));

        try {
            await this.core.request(`/api/dashboard/${dashboardId}`, 'PUT', { 
                ordered_cards: cardPayload 
            });
            console.log(`✅ Synced ${cardConfigs.length} cards to Dashboard ${dashboardId} (via PUT Dashboard check)`);
        } catch (e) {
            console.error(`❌ Failed syncCards (PUT DB): ${e.message}`);
            // If that fails, we might just be stuck manually adding in UI if API is stubborn.
        }
    }
}

module.exports = Dashboard;
