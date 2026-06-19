/**
 * hug-handler.ts — Hug Dynamic Touchpoint Platform routes
 *
 * Surfaces added (all additive, existing routes untouched):
 *   GET  /h/:token                   — public scan redirect (no HMAC)
 *   POST /hug/token/upsert           — admin: batch upsert hug_token rows
 *   POST /hug/customer/upsert        — admin: batch upsert hug_customer rows
 *   POST /hug/campaign/upsert        — admin: upsert hug_campaign rows
 *
 * Auth:
 *   /h/:token   — public; token is opaque, no PII on URL.
 *   /hug/*      — HMAC-secured via HUG_ADMIN_SECRET (same pattern as Sapo).
 *
 * Routing model (discussion-hug.md §7):
 *   targeting JSON = { field: [val, ...], ... }
 *   Between keys  = AND  (all conditions must pass)
 *   Within a list = OR   (any value matches)
 *   Missing key   = no constraint on that attribute
 *   Campaigns sorted by priority ASC; first match wins.
 *   DEFAULT campaign = targeting '{}' at max priority (always matches).
 */

import { Env, verifySignature } from './utils';

// ---------------------------------------------------------------------------
// Types for D1 rows
// ---------------------------------------------------------------------------

interface HugToken {
    token: string;
    customer_id: string | null;
    op_type: string;
    order_code: string | null;
    channel: string | null;
    ship_date: string | null;
    sku: string | null;
    campaign_hint: string | null;
    status: string;
    batch_id: string | null;
    created_at: string;
}

interface HugCustomer {
    customer_id: string;
    tier: string | null;
    recency_days: number | null;
    value_group: string | null;
    is_contactable: number;  // 0 | 1
    updated_at: string;
}

interface HugCampaign {
    campaign_id: string;
    name: string;
    targeting: string;        // JSON string
    destination_type: string;
    destination_url: string;
    offer_ref: string | null;
    priority: number;
    schedule_start: string | null;
    schedule_end: string | null;
    quota_total: number | null;
    quota_used: number;
    status: string;
    updated_at: string;
}

/** Resolved context assembled from hug_token + hug_customer for matching */
interface ScanContext {
    op_type: string;
    tier: string | null;
    channel: string | null;
    value_group: string | null;
    recency_days: number | null;
    is_contactable: number;
    customer_id: string | null;
    order_code: string | null;
    ship_date: string | null;
    sku: string | null;
}

// ---------------------------------------------------------------------------
// Campaign list cache (Worker-level in-memory, TTL ~60s)
// Avoids a D1 read on every hot-path scan.
// ---------------------------------------------------------------------------
let _campaignCache: HugCampaign[] | null = null;
let _campaignCacheTs = 0;
const CAMPAIGN_CACHE_TTL_MS = 60_000;

async function fetchActiveCampaigns(db: D1Database): Promise<HugCampaign[]> {
    const now = Date.now();
    if (_campaignCache && now - _campaignCacheTs < CAMPAIGN_CACHE_TTL_MS) {
        return _campaignCache;
    }
    const { results } = await db.prepare(
        `SELECT * FROM hug_campaign
         WHERE status = 'active'
           AND (schedule_start IS NULL OR schedule_start <= datetime('now'))
           AND (schedule_end   IS NULL OR schedule_end   >= datetime('now'))
           AND (quota_total IS NULL OR quota_used < quota_total)
         ORDER BY priority ASC`
    ).all<HugCampaign>();
    _campaignCache = results ?? [];
    _campaignCacheTs = now;
    return _campaignCache;
}

/** Invalidate campaign cache after admin upsert so next scan sees fresh data */
function invalidateCampaignCache(): void {
    _campaignCache = null;
    _campaignCacheTs = 0;
}

// ---------------------------------------------------------------------------
// Targeting matcher (§7 AND-between-keys / OR-within-list)
// ---------------------------------------------------------------------------

