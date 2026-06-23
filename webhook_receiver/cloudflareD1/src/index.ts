export type { Env } from './utils';
import { Env, verifySignature, logError } from './utils';
import { SOURCE_CONFIGS, DEFAULT_CONFIG, SourceConfig } from './config';
import {
    handleHugScan,
    handleHugOptinLanding,
    handleHugTokenUpsert,
    handleHugCustomerUpsert,
    handleHugCampaignUpsert,
    handleHugCampaignPreview,
} from './hug-handler';

export default {
    async fetch(request: Request, env: Env, ctx: ExecutionContext): Promise<Response> {
        const url = new URL(request.url);

        // ── Hug Dynamic Touchpoint Platform ──────────────────────────────────
        // GET /h/:token  — public scan redirect (no HMAC; token is opaque)
        const hugScanMatch = url.pathname.match(/^\/h\/([^/]+)$/);
        if (request.method === "GET" && hugScanMatch) {
            return handleHugScan(request, env, ctx, hugScanMatch[1]);
        }
        // GET /optin/:token  — opt-in landing page; campaign destination_url points here
        const hugOptinMatch = url.pathname.match(/^\/optin\/([^/]+)$/);
        if (request.method === "GET" && hugOptinMatch) {
            return handleHugOptinLanding(request, env, hugOptinMatch[1]);
        }
        // POST /hug/*/upsert  — admin provisioning routes (HMAC via HUG_ADMIN_SECRET)
        if (request.method === "POST" && url.pathname === "/hug/token/upsert") {
            return handleHugTokenUpsert(request, env);
        }
        if (request.method === "POST" && url.pathname === "/hug/customer/upsert") {
            return handleHugCustomerUpsert(request, env);
        }
        if (request.method === "POST" && url.pathname === "/hug/campaign/upsert") {
            return handleHugCampaignUpsert(request, env);
        }
        if (request.method === "POST" && url.pathname === "/hug/campaign/preview") {
            return handleHugCampaignPreview(request, env);
        }

        // ── Existing webhook queue routes (UNCHANGED) ─────────────────────
        // Match /webhook/<source_system>/<entity_type>/<action>
        if (request.method === "POST" && url.pathname.startsWith("/webhook/")) {
            return handleWebhook(request, env);
        } else if (request.method === "GET" && url.pathname === "/poll") {
            return handlePoll(request, env);
        } else if (request.method === "DELETE" && url.pathname === "/ack") {
            return handleAck(request, env);
        } else if (request.method === "POST" && url.pathname === "/ack-batch") {
            return handleBatchAck(request, env);
        } else if (request.method === "POST" && url.pathname === "/release") {
            return handleRelease(request, env);
        }

        return new Response("Not Found", { status: 404 });
    },
};


