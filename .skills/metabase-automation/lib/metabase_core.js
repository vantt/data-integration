const fs = require('fs');
const path = require('path');
const http = require('http');
const https = require('https');

// Reusable agents — HTTPS uses rejectUnauthorized:false for local self-signed certs
const httpAgent  = new http.Agent({ keepAlive: true });
const httpsAgent = new https.Agent({ rejectUnauthorized: false, keepAlive: true });

/** Minimal fetch-like wrapper using native http/https modules */
function nodeFetch(url, { method = 'GET', headers = {}, body } = {}) {
    return new Promise((resolve, reject) => {
        const parsed = new URL(url);
        const isHttps = parsed.protocol === 'https:';
        const agent = isHttps ? httpsAgent : httpAgent;
        const reqBody = body ? Buffer.from(body, 'utf-8') : null;
        const reqHeaders = { ...headers };
        if (reqBody) reqHeaders['Content-Length'] = reqBody.length;

        const opts = {
            hostname: parsed.hostname,
            port: parsed.port || (isHttps ? 443 : 80),
            path: parsed.pathname + parsed.search,
            method,
            headers: reqHeaders,
            agent
        };

        const lib = isHttps ? https : http;
        const req = lib.request(opts, (res) => {
            const chunks = [];
            res.on('data', c => chunks.push(c));
            res.on('end', () => {
                const text = Buffer.concat(chunks).toString('utf-8');
                resolve({
                    status: res.statusCode,
                    ok: res.statusCode >= 200 && res.statusCode < 300,
                    headers: { get: (k) => res.headers[k.toLowerCase()] },
                    json: () => Promise.resolve(JSON.parse(text)),
                    text: () => Promise.resolve(text)
                });
            });
        });
        req.on('error', reject);
        if (reqBody) req.write(reqBody);
        req.end();
    });
}

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
            "Content-Type": "application/json; charset=utf-8"
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
            const res = await nodeFetch(`${this.url}${endpoint}`, options);
            
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
            
            // Try to detect version
            try {
                // /api/session/properties usually contains version info
                const props = await this.request('/api/session/properties');
                this.version = props.version?.tag || "v0.0.0"; // e.g., "v0.60.2"
            } catch (vErr) {
                console.warn("⚠️ Could not detect Metabase version:", vErr.message);
                this.version = "v0.0.0";
            }

            console.log(`✅ Connected to Metabase as: ${user.common_name} (${user.email}) [Version: ${this.version}]`);
            return true;
        } catch (e) {
            console.error(`❌ Connection Failed: ${e.message}`);
            return false;
        }
    }

    /**
     * Helper to check if current version satisfies a requirement
     * @param {string} minVersion - e.g. "v0.60.0"
     */
    isVersionAtLeast(minVersion) {
        // Simple string/lexical comparison for now, or strip 'v'
        const cleanCurrent = this.version.replace(/^v/, '');
        const cleanMin = minVersion.replace(/^v/, '');
        return cleanCurrent.localeCompare(cleanMin, undefined, { numeric: true, sensitivity: 'base' }) >= 0;
    }
}

module.exports = MetabaseCore;
