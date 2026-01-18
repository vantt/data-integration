import { env, createExecutionContext, waitOnExecutionContext } from 'cloudflare:test';
import { describe, it, expect, beforeAll } from 'vitest';
import worker, { Env } from './index';

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

describe('Webhook Receiver Worker', () => {
  const SECRET = 'test-secret';

  beforeAll(async () => {
    // Apply schema
    const statements = SCHEMA_SQL
        .split(';')
        .map((s: string) => s.trim())
        .filter((s: string) => s.length > 0);
        
    for (const statement of statements) {
        await (env as unknown as Env).DB.prepare(statement).run();
    }
  });

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
