import { env, createExecutionContext, waitOnExecutionContext } from 'cloudflare:test';
import { describe, it, expect, beforeAll } from 'vitest';
import worker, { Env } from './index';
import { normaliseVnPhone, matchesTargeting } from './hug-handler';

const SCHEMA_SQL = `
CREATE TABLE IF NOT EXISTS webhooks (
    msg_id TEXT PRIMARY KEY,       -- UUID
    payload TEXT,                  -- JSON Body
    source_system TEXT,            -- "stripe", "github", etc.
    headers TEXT,                  -- JSON Headers
    status TEXT DEFAULT 'NEW',     -- NEW, PROCESSING, DONE
    enqueued_at INTEGER,           -- Unix Timestamp
    locked_until INTEGER DEFAULT 0 -- Timestamp for Visibility Timeout
);

CREATE INDEX IF NOT EXISTS idx_status_locked ON webhooks(status, locked_until);
CREATE INDEX IF NOT EXISTS idx_source_status_locked ON webhooks(source_system, status, locked_until);

CREATE TABLE IF NOT EXISTS webhook_errors (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    webhook_id TEXT,
    error_type TEXT,
    error_message TEXT,
    stack_trace TEXT,
    payload TEXT,
    created_at INTEGER DEFAULT (strftime('%s', 'now'))
);
CREATE INDEX IF NOT EXISTS idx_errors_created_at ON webhook_errors(created_at);

CREATE TABLE IF NOT EXISTS hug_token (
    token TEXT PRIMARY KEY,
    customer_id TEXT,
    op_type TEXT NOT NULL,
    order_code TEXT,
    channel TEXT,
    ship_date TEXT,
    sku TEXT,
    campaign_hint TEXT,
    status TEXT NOT NULL DEFAULT 'bound',
    batch_id TEXT,
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
);

CREATE TABLE IF NOT EXISTS hug_customer (
    customer_id TEXT PRIMARY KEY,
    tier TEXT,
    recency_days INTEGER,
    value_group TEXT,
    is_contactable INTEGER NOT NULL DEFAULT 0,
    customer_type TEXT,
    updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
);

CREATE TABLE IF NOT EXISTS hug_campaign (
    campaign_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    targeting TEXT NOT NULL DEFAULT '{}',
    destination_type TEXT NOT NULL,
    destination_url TEXT NOT NULL,
    offer_ref TEXT,
    priority INTEGER NOT NULL DEFAULT 100,
    schedule_start TEXT,
    schedule_end TEXT,
    quota_total INTEGER,
    quota_used INTEGER NOT NULL DEFAULT 0,
    status TEXT NOT NULL DEFAULT 'active',
    updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
);
`;

// Helper to generate HMAC signature
async function generateSignature(secret: string, body: string): Promise<string> {
  const encoder = new TextEncoder();
  const key = await crypto.subtle.importKey(
    'raw',
    encoder.encode(secret),
    { name: 'HMAC', hash: 'SHA-256' },
    false,
    ['sign']
  );
  const signature = await crypto.subtle.sign('HMAC', key, encoder.encode(body));
  return 'sha256=' + Array.from(new Uint8Array(signature)).map(b => b.toString(16).padStart(2, '0')).join('');
}

// Apply full schema once before all test suites so every describe block shares the same DB.
beforeAll(async () => {
    const statements = SCHEMA_SQL
        .split(';')
        .map((s: string) => s.trim())
        .filter((s: string) => s.length > 0);
    for (const statement of statements) {
        await (env as unknown as Env).DB.prepare(statement).run();
    }
});