/**
 * Evaluate whether a campaign's targeting JSON matches the given scan context.
 *
 * Supported attributes and their context types:
 *   op_type       string  → in list
 *   tier          string  → in list
 *   channel       string  → in list
 *   value_group   string  → in list
 *   is_contactable number → in list (0 or 1)
 *   recency_days  number  → supports gte / lte (object form: { gte: N } | { lte: N })
 *
 * Targeting format:
 *   Simple equality list:  { "tier": ["VIP", "CORE"] }
 *   Numeric range:         { "recency_days": { "gte": 30, "lte": 90 } }
 *   Mixed:                 { "op_type": ["package_insert"], "tier": ["VIP"] }
 *   Empty object {}:       matches everything (DEFAULT).
 *
 * Returns true if ALL keys match (AND), false if any key fails.
 * Missing key in targeting = no constraint (pass through).
 */
function matchesTargeting(targetingJson: string, ctx: ScanContext): boolean {
    let targeting: Record<string, unknown>;
    try {
        targeting = JSON.parse(targetingJson);
    } catch {
        // Malformed targeting → treat as DEFAULT (match all)
        return true;
    }

    const keys = Object.keys(targeting);
    // Empty object = DEFAULT campaign, always matches
    if (keys.length === 0) return true;

    for (const key of keys) {
        const rule = targeting[key];
        const ctxValue = (ctx as unknown as Record<string, unknown>)[key];

        if (Array.isArray(rule)) {
            // OR within the list: context value must be in the list
            // If context value is null/undefined → no match (the key has a constraint)
            if (ctxValue === null || ctxValue === undefined) return false;
            const matched = (rule as unknown[]).some(
                (v) => String(v) === String(ctxValue)
            );
            if (!matched) return false;
        } else if (typeof rule === 'object' && rule !== null) {
            // Numeric range object: { gte?: N, lte?: N, gt?: N, lt?: N }
            const numCtx = typeof ctxValue === 'number' ? ctxValue : null;
            if (numCtx === null) return false;
            const r = rule as Record<string, number>;
            if (r.gte !== undefined && !(numCtx >= r.gte)) return false;
            if (r.lte !== undefined && !(numCtx <= r.lte)) return false;
            if (r.gt  !== undefined && !(numCtx >  r.gt))  return false;
            if (r.lt  !== undefined && !(numCtx <  r.lt))  return false;
        } else {
            // Scalar equality
            if (ctxValue === null || ctxValue === undefined) return false;
            if (String(rule) !== String(ctxValue)) return false;
        }
    }
    return true;
}

/**
 * Select the winning campaign from the active list for a given context.
 * Campaigns already sorted priority ASC; first match wins.
 * Returns null if no campaign matches (caller should use fallback URL).
 */
function selectCampaign(campaigns: HugCampaign[], ctx: ScanContext): HugCampaign | null {
    for (const c of campaigns) {
        if (matchesTargeting(c.targeting, ctx)) {
            return c;
        }
    }
    return null;
}

// ---------------------------------------------------------------------------
// Fallback URL: configurable via HUG_FALLBACK_URL env var;
// defaults to a simple 404-ish landing (should be overridden in prod).
// ---------------------------------------------------------------------------
function getFallbackUrl(env: Env): string {
    return env.HUG_FALLBACK_URL ?? 'https://fgcare.vn';
}

// ---------------------------------------------------------------------------
// GET /h/:token  — public hot path
// ---------------------------------------------------------------------------

