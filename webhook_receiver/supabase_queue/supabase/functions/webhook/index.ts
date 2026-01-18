/* To invoke locally:

  1. Run `supabase start` (see: https://supabase.com/docs/reference/cli/supabase-start)
  2. Make an HTTP request:

  curl -i --location --request POST 'http://127.0.0.1:54321/functions/v1/webhook/sapo/order/create' \
    --header 'Authorization: Bearer <anon_key>' \
    --header 'Content-Type: application/json' \
    --header 'x-hub-signature-256: <signature>' \
    --data '{"name":"Functions"}'
*/

// Setup type definitions for built-in Supabase Runtime APIs
import "jsr:@supabase/functions-js/edge-runtime.d.ts"
import { createClient } from 'jsr:@supabase/supabase-js@2'

// Helper to verify HMAC signature
const verifySignature = async (secret: string, signature: string, body: string): Promise<boolean> => {
  const encoder = new TextEncoder();
  const key = await crypto.subtle.importKey(
    "raw",
    encoder.encode(secret),
    { name: "HMAC", hash: "SHA-256" },
    false,
    ["verify"]
  );

  // Convert hex signature to Uint8Array
  const signatureBytes = new Uint8Array(
    signature.match(/.{1,2}/g)!.map((byte) => parseInt(byte, 16))
  );

  return crypto.subtle.verify(
    "HMAC",
    key,
    signatureBytes,
    encoder.encode(body)
  );
};

Deno.serve(async (req: Request) => {
  try {
    // 1. Validate Method
    if (req.method !== 'POST') {
      return new Response('Method Not Allowed', { status: 405 });
    }

    // 2. HMAC Verification (Optional)
    const isHmacEnabled = Deno.env.get('HMAC_VERIFICATION_ENABLED') === 'true';

    // We need to read the body as text first to verify signature, then parse as JSON
    // Note: req.json() consumes the body, so we use req.text() then JSON.parse()
    const rawBody = await req.text();

    if (isHmacEnabled) {
      const secret = Deno.env.get('WEBHOOK_SECRET');
      if (!secret) {
        throw new Error('HMAC verification enabled but WEBHOOK_SECRET is not set');
      }

      const headerName = Deno.env.get('HMAC_HEADER_NAME') ?? 'x-hub-signature-256';
      const signature = req.headers.get(headerName);

      if (!signature) {
        throw new Error(`Missing signature header: ${headerName}`);
      }

      // Some providers prefix signature with "sha256=", remove it if present
      const cleanSignature = signature.replace(/^sha256=/, '');

      const isValid = await verifySignature(secret, cleanSignature, rawBody);
      if (!isValid) {
        return new Response(JSON.stringify({ error: 'Invalid signature' }), {
          status: 401,
          headers: { 'Content-Type': 'application/json' }
        });
      }
    }

    // 3. Initialize Supabase
    const supabaseClient = createClient(
      Deno.env.get('SUPABASE_URL') ?? '',
      Deno.env.get('SUPABASE_SERVICE_ROLE_KEY') ?? Deno.env.get('SUPABASE_ANON_KEY') ?? '',
    );

    // 4. Extract path parameters
    // Expected pattern: .../webhook/<source_system>/<entity_type>/<action>
    const url = new URL(req.url);
    const path = url.pathname;

    // Check for the pattern. We look for 'webhook/' followed by 3 segments.
    // This regex matches: /.../webhook/sapo/order/create
    const match = path.match(/\/webhook\/([^/]+)\/([^/]+)\/(.+)/);

    if (!match) {
      throw new Error(`Invalid URL format: ${path}. Expected format: .../webhook/<source_system>/<entity_type>/<action>`);
    }

    const [, source_system, entity_type, action] = match;

    // 5. Parse payload
    let body;
    try {
      body = JSON.parse(rawBody);
    } catch {
      throw new Error("Invalid JSON payload");
    }

    const payload = {
      entity_type,
      action,
      source_system,
      payload: body,
      received_at: new Date().toISOString()
    };

    console.log(`Received webhook for ${source_system}.${entity_type}.${action}`);

    // 6. Send to queue
    const { error } = await supabaseClient.rpc('queue_webhook', { webhook_data: payload });

    if (error) {
      console.error('Supabase RPC Error:', error);
      throw error;
    }

    return new Response(JSON.stringify({ status: 'queued', id: crypto.randomUUID() }), {
      status: 200,
      headers: {
        'Content-Type': 'application/json',
        'Access-Control-Allow-Origin': '*'
      }
    });

  }
  catch (error) {
    console.error('Webhook Error:', error);
    const err = error instanceof Error ? error.message : String(error);
    return new Response(JSON.stringify({ error: err }), {
      status: 400,
      headers: {
        'Content-Type': 'application/json',
        'Access-Control-Allow-Origin': '*'
      }
    });
  }
})