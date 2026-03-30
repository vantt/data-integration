class Snippet {
    constructor(core) {
        this.core = core;
    }

    async list() {
        return await this.core.request('/api/native-query-snippet');
    }

    async find(name) {
        const snippets = await this.list();
        return snippets.find(s => s.name === name);
    }

    async ensure(name, content, description = null) {
        const existing = await this.find(name);
        
        const payload = {
            name,
            content,
            description
        };

        if (existing) {
            const updated = await this.core.request(`/api/native-query-snippet/${existing.id}`, 'PUT', payload);
            console.log(`✅ Updated Snippet '${name}' (ID: ${updated.id})`);
            return updated;
        } else {
            const created = await this.core.request('/api/native-query-snippet', 'POST', payload);
            console.log(`✅ Created Snippet '${name}' (ID: ${created.id})`);
            return created;
        }
    }
}

module.exports = Snippet;