export async function handleHugScan(
    request: Request,
    env: Env,
    ctx: ExecutionContext,
    token: string
): Promise<Response> {
    try {
        // 1. Look up token in D1 (left join customer for tier)
        const row = await env.DB.prepare(
            `SELECT t.*, c.tier, c.recency_days, c.value_group, c.is_contactable
             FROM hug_token t
             LEFT JOIN hug_customer c ON c.customer_id = t.customer_id
             WHERE t.token = ? AND t.status = 'bound'`
        ).bind(token).first<HugToken & Partial<HugCustomer>>();

        const scanContext: ScanContext | null = row ? {
            op_type:       row.op_type,
            tier:          row.tier ?? null,
            channel:       row.channel ?? null,
            value_group:   row.value_group ?? null,
            recency_days:  row.recency_days ?? null,
            is_contactable: row.is_contactable ?? 0,
            customer_id:   row.customer_id ?? null,
            order_code:    row.order_code ?? null,
            ship_date:     row.ship_date ?? null,
            sku:           row.sku ?? null,
        } : null;

        // 2. Select winning campaign (or fallback)
        let redirectUrl = getFallbackUrl(env);
        let campaignId: string | null = null;

        if (scanContext) {
            const campaigns = await fetchActiveCampaigns(env.DB);
            const winner = selectCampaign(campaigns, scanContext);
            if (winner) {
                // Append attribution query params (non-PII)
                const dest = new URL(winner.destination_url);
                dest.searchParams.set('hug_token', token);
                dest.searchParams.set('hug_campaign', winner.campaign_id);
                redirectUrl = dest.toString();
                campaignId = winner.campaign_id;
            }
        }

        // 3. Non-blocking: insert scan event into existing webhooks queue (source_system='hug')
        //    Consumer drains via GET /poll?source_system=hug → local pipeline
        ctx.waitUntil(insertScanEvent(env, token, scanContext, campaignId));

        // 4. 302 redirect — immediate, not blocked by waitUntil
        return Response.redirect(redirectUrl, 302);

    } catch (e) {
        const err = e as Error;
        console.error('[hug-scan]', err.message, err.stack);
        // Graceful degradation: still redirect to fallback rather than 500
        return Response.redirect(getFallbackUrl(env), 302);
    }
}

/** Insert hug scan event into the existing webhooks FIFO queue (non-blocking via waitUntil) */
async function insertScanEvent(
    env: Env,
    token: string,
    ctx: ScanContext | null,
    campaignId: string | null
): Promise<void> {
    try {
        const id = crypto.randomUUID();
        const now = Date.now();
        const payload = {
            source_system: 'hug',
            entity_type: 'scan',
            action: 'created',
            payload: {
                token,
                customer_id: ctx?.customer_id ?? null,
                op_type: ctx?.op_type ?? null,
                channel: ctx?.channel ?? null,
                campaign_id: campaignId,
                tier: ctx?.tier ?? null,
                scanned_at: new Date().toISOString(),
            },
            received_at: new Date().toISOString(),
        };
        await env.DB.prepare(
            "INSERT INTO webhooks (msg_id, payload, source_system, headers, status, enqueued_at) VALUES (?, ?, 'hug', '{}', 'NEW', ?)"
        ).bind(id, JSON.stringify(payload), now).run();
    } catch (e) {
        // Non-fatal: scan redirect already happened; log and swallow
        console.error('[hug-scan-event]', (e as Error).message);
    }
}

// ---------------------------------------------------------------------------
// HMAC verification for admin routes — reuses utils.verifySignature
// Admin routes use HUG_ADMIN_SECRET + SHA-256 HMAC, hex-encoded,
// delivered in header X-Hug-Signature (value: sha256=<hex>).
// ---------------------------------------------------------------------------

async function verifyAdminHmac(request: Request, body: string, env: Env): Promise<boolean> {
    const secret = env.HUG_ADMIN_SECRET;
    if (!secret) {
        // No secret configured → reject (do not allow open admin)
        return false;
    }
    const sigHeader = request.headers.get('x-hug-signature') ?? '';
    if (!sigHeader.startsWith('sha256=')) return false;
    const hexSig = sigHeader.slice('sha256='.length);
    return verifySignature(secret, hexSig, body, 'hex');
}