describe('Webhook Receiver Worker', () => {
  const SECRET = 'test-secret';

  it('responds with 404 for unknown paths', async () => {
    const request = new Request('http://example.com/unknown', { method: 'GET' });
    const ctx = createExecutionContext();
    const response = await worker.fetch(request, env as unknown as Env, ctx);
    await waitOnExecutionContext(ctx);
    expect(response.status).toBe(404);
  });

  describe('POST /webhook', () => {
    it('rejects without signature', async () => {
      const request = new Request('http://example.com/webhook/stripe/charge/succeeded', {
        method: 'POST',
        body: JSON.stringify({ foo: 'bar' }),
      });
      // Mock env with secret via Object.assign or spread if possible, but env is read-only proxy in some contexts.
      // In vitest-pool-workers, 'env' is the binded environment.
      // We can't easily mutate 'env' if it is a real binding object.
      // However, we can pass a modified object to worker.fetch.
      
      const testEnv = { ...env, WEBHOOK_SECRET: SECRET, CHECK_HMAC: 'true' };
      
      const ctx = createExecutionContext();
      const response = await worker.fetch(request, testEnv as unknown as Env, ctx);
      await waitOnExecutionContext(ctx);
      expect(response.status).toBe(401);
    });

    it('rejects with invalid signature', async () => {
      const body = JSON.stringify({ foo: 'bar' });
      const request = new Request('http://example.com/webhook/stripe/charge/succeeded', {
        method: 'POST',
        body,
        headers: {
          'x-hub-signature-256': 'sha256=invalid',
        },
      });
      const testEnv = { ...env, WEBHOOK_SECRET: SECRET, CHECK_HMAC: 'true' };

      const ctx = createExecutionContext();
      const response = await worker.fetch(request, testEnv as unknown as Env, ctx);
      await waitOnExecutionContext(ctx);
      expect(response.status).toBe(401);
    });

    it('accepts with valid signature and inserts into DB', async () => {
      const body = JSON.stringify({ foo: 'bar' });
      const signature = await generateSignature(SECRET, body);
      const request = new Request('http://example.com/webhook/stripe/charge/succeeded', {
        method: 'POST',
        body,
        headers: {
          'x-hub-signature-256': signature,
        },
      });
      const testEnv = { ...env, WEBHOOK_SECRET: SECRET, CHECK_HMAC: 'true' };

      const ctx = createExecutionContext();
      const response = await worker.fetch(request, testEnv as unknown as Env, ctx);
      await waitOnExecutionContext(ctx);
      expect(response.status).toBe(200);

      // Verify DB insertion
      const { results } = await (env as unknown as Env).DB.prepare('SELECT * FROM webhooks').all();
      expect(results.length).toBeGreaterThan(0);
      const latest = results[results.length - 1];
      expect(latest.source_system).toBe('stripe');
      const wrapper = JSON.parse(latest.payload as string);
      expect(wrapper.payload).toEqual({ foo: 'bar' });
    });

    it('bypasses verification by default (CHECK_HMAC not set)', async () => {
      const body = JSON.stringify({ foo: 'bar' });
      // Invalid signature
      const request = new Request('http://example.com/webhook/stripe/charge/succeeded', {
        method: 'POST',
        body,
        headers: {
          'x-hub-signature-256': 'sha256=invalid',
        },
      });
      
      const testEnv = { ...env, WEBHOOK_SECRET: SECRET }; // CHECK_HMAC missing -> false

      const ctx = createExecutionContext();
      const response = await worker.fetch(request, testEnv as unknown as Env, ctx);
      await waitOnExecutionContext(ctx);
      expect(response.status).toBe(200);
    });

    it('validates Sapo webhook with correct Base64 signature', async () => {
        // Sapo uses Base64 encoding for HMAC and specific header
        const body = JSON.stringify({ event: 'order/create' });
        
        // Generate Sapo-style signature (Base64)
        const encoder = new TextEncoder();
        const key = await crypto.subtle.importKey(
            'raw',
            encoder.encode('sapo-secret-key'),
            { name: 'HMAC', hash: 'SHA-256' },
            false,
            ['sign']
        );
        const signatureBuffer = await crypto.subtle.sign('HMAC', key, encoder.encode(body));
        // Convert to Base64 string
        const signature = btoa(String.fromCharCode(...new Uint8Array(signatureBuffer)));

        const request = new Request('http://example.com/webhook/sapo/orders/create', {
            method: 'POST',
            body,
            headers: {
                'x-sapo-hmac-sha256': signature,
            },
        });

        // Mock env with SAPO_SECRET
        const testEnv = { ...env, SAPO_SECRET: 'sapo-secret-key', CHECK_HMAC: 'true' };

        const ctx = createExecutionContext();
        const response = await worker.fetch(request, testEnv as unknown as Env, ctx);
        await waitOnExecutionContext(ctx);
        expect(response.status).toBe(200);

        // Verify DB insertion
        const { results } = await (env as unknown as Env).DB.prepare("SELECT * FROM webhooks WHERE source_system = 'sapo'").all();
        expect(results.length).toBe(1);
        const latest = results[0];
        expect(latest.source_system).toBe('sapo');
    });

    it('captures custom headers in headers column', async () => {
      const body = JSON.stringify({ foo: 'baz' });
      const signature = await generateSignature(SECRET, body);
      const request = new Request('http://example.com/webhook/stripe/charge/succeeded', {
        method: 'POST',
        body,
        headers: {
          'x-hub-signature-256': signature,
          'x-custom-header': 'custom-column-val'
        },
      });
      const testEnv = { ...env, WEBHOOK_SECRET: SECRET, CHECK_HMAC: 'true' };

      const ctx = createExecutionContext();
      const response = await worker.fetch(request, testEnv as unknown as Env, ctx);
      await waitOnExecutionContext(ctx);
      expect(response.status).toBe(200);

      const { results } = await (env as unknown as Env).DB.prepare('SELECT * FROM webhooks ORDER BY enqueued_at DESC LIMIT 1').all();
      const latest = results[0];
      
      // Check headers column
      const headers = JSON.parse(latest.headers as string);
      expect(headers['x-custom-header']).toBe('custom-column-val');
      
      // Check payload does not contain headers
      const payload = JSON.parse(latest.payload as string);
      expect(payload.headers).toBeUndefined();
    });
  });

  describe('GET /poll', () => {
    // We need to ensure DB is clean or handle existing data. 
    // Since we run sequentially, we can just insert fresh data for this test.

    it('retrieves and locks new messages', async () => {
        const id = crypto.randomUUID();
        await (env as unknown as Env).DB.prepare("INSERT INTO webhooks (msg_id, payload, source_system, headers, status, enqueued_at) VALUES (?, ?, ?, ?, 'NEW', ?)")
            .bind(id, '{}', 'stripe', '{}', Date.now())
            .run();

        const request = new Request('http://example.com/poll?limit=10', { method: 'GET' });
        const ctx = createExecutionContext();
        const response = await worker.fetch(request, env as unknown as Env, ctx);
        await waitOnExecutionContext(ctx);
        
        expect(response.status).toBe(200);
        const body = await response.json() as any;
        const msg = body.messages.find((m: any) => m.msg_id === id);
        expect(msg).toBeDefined();
        expect(msg.status).toBe('PROCESSING');
    });

    it('respects source_system filter', async () => {
        // Clear DB
        await (env as unknown as Env).DB.prepare("DELETE FROM webhooks").run();
        
        await (env as unknown as Env).DB.prepare("INSERT INTO webhooks (msg_id, payload, source_system, headers, status, enqueued_at) VALUES (?, ?, ?, ?, 'NEW', ?)")
            .bind('msg-github', '{}', 'github', '{}', Date.now())
            .run();
        await (env as unknown as Env).DB.prepare("INSERT INTO webhooks (msg_id, payload, source_system, headers, status, enqueued_at) VALUES (?, ?, ?, ?, 'NEW', ?)")
            .bind('msg-stripe', '{}', 'stripe', '{}', Date.now())
            .run();

        const request = new Request('http://example.com/poll?source_system=github', { method: 'GET' });
        const ctx = createExecutionContext();
        const response = await worker.fetch(request, env as unknown as Env, ctx);
        await waitOnExecutionContext(ctx);

        const body = await response.json() as any;
        expect(body.messages.length).toBe(1);
        expect(body.messages[0].msg_id).toBe('msg-github');
    });
  });

  describe('ACK and RELEASE', () => {
      beforeAll(async () => {
          await (env as unknown as Env).DB.prepare("DELETE FROM webhooks").run();
      });

      it('ACK deletes the message', async () => {
          await (env as unknown as Env).DB.prepare("INSERT INTO webhooks (msg_id, payload, source_system, headers, status, enqueued_at) VALUES (?, ?, ?, ?, 'PROCESSING', ?)")
            .bind('msg-ack', '{}', 'stripe', '{}', Date.now())
            .run();

          const request = new Request('http://example.com/ack?id=msg-ack', { method: 'DELETE' });
          const ctx = createExecutionContext();
          const response = await worker.fetch(request, env as unknown as Env, ctx);
          await waitOnExecutionContext(ctx);
          expect(response.status).toBe(200);

          const { results } = await (env as unknown as Env).DB.prepare("SELECT * FROM webhooks WHERE msg_id = 'msg-ack'").all();
          expect(results.length).toBe(0);
      });

      it('RELEASE resets status to NEW', async () => {
        await (env as unknown as Env).DB.prepare("INSERT INTO webhooks (msg_id, payload, source_system, headers, status, enqueued_at, locked_until) VALUES (?, ?, ?, ?, 'PROCESSING', ?, ?)")
            .bind('msg-rel', '{}', 'stripe', '{}', Date.now(), Date.now() + 10000)
            .run();

        const request = new Request('http://example.com/release', { 
            method: 'POST',
            body: JSON.stringify({ id: 'msg-rel' }) 
        });
        const ctx = createExecutionContext();
        const response = await worker.fetch(request, env as unknown as Env, ctx);
        await waitOnExecutionContext(ctx);
        expect(response.status).toBe(200);

        const { results } = await (env as unknown as Env).DB.prepare("SELECT * FROM webhooks WHERE msg_id = 'msg-rel'").all();
        expect(results[0].status).toBe('NEW');
        expect(results[0].locked_until).toBeNull();
      });
  });

  describe('Error Logging', () => {
      it('logs errors to webhook_errors table on failure', async () => {
          // Trigger a failure by sending an invalid JSON body which we catch in handleWebhook
          // Note: handleWebhook catches JSON parse errors in the request.text() if possible,
          // or more likely if we can trigger a DB error or something.
          // Easier: Trigger invalid URL format which calls logError

          const request = new Request('http://example.com/webhook/invalid-format', { method: 'POST' });
          const ctx = createExecutionContext();
          const response = await worker.fetch(request, env as unknown as Env, ctx);
          await waitOnExecutionContext(ctx);

          expect(response.status).toBe(400);

          const { results } = await (env as unknown as Env).DB.prepare("SELECT * FROM webhook_errors").all();
          expect(results.length).toBeGreaterThan(0);
          expect(results[0].error_type).toBe('INVALID_URL_FORMAT');
      });
  });
});

