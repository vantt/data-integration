/**
 * hug-handler.ts — Hug Dynamic Touchpoint Platform routes
 *
 * Surfaces added (all additive, existing routes untouched):
 *   GET  /h/:token                   — public scan redirect (no HMAC)
 *   GET  /optin/:token               — opt-in landing page (mobile-first Vietnamese HTML)
 *   POST /hug/token/upsert           — admin: batch upsert hug_token rows
 *   POST /hug/customer/upsert        — admin: batch upsert hug_customer rows
 *   POST /hug/campaign/upsert        — admin: upsert hug_campaign rows
 *
 * Auth:
 *   /h/:token    — public; token is opaque, no PII on URL.
 *   /optin/:token — public; form posts to /webhook/hug/optin/created (generic handler).
 *   /hug/*       — HMAC-secured via HUG_ADMIN_SECRET (same pattern as Sapo).
 *
 * Opt-in capture: the landing form POSTs to POST /webhook/hug/optin/created which goes
 * through the existing generic webhook handler. That handler stores:
 *   source_system = 'hug'  (from URL path segment)
 *   payload = { source_system, entity_type: 'optin', action: 'created', payload: <body>, received_at }
 * The local consumer (hug_webhook_consumer.py) reads entity_type from the wrapper
 * after parsing the JSON payload column. Inner payload contract:
 *   { token, phone, name?, consent: { phone: bool, ts: iso }, ts: iso }
 *
 * Routing model (discussion-hug.md §7):
 *   targeting JSON = { field: [val, ...], ... }
 *   Between keys  = AND  (all conditions must pass)
 *   Within a list = OR   (any value matches)
 *   Missing key   = no constraint on that attribute
 *   Campaigns sorted by priority ASC; first match wins.
 *   DEFAULT campaign = targeting '{}' at max priority (always matches).
 */

import { Env, verifySignature, normalizeToken } from './utils';

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
        // Normalize: accept dashed grouped codes, HUG- prefixed printed codes,
        // full scan URLs, and any mix of -, _, ., space separators typed by staff.
        token = normalizeToken(token);

        // Guard: a valid bare token is exactly 12 chars.  Anything else after
        // normalization (garbage, truncated, wrong input) redirects immediately
        // without burning a D1 read.
        if (token.length !== 12) {
            return Response.redirect(getFallbackUrl(env), 302);
        }

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

// ---------------------------------------------------------------------------
// GET /optin/:token  — opt-in landing page (public, no HMAC)
//
// Campaign destination_url points here (e.g. https://hug.fjp.vn/optin/TOKEN).
// Serves a self-contained mobile-first Vietnamese HTML page with:
//   - Zalo OA follow CTA (link from HUG_ZALO_OA_URL env var, safe placeholder fallback)
//   - Phone + name form + consent checkbox
//   - On submit: POST JSON to /webhook/hug/optin/created, then show success state
//
// Token is embedded in the page for the form; no D1 lookup needed at landing time.
// The form submit validates phone client-side; server-side validation is in
// the generic /webhook handler (token/phone required, VN phone normalisation).
// ---------------------------------------------------------------------------

/** Zalo OA follow URL from env; placeholder prevents broken links in dev/staging. */
function getZaloOaUrl(env: Env): string {
    return env.HUG_ZALO_OA_URL ?? 'https://zalo.me/YOUR_OA_ID';
}

/** Vietnamese phone normalisation: strip spaces/dashes, rewrite 0XX → +84XX, validate. */
export function normaliseVnPhone(raw: string): string | null {
    // Remove all non-digit characters except leading +
    const stripped = raw.replace(/[\s\-().]/g, '');
    // Rewrite +84 prefix to 0 for normalisation, then back
    let digits = stripped;
    if (digits.startsWith('+84')) {
        digits = '0' + digits.slice(3);
    } else if (digits.startsWith('84') && digits.length === 11) {
        digits = '0' + digits.slice(2);
    }
    // Vietnamese mobile: 10 digits starting with 0[3-9]
    if (/^0[3-9]\d{8}$/.test(digits)) {
        return digits;
    }
    return null;
}