// ---------------------------------------------------------------------------
// POST /hug/token/upsert  — batch upsert hug_token rows (tokens bound locally)
// Body: { rows: HugTokenRow[] }
// ---------------------------------------------------------------------------

interface HugTokenRow {
    token: string;
    customer_id?: string | null;
    op_type: string;
    order_code?: string | null;
    channel?: string | null;
    ship_date?: string | null;
    sku?: string | null;
    campaign_hint?: string | null;
    status?: string;
    batch_id?: string | null;
}

export async function handleHugTokenUpsert(request: Request, env: Env): Promise<Response> {
    const body = await request.text();
    if (!(await verifyAdminHmac(request, body, env))) {
        return new Response('Unauthorized', { status: 401 });
    }

    let parsed: { rows: HugTokenRow[] };
    try {
        parsed = JSON.parse(body);
    } catch {
        return new Response('Invalid JSON', { status: 400 });
    }

    const rows = parsed.rows;
    if (!Array.isArray(rows) || rows.length === 0) {
        return new Response("Missing 'rows' array", { status: 400 });
    }

    // Validate required fields
    for (const r of rows) {
        if (!r.token || !r.op_type) {
            return new Response('Each row must have token and op_type', { status: 400 });
        }
    }

    // Batch upsert using D1 batch API (up to 100 rows per call; caller should chunk larger batches)
    const stmts = rows.map((r) =>
        env.DB.prepare(
            `INSERT INTO hug_token (token, customer_id, op_type, order_code, channel, ship_date, sku, campaign_hint, status, batch_id)
             VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
             ON CONFLICT(token) DO UPDATE SET
               customer_id   = excluded.customer_id,
               op_type       = excluded.op_type,
               order_code    = excluded.order_code,
               channel       = excluded.channel,
               ship_date     = excluded.ship_date,
               sku           = excluded.sku,
               campaign_hint = excluded.campaign_hint,
               status        = excluded.status,
               batch_id      = excluded.batch_id`
        ).bind(
            r.token,
            r.customer_id ?? null,
            r.op_type,
            r.order_code ?? null,
            r.channel ?? null,
            r.ship_date ?? null,
            r.sku ?? null,
            r.campaign_hint ?? null,
            r.status ?? 'bound',
            r.batch_id ?? null
        )
    );

    try {
        await env.DB.batch(stmts);
        return Response.json({ ok: true, upserted: rows.length });
    } catch (e) {
        console.error('[hug-token-upsert]', (e as Error).message);
        return new Response('Internal Server Error', { status: 500 });
    }
}

// ---------------------------------------------------------------------------
// POST /hug/customer/upsert  — batch upsert hug_customer (nightly tier push)
// Body: { rows: HugCustomerRow[] }
// ---------------------------------------------------------------------------

interface HugCustomerRow {
    customer_id: string;
    tier?: string | null;
    recency_days?: number | null;
    value_group?: string | null;
    is_contactable?: number;  // 0 | 1
}

export async function handleHugCustomerUpsert(request: Request, env: Env): Promise<Response> {
    const body = await request.text();
    if (!(await verifyAdminHmac(request, body, env))) {
        return new Response('Unauthorized', { status: 401 });
    }

    let parsed: { rows: HugCustomerRow[] };
    try {
        parsed = JSON.parse(body);
    } catch {
        return new Response('Invalid JSON', { status: 400 });
    }

    const rows = parsed.rows;
    if (!Array.isArray(rows) || rows.length === 0) {
        return new Response("Missing 'rows' array", { status: 400 });
    }

    for (const r of rows) {
        if (!r.customer_id) {
            return new Response('Each row must have customer_id', { status: 400 });
        }
    }

    const stmts = rows.map((r) =>
        env.DB.prepare(
            `INSERT INTO hug_customer (customer_id, tier, recency_days, value_group, is_contactable, updated_at)
             VALUES (?, ?, ?, ?, ?, strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
             ON CONFLICT(customer_id) DO UPDATE SET
               tier           = excluded.tier,
               recency_days   = excluded.recency_days,
               value_group    = excluded.value_group,
               is_contactable = excluded.is_contactable,
               updated_at     = excluded.updated_at`
        ).bind(
            r.customer_id,
            r.tier ?? null,
            r.recency_days ?? null,
            r.value_group ?? null,
            r.is_contactable ?? 0
        )
    );

    try {
        await env.DB.batch(stmts);
        return Response.json({ ok: true, upserted: rows.length });
    } catch (e) {
        console.error('[hug-customer-upsert]', (e as Error).message);
        return new Response('Internal Server Error', { status: 500 });
    }
}

