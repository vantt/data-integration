const fs = require('fs');
const path = require('path');

class MetabaseCore {
    /**
     * @param {string} url - Metabase Base URL
     * @param {string} apiKeyOrToken - Metabase API Key or Session Token
     * @param {object} options - Optional config
     * @param {string} options.authHeader - Header key to use (default: 'x-api-key', use 'X-Metabase-Session' for tokens)
     */
    constructor(url, apiKeyOrToken, options = {}) {
        if (!url || !apiKeyOrToken) {
            throw new Error("Metabase URL and API Key/Token are required.");
        }
        this.url = url.replace(/\/$/, ''); // Remove trailing slash
        
        const authHeader = options.authHeader || 'x-api-key';
        this.headers = {
            [authHeader]: apiKeyOrToken,
            "Content-Type": "application/json"
        };
    }

    /**
     * Generic API Request Wrapper
     * @param {string} endpoint - e.g. '/api/user/current'
     * @param {string} method - GET, POST, PUT, DELETE
     * @param {object} body - JSON body
     */
    async request(endpoint, method = 'GET', body = null) {
        const options = {
            method,
            headers: this.headers
        };

        if (body) {
            options.body = JSON.stringify(body);
        }

        try {
            const res = await fetch(`${this.url}${endpoint}`, options);
            
            // Handle 204 No Content
            if (res.status === 204) return true;

            const contentType = res.headers.get("content-type");
            let data;
            if (contentType && contentType.includes("application/json")) {
                data = await res.json();
            } else {
                data = await res.text();
            }

            if (!res.ok) {
                // Attach status to error for handling
                const error = new Error(`Metabase API Error ${res.status}: ${JSON.stringify(data)}`);
                error.status = res.status;
                error.data = data;
                throw error;
            }

            return data;
        } catch (error) {
            // Rethrow with context if needed, or just let it bubble
            throw error;
        }
    }

    async validateConnection() {
        try {
            const user = await this.request('/api/user/current');
            console.log(`✅ Connected to Metabase as: ${user.common_name} (${user.email})`);
            return true;
        } catch (e) {
            console.error(`❌ Connection Failed: ${e.message}`);
            return false;
        }
    }
}

module.exports = MetabaseCore;
