class Metric {
    constructor(core) {
        this.core = core;
    }

    async list() {
        return await this.core.request('/api/metric');
    }

    async find(name, tableId = null) {
        const metrics = await this.list();
        return metrics.find(m => {
            const nameMatch = m.name === name;
            if (tableId) return nameMatch && m.table_id === tableId;
            return nameMatch;
        });
    }

    /**
     * Create or Update a Metric
     * @param {string} name 
     * @param {string} description 
     * @param {number} tableId 
     * @param {object} definition - { aggregation: [], filter: [] }
     */
    async ensure(name, description, tableId, definition) {
        const existing = await this.find(name, tableId);
        
        const payload = {
            name,
            description,
            table_id: tableId,
            definition
        };

        if (existing) {
            // Update
            const updated = await this.core.request(`/api/metric/${existing.id}`, 'PUT', payload);
            console.log(`✅ Updated Metric '${name}' (ID: ${updated.id})`);
            return updated;
        } else {
            // Create
            const created = await this.core.request('/api/metric', 'POST', payload);
            console.log(`✅ Created Metric '${name}' (ID: ${created.id})`);
            return created;
        }
    }
}

module.exports = Metric;