async function handleWebhook(request: Request, env: Env): Promise<Response> {

    try {
        const url = new URL(request.url);
        const path = url.pathname;

        // Expected format: /webhook/<source_system>/<entity_type>/<action>
        const match = path.match(/\/webhook\/([^/]+)\/([^/]+)\/(.+)/);
        let textBody = "";

        try {
             textBody = await request.text();
        } catch (e) {
             const err = e as Error;
             await logError(env, 'REQUEST_READ_ERROR', err.message, err.stack);
             return new Response("Failed to read request body", { status: 400 });
        }

        if (!match) {
            await logError(env, 'INVALID_URL_FORMAT', `Invalid URL: ${path}`, undefined, undefined, textBody.substring(0, 1000));
            return new Response("Invalid URL format. Expected: /webhook/<source_system>/<entity_type>/<action>", { status: 400 });
        }

        const [, source_system, entity_type, action] = match;

        // 1. Load config for this source_system from code
        const config: SourceConfig = SOURCE_CONFIGS[source_system] || DEFAULT_CONFIG;

        // 2. Get Secret from Env
        const secretKey = config.secretKey;
        let secret = env[secretKey as string];

        // Fallback for default Global Secret if not found using specific key
        if (!secret && secretKey !== 'WEBHOOK_SECRET') {
             secret = env.WEBHOOK_SECRET;
        }

        const checkHmac = (env.CHECK_HMAC === 'true'); 
        
        let headerNames = config.headerNames;
        let encoding = config.encoding;

        // If using default config, respect the global env var for headers if set
        if (config === DEFAULT_CONFIG) {
             if (env.HMAC_HEADER_NAME) {
                 headerNames = env.HMAC_HEADER_NAME.split(',').map(h => h.trim());
             }
        }
        
        // 3. Perform Verification
        if (secret && checkHmac) {
            if (!headerNames || headerNames.length === 0) {
                 headerNames = ['x-hub-signature-256'];
            }

            let signatureFound = false;
            let isValid = false;

            for (const headerName of headerNames) {
                const signature = request.headers.get(headerName);
                if (signature) {
                    signatureFound = true;
                    
                    if (encoding === 'auto') {
                        // Heuristic: GitHub uses sha256=... (Hex). Sapo uses Base64 (no prefix usually).
                        if (signature.startsWith('sha256=')) {
                            const cleanSignature = signature.replace(/^sha256=/, '');
                            if (await verifySignature(secret, cleanSignature, textBody, 'hex')) {
                                isValid = true;
                                break;
                            }
                        } else {
                            // Assume Base64
                            if (await verifySignature(secret, signature, textBody, 'base64')) {
                                isValid = true;
                                break;
                            }
                        }
                    } else if (encoding === 'hex') {
                         const cleanSignature = signature.replace(/^sha256=/, '');
                         if (await verifySignature(secret, cleanSignature, textBody, 'hex')) {
                            isValid = true;
                            break;
                         }
                    } else if (encoding === 'base64') {
                         if (await verifySignature(secret, signature, textBody, 'base64')) {
                            isValid = true;
                            break;
                         }
                    }
                }
            }

            if (!signatureFound) {
                const msg = `Missing signature header. Expected one of: ${headerNames.join(', ')}`;
                await logError(env, 'HMAC_MISSING', msg, undefined, undefined, textBody.substring(0, 1000));
                return new Response(msg, { status: 401 });
            }

            if (!isValid) {
                await logError(env, 'HMAC_INVALID', "Invalid signature", undefined, undefined, textBody.substring(0, 1000));
                return new Response("Invalid signature", { status: 401 });
            }
        }

        let jsonBody;
        try {
            jsonBody = JSON.parse(textBody);
        } catch {
            // If body isn't JSON, treat it as raw text wrapped in an object
            jsonBody = { raw: textBody };
        }


        const headersJson = JSON.stringify(Object.fromEntries(request.headers));

        const payload = {
            source_system,
            entity_type,
            action,
            payload: jsonBody,
            received_at: new Date().toISOString()
        };

        // Queue depth guard: reject if too many unprocessed messages
        const depthResult = await env.DB.prepare(
            "SELECT COUNT(*) as cnt FROM webhooks WHERE status = 'NEW'"
        ).first<{ cnt: number }>();
        if ((depthResult?.cnt ?? 0) > 10000) {
            return new Response("Queue full", { status: 503 });
        }

        const id = crypto.randomUUID();
        const now = Date.now();

        // Insert into D1
        await env.DB.prepare(
            "INSERT INTO webhooks (msg_id, payload, source_system, headers, status, enqueued_at) VALUES (?, ?, ?, ?, 'NEW', ?)"
        )
            .bind(id, JSON.stringify(payload), source_system, headersJson, now)
            .run();

        return new Response("OK", { status: 200 });
    } catch (e) {
        const err = e as Error;
        console.error(e);
        await logError(env, 'WEBHOOK_HANDLER_ERROR', err.message, err.stack);
        return new Response("Internal Server Error", { status: 500 });
    }

}

