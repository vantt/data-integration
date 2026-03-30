class Card {
    constructor(core) {
        this.core = core;
    }

    async find(name, collectionId = null) {
        // Searching is tricky. /api/card returns valid cards.
        // Or search /api/collection/:id/items
        
        if (collectionId) {
            // Note: /api/collection/:id/items might NOT return archived items by default.
            // If we want to find archived ones, we might need ?archived=true (if API supports) 
            // or use /api/search?q=name&archived=true
            const items = await this.core.request(`/api/collection/${collectionId}/items?archived=true`); // Try to get everything
            if (Array.isArray(items)) {
                 const found = items.find(i => i.model === 'card' && i.name === name);
                 
                 // If found, ensure it is active
                 if (found && found.id) {
                     // Check if actually archived (the list item usually has 'archived' prop)
                     // If we are not sure, we can just GET the card details
                     // But optimization: just PUT { archived: false } if we suspect it.
                     // Let's being safe:
                     // The item from collection list might not have 'archived' field populated reliably? 
                     // Let's Fetch details to be sure, or just Unarchive blindly?
                     // Unarchive blindly is cheap.
                     // Wait, we need to check if it IS archived to avoid spamming logs.
                     // Assuming 'archived' prop exists in item list.
                     
                     // If strictly archived, restoring it.
                     // But collection/items endpoint behavior regarding archived is complex.
                     // Let's assume if we found it, we use it.
                     // We will Unarchive just in case.
                     // await this.core.request(`/api/card/${found.id}`, 'PUT', { archived: false });
                     // Doing this in 'ensure' is better.
                 }
                 return found; 
            }
        } else {
             // Search globally
        }
        return null;
    }

    /**
     * Create or Update a Native SQL Question
     */
    async ensure(name, sql, databaseId, collectionId, options = {}) {
        const existing = await this.find(name, collectionId);

        const payload = {
            name,
            description: options.description || null,
            collection_id: collectionId,
            dataset_query: {
                type: "native",
                native: { 
                    query: sql,
                    "template-tags": options.template_tags || {} 
                },
                database: databaseId
            },
            display: options.display || "table",
            visualization_settings: options.visualization_settings || {}
        };

        if (existing) {
            console.log(`ℹ️ Question '${name}' exists (ID: ${existing.id})`);
            
            // UNARCHIVE if needed (Blindly ensure active)
            try {
               await this.core.request(`/api/card/${existing.id}`, 'PUT', { archived: false });
            } catch (e) {
               // ignore
            }

            // UPDATE
            const updated = await this.core.request(`/api/card/${existing.id}`, 'PUT', payload);
            console.log(`✅ Updated Question '${name}' (ID: ${updated.id})`);
            return updated;
        } else {
// ...
            // CREATE
            const created = await this.core.request('/api/card', 'POST', payload);
            console.log(`✅ Created Question '${name}' (ID: ${created.id})`);
            return created;
        }
    }
}

module.exports = Card;
