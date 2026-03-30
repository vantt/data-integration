const MetabaseCore = require('../lib/metabase_core');
const Collection = require('../lib/resources/Collection');
const Card = require('../lib/resources/Card');
const Dashboard = require('../lib/resources/Dashboard');
const Table = require('../lib/resources/Table');
const Metric = require('../lib/resources/Metric');
const Model = require('../lib/resources/Model');
const Segment = require('../lib/resources/Segment');
const Pulse = require('../lib/resources/Pulse');
const Snippet = require('../lib/resources/Snippet');

class MetabaseClient {
    /**
     * @param {string} url 
     * @param {string} apiKey 
     * @param {object} options - { authHeader: 'X-Metabase-Session' | 'x-api-key' }
     */
    constructor(url, apiKey, options = {}) {
        this.core = new MetabaseCore(url, apiKey, options);
        this.collection = new Collection(this.core);
        this.card = new Card(this.core);
        this.dashboard = new Dashboard(this.core);
        this.table = new Table(this.core);
        this.metric = new Metric(this.core);
        this.model = new Model(this.core);
        this.segment = new Segment(this.core);
        this.pulse = new Pulse(this.core);
        this.snippet = new Snippet(this.core);
    }

    async connect() {
        return await this.core.validateConnection();
    }

    /**
     * Helper to find a database ID by name
     * Handles the { data: [...] } structure from Metabase API
     */
    async findDatabaseId(name) {
        try {
            const res = await this.core.request('/api/database');
            let dbs = [];
            if (Array.isArray(res)) dbs = res;
            else if (res && Array.isArray(res.data)) dbs = res.data;
            
            const found = dbs.find(d => d.name === name);
            if (found) return found.id;
            
            console.warn(`⚠️ Database '${name}' not found. Available: ${dbs.map(d => d.name).join(', ')}`);
            return null;
        } catch (err) {
            console.error("Failed to fetch databases:", err.message);
            return null;
        }
    }
}

module.exports = MetabaseClient;