async function handlePoll(request: Request, env: Env): Promise<Response> {
    const url = new URL(request.url);
    const now = Date.now();
    const LOCK_TIMEOUT = 60000; // 60 seconds

    // Parse params
    const limitParam = parseInt(url.searchParams.get("limit") || "10", 10);
    const limit = Math.min(Math.max(limitParam, 1), 1000); // Clamp between 1 and 1000
    const sourceSystem = url.searchParams.get("source_system");

    // 1. Find pending items (NEW or EXPIRED PROCESSING)
    // 2. Lock them for this consumer
    // Note: SQLite uses dynamic typing. VARCHAR is treated as TEXT.
    // We use ORDER BY created_at ASC to ensure FIFO (Oldest First).
    
    let stmt: string;
    let params: any[];

    if (sourceSystem) {
        // Optimized query using idx_source_status_locked
        stmt = `
        UPDATE webhooks
        SET status = 'PROCESSING', locked_until = ?
        WHERE msg_id IN (
          SELECT msg_id FROM webhooks
          WHERE source_system = ?
            AND (status = 'NEW' 
                 OR (status = 'PROCESSING' AND locked_until < ?))
          ORDER BY enqueued_at ASC
          LIMIT ?
        )
        RETURNING *
      `;
      params = [now + LOCK_TIMEOUT, sourceSystem, now, limit];
    } else {
        // Generic query using idx_status_locked
        stmt = `
        UPDATE webhooks
        SET status = 'PROCESSING', locked_until = ?
        WHERE msg_id IN (
          SELECT msg_id FROM webhooks
          WHERE status = 'NEW' 
             OR (status = 'PROCESSING' AND locked_until < ?)
          ORDER BY enqueued_at ASC
          LIMIT ?
        )
        RETURNING *
      `;
      params = [now + LOCK_TIMEOUT, now, limit];
    }

    try {
        const { results } = await env.DB.prepare(stmt)
            .bind(...params)
            .all();

        return Response.json({ messages: results });
    } catch (e) {
        const err = e as Error;
        console.error(e);
        await logError(env, 'POLL_HANDLER_ERROR', err.message, err.stack);
        return new Response("Internal Server Error", { status: 500 });
    }
}

async function handleBatchAck(request: Request, env: Env): Promise<Response> {
    try {
        const body = await request.json() as any;
        const ids = body.ids;

        if (!Array.isArray(ids) || ids.length === 0) {
             return new Response("Missing 'ids' array in body", { status: 400 });
        }

        // Limit batch size to prevent too complex queries if necessary, though 1000 is likely fine for specific logic.
        // For D1, we might need to be careful about the number of bind parameters if we expanded them.
        // However, 'DELETE FROM webhooks WHERE msg_id IN (...)' with many ? can be heavy.
        // Let's use a loop or chunks if we expect massive batches, but for now assuming reasonable limits (e.g. 1000).
        // D1 has a limit on SQL variables (SQLITE_MAX_VARIABLE_NUMBER default is often 999 or 32766). 
        // 1000 should be safe enough if the default is high, but let's be safe.
        // Actually, executing a single DELETE WHERE ID IN (...) is efficient.

        // Construct the query: DELETE FROM webhooks WHERE msg_id IN (?, ?, ...)
        const placeholders = ids.map(() => "?").join(", ");
        const stmt = `DELETE FROM webhooks WHERE msg_id IN (${placeholders})`;

        await env.DB.prepare(stmt)
            .bind(...ids)
            .run();

        return new Response("ACK BATCH", { status: 200 });
    } catch (e) {
        const err = e as Error;
        console.error(e);
        await logError(env, 'BATCH_ACK_ERROR', err.message, err.stack);
        return new Response("Internal Server Error", { status: 500 });
    }
}

async function handleAck(request: Request, env: Env): Promise<Response> {
    const url = new URL(request.url);
    const id = url.searchParams.get("id");

    if (!id) {
        return new Response("Missing id param", { status: 400 });
    }

    try {
        await env.DB.prepare("DELETE FROM webhooks WHERE msg_id = ?").bind(id).run();
        return new Response("ACK", { status: 200 });
    } catch (e) {
        const err = e as Error;
        console.error(e);
        await logError(env, 'ACK_ERROR', err.message, err.stack);
        return new Response("Internal Server Error", { status: 500 });
    }
}

async function handleRelease(request: Request, env: Env): Promise<Response> {
    try {
        const body = await request.json() as any;
        const id = body.id;

        if (!id) {
            return new Response("Missing id in body", { status: 400 });
        }

        // Release the item: Reset status to NEW and clear locked_until
        await env.DB.prepare(
            "UPDATE webhooks SET status = 'NEW', locked_until = NULL WHERE msg_id = ?"
        )
            .bind(id)
            .run();

        return new Response("RELEASED", { status: 200 });
    } catch (e) {
        const err = e as Error;
        console.error(e);
        await logError(env, 'RELEASE_ERROR', err.message, err.stack);
        return new Response("Internal Server Error", { status: 500 });
    }
}
