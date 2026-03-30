class Collection {
    constructor(core) {
        this.core = core;
    }

    /**
     * List all collections (flat list is standard API behavior usually)
     * Metabase /api/collection returns tree.
     */
    async list() {
        return await this.core.request('/api/collection');
    }

    /**
     * Flatten collection tree to find by name easily
     */
    async find(name) {
        // Simple BFS/DFS to find collection by name
        // Warning: Names are not unique in Metabase, this finds the first match.
        const root = await this.list();
        // The root response is a list of root collections.
        
        let queue = [...root];
        while (queue.length > 0) {
            const current = queue.shift();
            if (current.name === name) return current;
            
            // Metabase API usually doesn't return full children tree in list unless requested?
            // Actually /api/collection returns "tree".
            // Let's assume standard structure.
             if (current.children) {
                 queue.push(...current.children);
             }
        }
        return null;
    }

    /**
     * Get or Create a collection
     * @param {string} name 
     * @param {object} options - { parent_id, color, description }
     */
    async ensure(name, options = {}) {
        const existing = await this.find(name);
        if (existing) {
            console.log(`✅ Collection '${name}' exists (ID: ${existing.id})`);
            return existing;
        }

        const payload = {
            name,
            color: options.color || "#509EE3",
            description: options.description || null,
            parent_id: options.parent_id || null
        };

        const created = await this.core.request('/api/collection', 'POST', payload);
        console.log(`✅ Created Collection '${name}' (ID: ${created.id})`);
        return created;
    }
}

module.exports = Collection;
