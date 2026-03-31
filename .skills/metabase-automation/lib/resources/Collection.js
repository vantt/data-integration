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
     * Flatten collection tree to find by name.
     * @param {string} name - Collection name to search for
     * @param {object} options - { parent_id } to scope the search to a specific parent
     */
    async find(name, options = {}) {
        const root = await this.list();
        const parentId = options.parent_id || null;

        let queue = [...root];
        while (queue.length > 0) {
            const current = queue.shift();

            // Match by name AND parent scope (if provided)
            const nameMatch = current.name === name;
            const parentMatch = parentId === null
                ? true  // No parent filter — accept any match (backwards-compatible)
                : (current.location === `/${parentId}/` || current.parent_id === parentId);

            if (nameMatch && parentMatch) return current;

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
        const existing = await this.find(name, { parent_id: options.parent_id || null });
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