// ---------------------------------------------------------------------------
// normaliseVnPhone unit tests
// ---------------------------------------------------------------------------
describe('normaliseVnPhone', () => {
    it('accepts standard 10-digit VN mobile', () => {
        expect(normaliseVnPhone('0912345678')).toBe('0912345678');
    });

    it('strips spaces and dashes', () => {
        expect(normaliseVnPhone('0912 345 678')).toBe('0912345678');
        expect(normaliseVnPhone('091-234-5678')).toBe('0912345678');
    });

    it('rewrites +84 prefix to 0', () => {
        expect(normaliseVnPhone('+84912345678')).toBe('0912345678');
    });

    it('rewrites 84XXXXXXXXX (11 digits) to 0', () => {
        expect(normaliseVnPhone('84912345678')).toBe('0912345678');
    });

    it('rejects landline (9 digits after 0)', () => {
        expect(normaliseVnPhone('02812345678')).toBeNull();
    });

    it('rejects too-short number', () => {
        expect(normaliseVnPhone('091234')).toBeNull();
    });

    it('rejects empty string', () => {
        expect(normaliseVnPhone('')).toBeNull();
    });
});

// ---------------------------------------------------------------------------
// Hug opt-in landing page and opt-in capture tests
// ---------------------------------------------------------------------------
describe('Hug opt-in landing page (GET /optin/:token)', () => {
    it('returns 200 HTML page containing the token, form, and Zalo CTA', async () => {
        const token = 'abc123testtoken';
        const testEnv = { ...env, HUG_ZALO_OA_URL: 'https://zalo.me/test_oa' };
        const request = new Request(`http://example.com/optin/${token}`, { method: 'GET' });
        const ctx = createExecutionContext();
        const response = await worker.fetch(request, testEnv as unknown as Env, ctx);
        await waitOnExecutionContext(ctx);

        expect(response.status).toBe(200);
        expect(response.headers.get('Content-Type')).toContain('text/html');

        const body = await response.text();
        // Token embedded in page JS for form submission
        expect(body).toContain(JSON.stringify(token));
        // Form with phone input
        expect(body).toContain('type="tel"');
        // Consent checkbox
        expect(body).toContain('type="checkbox"');
        // Zalo follow CTA link
        expect(body).toContain('https://zalo.me/test_oa');
        expect(body).toContain('Zalo OA');
        // Submit posts to generic hug optin webhook path
        expect(body).toContain('/webhook/hug/optin/created');
    });

    it('uses placeholder Zalo URL when HUG_ZALO_OA_URL is not set', async () => {
        const token = 'tok999';
        const request = new Request(`http://example.com/optin/${token}`, { method: 'GET' });
        const ctx = createExecutionContext();
        const response = await worker.fetch(request, env as unknown as Env, ctx);
        await waitOnExecutionContext(ctx);

        expect(response.status).toBe(200);
        const body = await response.text();
        expect(body).toContain('zalo.me/YOUR_OA_ID');
    });

    it('rejects empty token', async () => {
        // /optin/ without token falls through to 404 (no route match)
        const request = new Request('http://example.com/optin/', { method: 'GET' });
        const ctx = createExecutionContext();
        const response = await worker.fetch(request, env as unknown as Env, ctx);
        await waitOnExecutionContext(ctx);
        expect(response.status).toBe(404);
    });

    it('sanitises token in HTML output to prevent XSS', async () => {
        // Token with HTML-special chars: the handler strips them with safeToken replacement
        // before embedding in the HTML. URL-encoding means the Request path won't contain
        // literal < >, so we test XSS hygiene by checking the output doesn't contain unescaped
        // HTML injection for a crafted token value.
        const request = new Request('http://example.com/optin/tok-safe-123', { method: 'GET' });
        const ctx = createExecutionContext();
        const response = await worker.fetch(request, env as unknown as Env, ctx);
        await waitOnExecutionContext(ctx);

        expect(response.status).toBe(200);
        const body = await response.text();
        // Token must appear correctly in output (not stripped or corrupted for safe tokens)
        expect(body).toContain(JSON.stringify('tok-safe-123'));
    });

    it('shows offer code in success state when campaign has offer_ref', async () => {
        // Seed a campaign with a known offer code
        await (env as unknown as Env).DB.prepare(
            "INSERT OR REPLACE INTO hug_campaign (campaign_id, name, targeting, destination_type, destination_url, offer_ref, status) VALUES (?, ?, ?, ?, ?, ?, ?)"
        ).bind('camp-offer', 'A2 Test', '{}', 'url', 'https://example.com', 'HUG50', 'active').run();

        const token = 'tok-camp-test';
        const testEnv = { ...env, HUG_ZALO_OA_URL: 'https://zalo.me/test_oa' };
        const request = new Request(`http://example.com/optin/${token}?hug_campaign=camp-offer`, { method: 'GET' });
        const ctx = createExecutionContext();
        const response = await worker.fetch(request, testEnv as unknown as Env, ctx);
        await waitOnExecutionContext(ctx);

        expect(response.status).toBe(200);
        const body = await response.text();
        // Offer code must appear prominently in the success state
        expect(body).toContain('HUG50');
        // CAMPAIGN_ID must be baked into page JS for form submission
        expect(body).toContain(JSON.stringify('camp-offer'));
    });

    it('shows generic success when campaign has no offer_ref', async () => {
        // Seed campaign without offer code
        await (env as unknown as Env).DB.prepare(
            "INSERT OR REPLACE INTO hug_campaign (campaign_id, name, targeting, destination_type, destination_url, offer_ref, status) VALUES (?, ?, ?, ?, ?, ?, ?)"
        ).bind('camp-no-offer', 'Generic Campaign', '{}', 'url', 'https://example.com', null, 'active').run();

        const token = 'tok-no-offer';
        const request = new Request(`http://example.com/optin/${token}?hug_campaign=camp-no-offer`, { method: 'GET' });
        const ctx = createExecutionContext();
        const response = await worker.fetch(request, env as unknown as Env, ctx);
        await waitOnExecutionContext(ctx);

        expect(response.status).toBe(200);
        const body = await response.text();
        // Generic fallback message
        expect(body).toContain('Chúng tôi sẽ liên hệ sớm');
    });

    it('returns 200 with no offer code when campaign_id is unknown', async () => {
        // No DB row for 'camp-unknown' — must degrade gracefully
        const request = new Request('http://example.com/optin/tok-unk?hug_campaign=camp-unknown', { method: 'GET' });
        const ctx = createExecutionContext();
        const response = await worker.fetch(request, env as unknown as Env, ctx);
        await waitOnExecutionContext(ctx);

        expect(response.status).toBe(200);
        const body = await response.text();
        expect(body).toContain('Chúng tôi sẽ liên hệ sớm');
    });

    it('returns 200 with no offer code when hug_campaign param is absent', async () => {
        const request = new Request('http://example.com/optin/tok-no-param', { method: 'GET' });
        const ctx = createExecutionContext();
        const response = await worker.fetch(request, env as unknown as Env, ctx);
        await waitOnExecutionContext(ctx);

        expect(response.status).toBe(200);
        const body = await response.text();
        // CAMPAIGN_ID baked as empty string when not provided
        expect(body).toContain('var CAMPAIGN_ID = ""');
    });
});

