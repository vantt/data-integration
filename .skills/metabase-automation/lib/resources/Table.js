class Table {
    constructor(core) {
        this.core = core;
    }

    async list() {
        return await this.core.request('/api/table');
    }

    /**
     * Find table by name (and optionally schema_name or db_id)
     */
    async find(name, schema = null) {
        const tables = await this.list();
        return tables.find(t => {
            const nameMatch = t.name === name || t.display_name === name;
            if (schema) {
                return nameMatch && t.schema === schema;
            }
            return nameMatch;
        });
    }

    /**
     * Get fields for a table
     */
    async getFields(tableId) {
        return await this.core.request(`/api/table/${tableId}/query_metadata`);
    }
}

module.exports = Table;
