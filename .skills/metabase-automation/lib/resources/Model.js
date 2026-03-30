class Model {
    constructor(core) {
        this.core = core;
    }

    async find(name) {
        // Models are Cards with dataset=true — search as card, pick first exact match
        const res = await this.core.request(`/api/search?q=${encodeURIComponent(name)}&models=card`);
        const items = Array.isArray(res) ? res : (res && Array.isArray(res.data) ? res.data : []);
        return items.find(c => c.name === name) || null;
    }

    /**
     * Create/Update a Model (Dataset)
     */
    async ensure(name, query, databaseId, collectionId, options = {}) {
        const existing = await this.find(name);
        
        const payload = {
            name,
            description: options.description || null,
            collection_id: collectionId,
            dataset_query: {
                type: "native", // Models can be native SQL or query builder
                native: { query: query },
                database: databaseId
            },
            display: "table",
            dataset: true, // This makes it a Model!
            visualization_settings: options.visualization_settings || {}
        };
        
        // Add metadata_positions, result_metadata if needed for models to work well?
        // Usually Metabase infers.

        if (existing) {
            const updated = await this.core.request(`/api/card/${existing.id}`, 'PUT', payload);
            console.log(`✅ Updated Model '${name}' (ID: ${updated.id})`);
            return updated;
        } else {
            const created = await this.core.request('/api/card', 'POST', payload);
            console.log(`✅ Created Model '${name}' (ID: ${created.id})`);
            return created;
        }
    }
}

module.exports = Model;