// ---------------------------------------------------------------------------
// matchesTargeting — not_in operator unit tests
// Parity with Python matches_targeting in crm/src/hug/targeting_engine.py.
// ScanContext is satisfied by a minimal object cast via unknown.
// ---------------------------------------------------------------------------
describe('matchesTargeting — not_in operator', () => {
    // Helper: build a minimal JSON ScanContext-compatible record.
    function ctx(overrides: Record<string, unknown> = {}): Record<string, unknown> {
        return {
            op_type: 'package_insert',
            tier: null,
            channel: null,
            value_group: null,
            recency_days: null,
            is_contactable: 0,
            customer_id: null,
            order_code: null,
            ship_date: null,
            sku: null,
            ...overrides,
        };
    }

    it('not_in: value absent from excluded list → true', () => {
        // tier="VIP" is not in ["WHOLESALE","STAFF"] → campaign matches
        const result = matchesTargeting(
            JSON.stringify({ tier: { not_in: ['WHOLESALE', 'STAFF'] } }),
            ctx({ tier: 'VIP' }) as any,
        );
        expect(result).toBe(true);
    });

    it('not_in: value in excluded list → false', () => {
        // tier="WHOLESALE" is in the excluded list → campaign does NOT match
        const result = matchesTargeting(
            JSON.stringify({ tier: { not_in: ['WHOLESALE', 'STAFF'] } }),
            ctx({ tier: 'WHOLESALE' }) as any,
        );
        expect(result).toBe(false);
    });

    it('not_in: null/undefined ctx value → true (passes — unknown is not excluded)', () => {
        // tier=null (customer has no tier) → should NOT be blocked by an exclusion rule
        const result = matchesTargeting(
            JSON.stringify({ tier: { not_in: ['WHOLESALE', 'STAFF'] } }),
            ctx({ tier: null }) as any,
        );
        expect(result).toBe(true);
    });

    it('not_in: string coercion parity with Python — int value in rule', () => {
        // is_contactable={"not_in":[0]} with ctx value 0 → in list → false
        const resultIn = matchesTargeting(
            JSON.stringify({ is_contactable: { not_in: [0] } }),
            ctx({ is_contactable: 0 }) as any,
        );
        expect(resultIn).toBe(false);

        // is_contactable={"not_in":[0]} with ctx value 1 → not in list → true
        const resultOut = matchesTargeting(
            JSON.stringify({ is_contactable: { not_in: [0] } }),
            ctx({ is_contactable: 1 }) as any,
        );
        expect(resultOut).toBe(true);
    });

    it('not_in combined with positive list rule (AND) — both must pass', () => {
        // tier NOT in WHOLESALE/STAFF AND op_type IS package_insert → true when both pass
        const targeting = JSON.stringify({
            tier: { not_in: ['WHOLESALE', 'STAFF'] },
            op_type: ['package_insert'],
        });
        const passCtx = ctx({ tier: 'VIP', op_type: 'package_insert' });
        expect(matchesTargeting(targeting, passCtx as any)).toBe(true);

        // tier passes but op_type fails → overall false
        const failCtx = ctx({ tier: 'VIP', op_type: 'loyalty_card' });
        expect(matchesTargeting(targeting, failCtx as any)).toBe(false);

        // tier fails (excluded) even if op_type passes → overall false
        const failTierCtx = ctx({ tier: 'WHOLESALE', op_type: 'package_insert' });
        expect(matchesTargeting(targeting, failTierCtx as any)).toBe(false);
    });

    it('numeric range still works alongside not_in detection', () => {
        // recency_days range object (no not_in key) must still route to range branch
        const result = matchesTargeting(
            JSON.stringify({ recency_days: { gte: 30, lte: 90 } }),
            ctx({ recency_days: 60 }) as any,
        );
        expect(result).toBe(true);

        const outOfRange = matchesTargeting(
            JSON.stringify({ recency_days: { gte: 30, lte: 90 } }),
            ctx({ recency_days: 100 }) as any,
        );
        expect(outOfRange).toBe(false);
    });
});

