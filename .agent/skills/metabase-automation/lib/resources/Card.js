class Card {
    constructor(core) {
        this.core = core;
    }

    async find(name, collectionId = null) {
        // Searching is tricky. /api/card returns valid cards.
        // Or search /api/collection/:id/items
        
        if (collectionId) {
            const items = await this.core.request(`/api/collection/${collectionId}/items`);
            if (Array.isArray(items)) {
                 const found = items.find(i => i.model === 'card' && i.name === name);
                 return found; 
            }
        } else {
             // Search globally (less efficient)
             // Using /api/search?q=name might be better?
             // Let's assume we usually look in a specific collection for management.
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
            // UPDATE
            // PUT /api/card/:id
            // Need to merge? Or overwrite? Overwrite is "Configuration Management" style.
            const updated = await this.core.request(`/api/card/${existing.id}`, 'PUT', payload);
            console.log(`✅ Updated Question '${name}' (ID: ${updated.id})`);
            return updated;
        } else {
            // CREATE
            const created = await this.core.request('/api/card', 'POST', payload);
            console.log(`✅ Created Question '${name}' (ID: ${created.id})`);
            return created;
        }
    }
}

module.exports = Card;