// ---------------------------------------------------------------------------
// POST /hug/campaign/upsert  — upsert hug_campaign rows (admin UI save)
// Body: { rows: HugCampaignRow[] }
// ---------------------------------------------------------------------------

interface HugCampaignRow {
    campaign_id: string;
    name: string;
    targeting?: Record<string, unknown>;  // will be JSON.stringified
    destination_type: string;
    destination_url: string;
    offer_ref?: string | null;
    priority?: number;
    schedule_start?: string | null;
    schedule_end?: string | null;
    quota_total?: number | null;
    quota_used?: number;
    status?: string;
}

export async function handleHugCampaignUpsert(request: Request, env: Env): Promise<Response> {
    const body = await request.text();
    if (!(await verifyAdminHmac(request, body, env))) {
        return new Response('Unauthorized', { status: 401 });
    }

    let parsed: { rows: HugCampaignRow[] };
    try {
        parsed = JSON.parse(body);
    } catch {
        return new Response('Invalid JSON', { status: 400 });
    }

    const rows = parsed.rows;
    if (!Array.isArray(rows) || rows.length === 0) {
        return new Response("Missing 'rows' array", { status: 400 });
    }

    for (const r of rows) {
        if (!r.campaign_id || !r.name || !r.destination_type || !r.destination_url) {
            return new Response('Each row must have campaign_id, name, destination_type, destination_url', { status: 400 });
        }
        // Validate targeting is parseable
        if (r.targeting !== undefined && typeof r.targeting !== 'object') {
            return new Response('targeting must be an object', { status: 400 });
        }
    }

    const stmts = rows.map((r) =>
        env.DB.prepare(
            `INSERT INTO hug_campaign
               (campaign_id, name, targeting, destination_type, destination_url,
                offer_ref, priority, schedule_start, schedule_end,
                quota_total, quota_used, status, updated_at)
             VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
             ON CONFLICT(campaign_id) DO UPDATE SET
               name             = excluded.name,
               targeting        = excluded.targeting,
               destination_type = excluded.destination_type,
               destination_url  = excluded.destination_url,
               offer_ref        = excluded.offer_ref,
               priority         = excluded.priority,
               schedule_start   = excluded.schedule_start,
               schedule_end     = excluded.schedule_end,
               quota_total      = excluded.quota_total,
               quota_used       = CASE WHEN excluded.quota_used IS NOT NULL THEN excluded.quota_used ELSE hug_campaign.quota_used END,
               status           = excluded.status,
               updated_at       = excluded.updated_at`
        ).bind(
            r.campaign_id,
            r.name,
            JSON.stringify(r.targeting ?? {}),
            r.destination_type,
            r.destination_url,
            r.offer_ref ?? null,
            r.priority ?? 100,
            r.schedule_start ?? null,
            r.schedule_end ?? null,
            r.quota_total ?? null,
            r.quota_used ?? 0,
            r.status ?? 'active'
        )
    );

    try {
        await env.DB.batch(stmts);
        // Flush campaign cache so next scan sees fresh rules
        invalidateCampaignCache();
        return Response.json({ ok: true, upserted: rows.length });
    } catch (e) {
        console.error('[hug-campaign-upsert]', (e as Error).message);
        return new Response('Internal Server Error', { status: 500 });
    }
}