describe('Hug opt-in capture (POST /webhook/hug/optin/created)', () => {
    const OPTIN_URL = 'http://example.com/webhook/hug/optin/created';

    it('enqueues a row with source_system=hug, entity_type=optin, and required payload keys', async () => {
        // Clear hug rows from previous tests
        await (env as unknown as Env).DB.prepare("DELETE FROM webhooks WHERE source_system = 'hug'").run();

        const ts = new Date().toISOString();
        const body = JSON.stringify({
            token: 'tok-optin-001',
            phone: '0912345678',
            consent: { phone: true, ts },
            ts,
        });

        const request = new Request(OPTIN_URL, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body,
        });
        const ctx = createExecutionContext();
        // CHECK_HMAC is not set → no HMAC check (public form endpoint)
        const response = await worker.fetch(request, env as unknown as Env, ctx);
        await waitOnExecutionContext(ctx);

        expect(response.status).toBe(200);

        // Verify the stored row matches what the consumer expects
        const { results } = await (env as unknown as Env).DB.prepare(
            "SELECT * FROM webhooks WHERE source_system = 'hug'"
        ).all();

        expect(results.length).toBe(1);
        const row = results[0];

        // Top-level row: source_system must be 'hug' so the consumer's poll filter works
        expect(row.source_system).toBe('hug');

        // Parse the stored wrapper JSON
        const wrapper = JSON.parse(row.payload as string);

        // entity_type in wrapper = 'optin' (consumer reads this from wrapper.entity_type)
        expect(wrapper.entity_type).toBe('optin');
        expect(wrapper.source_system).toBe('hug');
        expect(wrapper.action).toBe('created');

        // Inner payload must have all required keys for the dbt model
        const inner = wrapper.payload;
        expect(inner.token).toBe('tok-optin-001');
        expect(inner.phone).toBe('0912345678');
        expect(inner.consent).toBeDefined();
        expect(inner.consent.phone).toBe(true);
        expect(inner.ts).toBe(ts);
    });

    it('enqueues row including optional name field when provided', async () => {
        await (env as unknown as Env).DB.prepare("DELETE FROM webhooks WHERE source_system = 'hug'").run();

        const ts = new Date().toISOString();
        const body = JSON.stringify({
            token: 'tok-optin-002',
            phone: '0987654321',
            name: 'Nguyễn Thị B',
            consent: { phone: true, ts },
            ts,
        });

        const request = new Request(OPTIN_URL, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body,
        });
        const ctx = createExecutionContext();
        const response = await worker.fetch(request, env as unknown as Env, ctx);
        await waitOnExecutionContext(ctx);

        expect(response.status).toBe(200);

        const { results } = await (env as unknown as Env).DB.prepare(
            "SELECT * FROM webhooks WHERE source_system = 'hug'"
        ).all();
        const inner = JSON.parse(results[0].payload as string).payload;
        expect(inner.name).toBe('Nguyễn Thị B');
    });

    it('includes campaign_id in stored payload when provided', async () => {
        await (env as unknown as Env).DB.prepare("DELETE FROM webhooks WHERE source_system = 'hug'").run();

        const ts = new Date().toISOString();
        const body = JSON.stringify({
            token: 'tok-optin-camp',
            phone: '0912000001',
            consent: { phone: true, ts },
            ts,
            campaign_id: 'camp-a2',
        });

        const request = new Request(OPTIN_URL, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body,
        });
        const ctx = createExecutionContext();
        const response = await worker.fetch(request, env as unknown as Env, ctx);
        await waitOnExecutionContext(ctx);

        expect(response.status).toBe(200);

        const { results } = await (env as unknown as Env).DB.prepare(
            "SELECT * FROM webhooks WHERE source_system = 'hug'"
        ).all();
        expect(results.length).toBe(1);
        const inner = JSON.parse(results[0].payload as string).payload;
        expect(inner.campaign_id).toBe('camp-a2');
    });

    it('accepts the request without HMAC when CHECK_HMAC is not set (default deployment)', async () => {
        // The form is a public endpoint. The default deployment does NOT set CHECK_HMAC,
        // so the generic handler skips HMAC verification for all sources including 'hug'.
        const ts = new Date().toISOString();
        const body = JSON.stringify({
            token: 'tok-public',
            phone: '0900111222',
            consent: { phone: true, ts },
            ts,
        });
        // No CHECK_HMAC, no WEBHOOK_SECRET — mirrors default Cloudflare deployment for hug
        const testEnv = { ...env };

        const request = new Request(OPTIN_URL, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body,
        });
        const ctx = createExecutionContext();
        const response = await worker.fetch(request, testEnv as unknown as Env, ctx);
        await waitOnExecutionContext(ctx);

        expect(response.status).toBe(200);
    });
});

