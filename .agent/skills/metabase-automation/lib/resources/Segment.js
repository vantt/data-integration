class Segment {
    constructor(core) {
        this.core = core;
    }

    async list() {
        return await this.core.request('/api/segment');
    }

    async find(name, tableId = null) {
        const segments = await this.list();
        return segments.find(s => {
            const nameMatch = s.name === name;
            if (tableId) return nameMatch && s.table_id === tableId;
            return nameMatch;
        });
    }

    async ensure(name, description, tableId, definition) {
        // definition: { filter: [...] } // MBQL filter clause
        const existing = await this.find(name, tableId);
        
        const payload = {
            name,
            description,
            table_id: tableId,
            definition
        };

        if (existing) {
            const updated = await this.core.request(`/api/segment/${existing.id}`, 'PUT', payload);
            console.log(`✅ Updated Segment '${name}' (ID: ${updated.id})`);
            return updated;
        } else {
            const created = await this.core.request('/api/segment', 'POST', payload);
            console.log(`✅ Created Segment '${name}' (ID: ${created.id})`);
            return created;
        }
    }
}

module.exports = Segment;
