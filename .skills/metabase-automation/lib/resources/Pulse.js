class Pulse {
    constructor(core) {
        this.core = core;
    }

    async list() {
        return await this.core.request('/api/pulse');
    }

    async find(name) {
        const pulses = await this.list();
        return pulses.find(p => p.name === name);
    }

    /**
     * Create/Update a Pulse (Email/Slack Alert)
     * @param {string} name 
     * @param {Array<object>} cards - [{ id: cardId, include_csv: false, include_xls: false }]
     * @param {Array<object>} channels - [{ channel_type: "email", enabled: true, recipients: [{email: "..."}] }]
     * @param {object} options - { skip_if_empty: true, collection_id: ... }
     */
    async ensure(name, cards, channels, options = {}) {
        const existing = await this.find(name);
        
        const payload = {
            name,
            cards,
            channels,
            skip_if_empty: options.skip_if_empty !== false,
            collection_id: options.collection_id || null
        };

        if (existing) {
            const updated = await this.core.request(`/api/pulse/${existing.id}`, 'PUT', payload);
            console.log(`✅ Updated Pulse '${name}' (ID: ${updated.id})`);
            return updated;
        } else {
            const created = await this.core.request('/api/pulse', 'POST', payload);
            console.log(`✅ Created Pulse '${name}' (ID: ${created.id})`);
            return created;
        }
    }
}

module.exports = Pulse;