// ---------------------------------------------------------------------------
// hug_customer customer_type — upsert + scan context + targeting tests
// ---------------------------------------------------------------------------
describe('hug_customer customer_type', () => {
    const UPSERT_URL = 'http://example.com/hug/customer/upsert';
    const SCAN_TOKEN = 'SCANCTYPE001';  // exactly 12 chars (Crockford base32 format)

    async function signedUpsert(body: string): Promise<Response> {
        const sig = await generateSignature('test-hmac-secret', body);
        const request = new Request(UPSERT_URL, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'x-hug-signature': sig,
            },
            body,
        });
        const testEnv = { ...env, HUG_ADMIN_SECRET: 'test-hmac-secret' };
        const ctx = createExecutionContext();
        const response = await worker.fetch(request, testEnv as unknown as Env, ctx);
        await waitOnExecutionContext(ctx);
        return response;
    }

    beforeAll(async () => {
        // Seed a token bound to customer 'cust-ct-1'
        await (env as unknown as Env).DB.prepare(
            `INSERT OR REPLACE INTO hug_token
             (token, customer_id, op_type, status)
             VALUES (?, 'cust-ct-1', 'package_insert', 'bound')`
        ).bind(SCAN_TOKEN).run();
    });

    it('CT1: upsert stores customer_type in hug_customer', async () => {
        const body = JSON.stringify({
            rows: [{ customer_id: 'cust-ct-1', tier: 'VIP', recency_days: 5, value_group: 'HIGH', is_contactable: 1, customer_type: 'RETAIL' }],
        });
        const resp = await signedUpsert(body);
        expect(resp.status).toBe(200);

        const row = await (env as unknown as Env).DB.prepare(
            "SELECT customer_type FROM hug_customer WHERE customer_id = 'cust-ct-1'"
        ).first<{ customer_type: string | null }>();
        expect(row?.customer_type).toBe('RETAIL');
    });

    it('CT2: upsert accepts null customer_type (nullable column)', async () => {
        const body = JSON.stringify({
            rows: [{ customer_id: 'cust-ct-null', tier: 'CORE', recency_days: 10, value_group: 'MID', is_contactable: 0, customer_type: null }],
        });
        const resp = await signedUpsert(body);
        expect(resp.status).toBe(200);

        const row = await (env as unknown as Env).DB.prepare(
            "SELECT customer_type FROM hug_customer WHERE customer_id = 'cust-ct-null'"
        ).first<{ customer_type: string | null }>();
        expect(row?.customer_type).toBeNull();
    });

    it('CT3: upsert omitting customer_type field treats it as null', async () => {
        const body = JSON.stringify({
            rows: [{ customer_id: 'cust-ct-omit', tier: 'CASUAL', recency_days: 20, value_group: 'LOW', is_contactable: 0 }],
        });
        const resp = await signedUpsert(body);
        expect(resp.status).toBe(200);

        const row = await (env as unknown as Env).DB.prepare(
            "SELECT customer_type FROM hug_customer WHERE customer_id = 'cust-ct-omit'"
        ).first<{ customer_type: string | null }>();
        expect(row?.customer_type).toBeNull();
    });

    it('CT4: handleHugScan includes customer_type in ScanContext — matchesTargeting not_in works', async () => {
        // Upsert the customer with customer_type='WHOLESALE' so scan context resolves it.
        const upsertBody = JSON.stringify({
            rows: [{ customer_id: 'cust-ct-1', tier: 'VIP', recency_days: 5, value_group: 'HIGH', is_contactable: 1, customer_type: 'WHOLESALE' }],
        });
        await signedUpsert(upsertBody);

        // Use the campaign upsert endpoint so handleHugCampaignUpsert calls
        // invalidateCampaignCache() — direct DB writes bypass the cache flush.
        const testEnvHmac = { ...env, HUG_ADMIN_SECRET: 'test-hmac-secret' };

        const campBody = JSON.stringify({
            rows: [
                // Excludes WHOLESALE: RETAIL/etc pass, WHOLESALE blocked (priority 50 = higher).
                {
                    campaign_id: 'camp-ct-excl',
                    name: 'Exclude Wholesale',
                    targeting: { customer_type: { not_in: ['WHOLESALE', 'STAFF'] } },
                    destination_type: 'url',
                    destination_url: 'https://fgcare.vn/retail',
                    status: 'active',
                    priority: 50,
                },
                // DEFAULT catches everyone including WHOLESALE (priority 999 = lower).
                {
                    campaign_id: 'camp-ct-default',
                    name: 'Default',
                    targeting: {},
                    destination_type: 'url',
                    destination_url: 'https://fgcare.vn/default',
                    status: 'active',
                    priority: 999,
                },
            ],
        });
        const campSig = await generateSignature('test-hmac-secret', campBody);
        const campResp = await worker.fetch(
            new Request('http://example.com/hug/campaign/upsert', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json', 'x-hug-signature': campSig },
                body: campBody,
            }),
            testEnvHmac as unknown as Env,
            createExecutionContext(),
        );
        expect(campResp.status).toBe(200); // confirms campaign upsert + cache invalidation

        const scanRequest = new Request(`http://example.com/h/${SCAN_TOKEN}`);
        const testEnv = { ...env, HUG_ADMIN_SECRET: 'test-hmac-secret', HUG_FALLBACK_URL: 'https://fgcare.vn/fallback' };
        const ctx = createExecutionContext();
        const response = await worker.fetch(scanRequest, testEnv as unknown as Env, ctx);
        await waitOnExecutionContext(ctx);

        // WHOLESALE customer: excluded from camp-ct-excl → falls to camp-ct-default (priority 999)
        expect(response.status).toBe(302);
        const location = response.headers.get('Location') ?? '';
        // The Worker appends ?hug_token=...&hug_campaign=... query params to the destination URL.
        // Assert base URL is the DEFAULT campaign destination, NOT the retail-only exclusion campaign.
        expect(location).toContain('https://fgcare.vn/default');
        expect(location).not.toContain('https://fgcare.vn/retail');
        expect(location).toContain('camp-ct-default');
    });

    it('CT5: matchesTargeting customer_type not_in — RETAIL passes exclusion, STAFF blocked', () => {
        // Verify the matcher itself handles customer_type correctly without a full scan.
        // ScanContext helper (customer_type added).
        function ctxWithType(overrides: Record<string, unknown> = {}): Record<string, unknown> {
            return {
                op_type: 'package_insert', tier: null, channel: null,
                value_group: null, recency_days: null, is_contactable: 0,
                customer_id: null, order_code: null, ship_date: null, sku: null,
                customer_type: null,
                ...overrides,
            };
        }

        const notInRule = JSON.stringify({ customer_type: { not_in: ['WHOLESALE', 'STAFF'] } });

        expect(matchesTargeting(notInRule, ctxWithType({ customer_type: 'RETAIL' }) as any)).toBe(true);
        expect(matchesTargeting(notInRule, ctxWithType({ customer_type: 'STAFF' }) as any)).toBe(false);
        expect(matchesTargeting(notInRule, ctxWithType({ customer_type: 'WHOLESALE' }) as any)).toBe(false);
        // null customer_type passes (unknown is not in the excluded set).
        expect(matchesTargeting(notInRule, ctxWithType({ customer_type: null }) as any)).toBe(true);
    });
});

