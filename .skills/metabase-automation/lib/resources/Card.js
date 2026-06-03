class Card {
    constructor(core) {
        this.core = core;
    }

    async find(name, collectionId = null) {
        if (collectionId) {
            const res = await this.core.request(`/api/collection/${collectionId}/items?models=card`);
            const items = Array.isArray(res) ? res : (res && Array.isArray(res.data) ? res.data : []);
            return items.find(i => i.name === name) || null;
        } else {
            // Search globally via /api/search
            const res = await this.core.request(`/api/search?q=${encodeURIComponent(name)}&models=card`);
            const items = Array.isArray(res) ? res : (res && Array.isArray(res.data) ? res.data : []);
            return items.find(i => i.name === name) || null;
        }
    }

    /**
     * Find an ACTIVE (non-archived) card by exact name in a specific collection.
     * Used by deploy_from_markdown for idempotent card upsert — prevents orphan
     * duplicate accumulation when the card is not yet wired into the dashboard's
     * dashcards (e.g. fresh dashboard or post-archive-cleanup scenario).
     *
     * @param {string} name - Exact card name to match
     * @param {number} collectionId - Collection to scope the search (required)
     * @returns {object|null} Metabase card object or null if not found
     */
    async findActiveInCollection(name, collectionId) {
        if (!collectionId) return null;
        const res = await this.core.request(`/api/collection/${collectionId}/items?models=card`);
        const items = Array.isArray(res) ? res : (res && Array.isArray(res.data) ? res.data : []);
        // Match by exact name and exclude archived cards (archived=true means soft-deleted)
        return items.find(i => i.name === name && i.archived !== true) || null;
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