export async function handleHugOptinLanding(
    request: Request,
    env: Env,
    token: string
): Promise<Response> {
    // Reject obviously invalid tokens early (empty or path-traversal chars)
    if (!token || token.length > 128 || /[<>"'`\\/]/.test(token)) {
        return new Response('Bad Request', { status: 400 });
    }

    const zaloUrl = getZaloOaUrl(env);
    // Escape token for safe embedding in HTML/JS — it's alphanumeric but be explicit
    const safeToken = token.replace(/[<>&"']/g, '');

    // Read campaign attribution from URL param (appended by scan redirect)
    const url = new URL(request.url);
    const rawCampaignId = url.searchParams.get('hug_campaign');
    // Allow only reasonable alphanumeric IDs (matches campaign_id column values)
    const campaignId: string | null =
        rawCampaignId && /^[\w-]{1,64}$/.test(rawCampaignId) ? rawCampaignId : null;

    // Fetch offer_ref from D1 for this campaign — graceful fallback: missing/unknown = no code shown
    let offerCode: string | null = null;
    if (campaignId) {
        try {
            const row = await env.DB.prepare(
                "SELECT offer_ref FROM hug_campaign WHERE campaign_id = ? AND status = 'active' LIMIT 1"
            ).bind(campaignId).first<{ offer_ref: string | null }>();
            // Sanitise offer code: Sapo codes are alphanumeric; strip any stray HTML chars
            const raw = row?.offer_ref ?? null;
            offerCode = raw ? raw.replace(/[<>&"']/g, '') : null;
        } catch {
            // D1 lookup failure must never crash the landing page — show no code
            offerCode = null;
        }
    }

    // Inline success content: show offer code if available, otherwise generic message
    const successContent = offerCode
        ? `<p style="margin-bottom:12px">Mã ưu đãi của bạn:</p>
        <p style="font-size:1.6rem;font-weight:700;color:#e8231a;letter-spacing:.1em;margin-bottom:8px">${offerCode}</p>
        <p style="color:#555;font-size:.85rem;margin-bottom:20px">Nhập mã này khi đặt hàng để được giảm giá.</p>`
        : `<p>Cảm ơn bạn. Chúng tôi sẽ liên hệ sớm nhất có thể.</p>`;

    const html = `<!DOCTYPE html>
<html lang="vi">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<meta name="robots" content="noindex">
<title>Nhận ưu đãi từ chúng tôi</title>
<style>
  *{box-sizing:border-box;margin:0;padding:0}
  body{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;background:#f5f5f5;color:#222;min-height:100vh;display:flex;align-items:center;justify-content:center;padding:16px}
  .card{background:#fff;border-radius:16px;padding:28px 24px;max-width:420px;width:100%;box-shadow:0 2px 16px rgba(0,0,0,.08)}
  h1{font-size:1.3rem;font-weight:700;margin-bottom:8px;color:#1a1a2e}
  .sub{font-size:.95rem;color:#555;margin-bottom:20px;line-height:1.5}
  .zalo-btn{display:flex;align-items:center;justify-content:center;gap:10px;background:#0068FF;color:#fff;text-decoration:none;border-radius:10px;padding:14px;font-size:1rem;font-weight:600;margin-bottom:24px;transition:opacity .15s}
  .zalo-btn:hover{opacity:.88}
  .zalo-icon{width:24px;height:24px;flex-shrink:0}
  .divider{display:flex;align-items:center;gap:8px;margin-bottom:20px;color:#aaa;font-size:.85rem}
  .divider::before,.divider::after{content:'';flex:1;height:1px;background:#e0e0e0}
  label{display:block;font-size:.9rem;font-weight:600;margin-bottom:6px;color:#333}
  input[type=tel],input[type=text]{width:100%;border:1px solid #ddd;border-radius:8px;padding:12px;font-size:1rem;margin-bottom:14px;outline:none;transition:border-color .15s}
  input:focus{border-color:#0068FF}
  .consent{display:flex;gap:10px;align-items:flex-start;margin-bottom:20px}
  .consent input{margin-top:3px;width:18px;height:18px;flex-shrink:0;cursor:pointer}
  .consent span{font-size:.85rem;color:#555;line-height:1.5}
  .submit-btn{width:100%;background:#e8231a;color:#fff;border:none;border-radius:10px;padding:14px;font-size:1rem;font-weight:700;cursor:pointer;transition:opacity .15s}
  .submit-btn:hover{opacity:.88}
  .submit-btn:disabled{opacity:.5;cursor:not-allowed}
  .error{color:#e8231a;font-size:.85rem;margin-bottom:12px;display:none}
  .success{display:none;text-align:center;padding:20px 0}
  .success h2{color:#00a651;font-size:1.2rem;margin-bottom:10px}
  .success p{color:#555;font-size:.9rem;line-height:1.5;margin-bottom:20px}
</style>
</head>
<body>
<div class="card">
  <!-- Value proposition -->
  <h1>Nhận ưu đãi dành riêng cho bạn</h1>
  <p class="sub">Theo dõi Zalo OA để nhận thông báo ưu đãi và hỗ trợ nhanh nhất. Hoặc để lại số điện thoại để chúng tôi liên hệ trực tiếp.</p>

  <!-- Zalo OA follow CTA -->
  <a class="zalo-btn" href="${zaloUrl}" target="_blank" rel="noopener">
    <svg class="zalo-icon" viewBox="0 0 48 48" fill="none" xmlns="http://www.w3.org/2000/svg">
      <rect width="48" height="48" rx="12" fill="#fff"/>
      <text x="6" y="34" font-size="28" font-family="Arial,sans-serif" font-weight="900" fill="#0068FF">Z</text>
    </svg>
    Theo dõi Zalo OA
  </a>

  <div class="divider">hoặc để lại số điện thoại</div>

  <!-- Opt-in form -->
  <form id="optin-form" novalidate>
    <label for="phone">Số điện thoại <span style="color:#e8231a">*</span></label>
    <input type="tel" id="phone" name="phone" placeholder="0912 345 678" autocomplete="tel" inputmode="numeric">

    <label for="name">Họ tên (không bắt buộc)</label>
    <input type="text" id="name" name="name" placeholder="Nguyễn Văn A" autocomplete="name">

    <div class="consent">
      <input type="checkbox" id="consent" name="consent">
      <span>Tôi đồng ý để <strong>Fine Japan Vietnam</strong> liên hệ tư vấn và gửi thông tin ưu đãi qua số điện thoại này.</span>
    </div>

    <div class="error" id="form-error">Vui lòng kiểm tra lại thông tin.</div>
    <button class="submit-btn" type="submit" id="submit-btn">Nhận ưu đãi ngay</button>
  </form>

  <!-- Success state (shown after submit) -->
  <div class="success" id="success-state">
    <h2>Đã nhận thông tin!</h2>
    ${successContent}
    <a class="zalo-btn" href="${zaloUrl}" target="_blank" rel="noopener">
      <svg class="zalo-icon" viewBox="0 0 48 48" fill="none" xmlns="http://www.w3.org/2000/svg">
        <rect width="48" height="48" rx="12" fill="#fff"/>
        <text x="6" y="34" font-size="28" font-family="Arial,sans-serif" font-weight="900" fill="#0068FF">Z</text>
      </svg>
      Theo dõi Zalo OA
    </a>
  </div>
</div>

<script>
(function(){
  var TOKEN = ${JSON.stringify(safeToken)};
  var CAMPAIGN_ID = ${JSON.stringify(campaignId ?? '')};
  var SUBMIT_URL = '/webhook/hug/optin/created';

  function normPhone(raw) {
    var s = raw.replace(/[\\s\\-().]/g, '');
    if (s.startsWith('+84')) s = '0' + s.slice(3);
    else if (/^84\\d{9}$/.test(s)) s = '0' + s.slice(2);
    return /^0[3-9]\\d{8}$/.test(s) ? s : null;
  }

  var form = document.getElementById('optin-form');
  var errEl = document.getElementById('form-error');
  var btn = document.getElementById('submit-btn');
  var successEl = document.getElementById('success-state');

  function showError(msg) {
    errEl.textContent = msg;
    errEl.style.display = 'block';
  }
  function clearError() { errEl.style.display = 'none'; }

  form.addEventListener('submit', function(e) {
    e.preventDefault();
    clearError();

    var phoneRaw = document.getElementById('phone').value.trim();
    var name = document.getElementById('name').value.trim();
    var consentChecked = document.getElementById('consent').checked;
    var phone = normPhone(phoneRaw);

    if (!phone) { showError('Số điện thoại không hợp lệ. Vui lòng nhập lại (VD: 0912 345 678).'); return; }
    if (!consentChecked) { showError('Bạn cần đồng ý để chúng tôi liên hệ.'); return; }

    btn.disabled = true;
    btn.textContent = 'Đang gửi…';

    var ts = new Date().toISOString();
    var body = {
      token: TOKEN,
      phone: phone,
      consent: { phone: true, ts: ts },
      ts: ts
    };
    if (name) body.name = name;
    // Include campaign attribution so the pipeline can tie this opt-in to a campaign
    if (CAMPAIGN_ID) body.campaign_id = CAMPAIGN_ID;

    fetch(SUBMIT_URL, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body)
    })
    .then(function(r) {
      if (!r.ok) throw new Error('server_error_' + r.status);
      form.style.display = 'none';
      successEl.style.display = 'block';
    })
    .catch(function(err) {
      btn.disabled = false;
      btn.textContent = 'Nhận ưu đãi ngay';
      showError('Gửi thất bại, vui lòng thử lại. (' + err.message + ')');
    });
  });
})();
</script>
</body>
</html>`;

    return new Response(html, {
        status: 200,
        headers: { 'Content-Type': 'text/html; charset=utf-8' },
    });
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