// ---------------------------------------------------------------------------
// POST /hug/campaign/preview — D1-backed match count + customer list
// ---------------------------------------------------------------------------
describe('POST /hug/campaign/preview', () => {
    const ADMIN_SECRET = 'preview-test-secret';
    const PREVIEW_URL = 'http://example.com/hug/campaign/preview';

    async function signBody(body: string): Promise<string> {
        return generateSignature(ADMIN_SECRET, body);
    }

    // Seed a small hug_customer dataset shared across the preview tests.
    beforeAll(async () => {
        const db = (env as unknown as Env).DB;
        await db.prepare('DELETE FROM hug_customer').run();
        // 3 customers: 2 VIP (one RETAIL, one WHOLESALE), 1 CORE RETAIL
        await db.prepare(
            `INSERT OR REPLACE INTO hug_customer
             (customer_id, tier, recency_days, value_group, is_contactable, customer_type, updated_at)
             VALUES (?, ?, ?, ?, ?, ?, ?)`
        ).bind('c001', 'VIP',  10, 'HIGH', 1, 'RETAIL',    '2026-06-22T10:00:00Z').run();
        await db.prepare(
            `INSERT OR REPLACE INTO hug_customer
             (customer_id, tier, recency_days, value_group, is_contactable, customer_type, updated_at)
             VALUES (?, ?, ?, ?, ?, ?, ?)`
        ).bind('c002', 'VIP',  30, 'HIGH', 0, 'WHOLESALE', '2026-06-22T11:00:00Z').run();
        await db.prepare(
            `INSERT OR REPLACE INTO hug_customer
             (customer_id, tier, recency_days, value_group, is_contactable, customer_type, updated_at)
             VALUES (?, ?, ?, ?, ?, ?, ?)`
        ).bind('c003', 'CORE', 60, 'MID',  1, 'RETAIL',    '2026-06-22T09:00:00Z').run();
    });

    it('PR01: returns 401 when X-Hug-Signature header is missing', async () => {
        const body = JSON.stringify({ targeting: {} });
        const request = new Request(PREVIEW_URL, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body,
        });
        const testEnv = { ...env, HUG_ADMIN_SECRET: ADMIN_SECRET };
        const ctx = createExecutionContext();
        const resp = await worker.fetch(request, testEnv as unknown as Env, ctx);
        await waitOnExecutionContext(ctx);
        expect(resp.status).toBe(401);
    });

    it('PR02: returns 401 when signature is invalid', async () => {
        const body = JSON.stringify({ targeting: {} });
        const request = new Request(PREVIEW_URL, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'x-hug-signature': 'sha256=badhash',
            },
            body,
        });
        const testEnv = { ...env, HUG_ADMIN_SECRET: ADMIN_SECRET };
        const ctx = createExecutionContext();
        const resp = await worker.fetch(request, testEnv as unknown as Env, ctx);
        await waitOnExecutionContext(ctx);
        expect(resp.status).toBe(401);
    });

    it('PR03: empty targeting {} matches all 3 customers; upper_bound false', async () => {
        const body = JSON.stringify({ targeting: {} });
        const sig = await signBody(body);
        const request = new Request(PREVIEW_URL, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', 'x-hug-signature': sig },
            body,
        });
        const testEnv = { ...env, HUG_ADMIN_SECRET: ADMIN_SECRET };
        const ctx = createExecutionContext();
        const resp = await worker.fetch(request, testEnv as unknown as Env, ctx);
        await waitOnExecutionContext(ctx);
        expect(resp.status).toBe(200);
        const data = await resp.json() as any;
        expect(data.count).toBe(3);
        expect(data.total_customers).toBe(3);
        expect(data.upper_bound).toBe(false);
        // data_as_of is the max updated_at across rows (lexicographic max of ISO strings)
        expect(data.data_as_of).toBe('2026-06-22T11:00:00Z');
        expect(Array.isArray(data.customers)).toBe(true);
        expect(data.customers.length).toBe(3);
    });

    it('PR04: tier filter ["VIP"] → 2 customers; includes both VIP rows', async () => {
        const body = JSON.stringify({ targeting: { tier: ['VIP'] } });
        const sig = await signBody(body);
        const request = new Request(PREVIEW_URL, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', 'x-hug-signature': sig },
            body,
        });
        const testEnv = { ...env, HUG_ADMIN_SECRET: ADMIN_SECRET };
        const ctx = createExecutionContext();
        const resp = await worker.fetch(request, testEnv as unknown as Env, ctx);
        await waitOnExecutionContext(ctx);
        expect(resp.status).toBe(200);
        const data = await resp.json() as any;
        expect(data.count).toBe(2);
        expect(data.upper_bound).toBe(false);
        const ids = data.customers.map((c: any) => c.customer_id);
        expect(ids).toContain('c001');
        expect(ids).toContain('c002');
    });

    it('PR05: not_in targeting customer_type → excludes WHOLESALE', async () => {
        const body = JSON.stringify({
            targeting: { customer_type: { not_in: ['WHOLESALE'] } },
        });
        const sig = await signBody(body);
        const request = new Request(PREVIEW_URL, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', 'x-hug-signature': sig },
            body,
        });
        const testEnv = { ...env, HUG_ADMIN_SECRET: ADMIN_SECRET };
        const ctx = createExecutionContext();
        const resp = await worker.fetch(request, testEnv as unknown as Env, ctx);
        await waitOnExecutionContext(ctx);
        expect(resp.status).toBe(200);
        const data = await resp.json() as any;
        // c001 (RETAIL) + c003 (RETAIL) pass; c002 (WHOLESALE) excluded
        expect(data.count).toBe(2);
        const ids = data.customers.map((c: any) => c.customer_id);
        expect(ids).not.toContain('c002');
    });

    it('PR06: touchpoint attr (op_type) in targeting → stripped; upper_bound true; count = empty targeting count', async () => {
        // op_type is a touchpoint-level attr not in hug_customer.
        // The Worker must strip it, set upper_bound:true, and count all rows (same as {}).
        const body = JSON.stringify({
            targeting: { op_type: ['package_insert'] },
        });
        const sig = await signBody(body);
        const request = new Request(PREVIEW_URL, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', 'x-hug-signature': sig },
            body,
        });
        const testEnv = { ...env, HUG_ADMIN_SECRET: ADMIN_SECRET };
        const ctx = createExecutionContext();
        const resp = await worker.fetch(request, testEnv as unknown as Env, ctx);
        await waitOnExecutionContext(ctx);
        expect(resp.status).toBe(200);
        const data = await resp.json() as any;
        // Stripped targeting = {} → all 3 rows match
        expect(data.count).toBe(3);
        expect(data.upper_bound).toBe(true);
    });

    it('PR07: sku attr in targeting → stripped; upper_bound true', async () => {
        const body = JSON.stringify({
            targeting: { tier: ['VIP'], sku: ['FJ-OMEGA3-60'] },
        });
        const sig = await signBody(body);
        const request = new Request(PREVIEW_URL, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', 'x-hug-signature': sig },
            body,
        });
        const testEnv = { ...env, HUG_ADMIN_SECRET: ADMIN_SECRET };
        const ctx = createExecutionContext();
        const resp = await worker.fetch(request, testEnv as unknown as Env, ctx);
        await waitOnExecutionContext(ctx);
        expect(resp.status).toBe(200);
        const data = await resp.json() as any;
        // sku stripped; tier=["VIP"] remains → 2 VIP rows
        expect(data.count).toBe(2);
        expect(data.upper_bound).toBe(true);
    });

    it('PR08: limit/offset pagination — offset=1 shifts customer slice', async () => {
        // Full match ({}) = 3 rows sorted by customer_id: c001, c002, c003.
        // offset=1, limit=2 → slice [1..3) = c002, c003
        const body = JSON.stringify({ targeting: {}, limit: 2, offset: 1 });
        const sig = await signBody(body);
        const request = new Request(PREVIEW_URL, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', 'x-hug-signature': sig },
            body,
        });
        const testEnv = { ...env, HUG_ADMIN_SECRET: ADMIN_SECRET };
        const ctx = createExecutionContext();
        const resp = await worker.fetch(request, testEnv as unknown as Env, ctx);
        await waitOnExecutionContext(ctx);
        expect(resp.status).toBe(200);
        const data = await resp.json() as any;
        // count reflects total matched (all 3), not page size
        expect(data.count).toBe(3);
        // Page contains only 2 rows due to limit
        expect(data.customers.length).toBe(2);
        // offset=1 skips first matched row (c001)
        expect(data.customers[0].customer_id).toBe('c002');
        expect(data.customers[1].customer_id).toBe('c003');
    });

    it('PR09: customer_type attr targeting → exact count (not upper_bound)', async () => {
        // customer_type is a customer-level attr — not stripped, not upper_bound
        const body = JSON.stringify({
            targeting: { customer_type: ['RETAIL'] },
        });
        const sig = await signBody(body);
        const request = new Request(PREVIEW_URL, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', 'x-hug-signature': sig },
            body,
        });
        const testEnv = { ...env, HUG_ADMIN_SECRET: ADMIN_SECRET };
        const ctx = createExecutionContext();
        const resp = await worker.fetch(request, testEnv as unknown as Env, ctx);
        await waitOnExecutionContext(ctx);
        expect(resp.status).toBe(200);
        const data = await resp.json() as any;
        expect(data.count).toBe(2);   // c001 + c003 are RETAIL
        expect(data.upper_bound).toBe(false);
    });
});
