export interface Env {
    DB: D1Database;
    WEBHOOK_SECRET?: string;
    HMAC_HEADER_NAME?: string;
    CHECK_HMAC?: string;
    // Hug Dynamic Touchpoint Platform
    // Set via: wrangler secret put HUG_ADMIN_SECRET
    HUG_ADMIN_SECRET?: string;
    // Fallback redirect URL when token not found or no campaign matches.
    // Set via: wrangler secret put HUG_FALLBACK_URL  (or as a plain var in wrangler.toml)
    HUG_FALLBACK_URL?: string;
    // Zalo OA follow link displayed on the opt-in landing page.
    // Set via: wrangler secret put HUG_ZALO_OA_URL  (or as a var in wrangler.toml for non-secret values)
    HUG_ZALO_OA_URL?: string;
    [key: string]: any; // Allow dynamic access for other secrets
}

// Helper to verify HMAC signature
export const verifySignature = async (secret: string, signature: string, body: string, encoding: 'hex' | 'base64'): Promise<boolean> => {
    const encoder = new TextEncoder();
    const key = await crypto.subtle.importKey(
        "raw",
        encoder.encode(secret),
        { name: "HMAC", hash: "SHA-256" },
        false,
        ["verify"]
    );

    let signatureBytes: Uint8Array;

    if (encoding === 'hex') {
        // Convert hex signature to Uint8Array
        const match = signature.match(/.{1,2}/g);
        if (!match) return false;
        signatureBytes = new Uint8Array(match.map((byte) => parseInt(byte, 16)));
    } else {
        // Convert base64 signature to Uint8Array
        try {
            const binaryString = atob(signature);
            signatureBytes = new Uint8Array(binaryString.length);
            for (let i = 0; i < binaryString.length; i++) {
                signatureBytes[i] = binaryString.charCodeAt(i);
            }
        } catch (e) {
            return false;
        }
    }

    return crypto.subtle.verify(
        "HMAC",
        key,
        signatureBytes,
        encoder.encode(body)
    );
};

/**
 * Normalize any human or scanner input form into a bare 12-char token string.
 *
 * Accepted input forms:
 *   - Bare token:              "7K2NQ9XRWAB4"
 *   - Grouped code (dashes):   "7K2N-Q9XR-WAB4"
 *   - Printed human code:      "HUG-7K2N-Q9XR-WAB4"  (also lowercase / extra spaces)
 *   - Full scan URL:           "https://hug.fjp.vn/h/7K2NQ9XRWAB4"
 *   - URL-encoded form:        "HUG%207K2N%20Q9XR%20WAB4"  (scanner may percent-encode)
 *   - Underscore or dot separators: "7K2N_Q9XR_WAB4", "7K2N.Q9XR.WAB4"
 *
 * Separator set is broader than the printed-code spec so that any separator a
 * typist might reach for (-, _, ., space) works without training.
 *
 * This function does NOT validate — the caller should check length === 12
 * and redirect to fallback immediately when the result does not match.
 */
export function normalizeToken(raw: string): string {
    // Percent-decode first so "%20"-encoded spaces and encoded characters are
    // handled before trimming. Malformed sequences (invalid %) fall back to raw.
    let s: string;
    try {
        s = decodeURIComponent(raw);
    } catch {
        s = raw;
    }

    s = s.trim().toUpperCase();

    // If the input looks like a URL (contains "://"), extract the last path
    // segment, dropping query string and fragment first.
    // e.g. "HTTPS://HUG.FJP.VN/H/7K2NQ9XRWAB4?foo=1#bar" → "7K2NQ9XRWAB4"
    if (s.includes('://')) {
        const withoutQuery = s.split('?')[0].split('#')[0];
        s = withoutQuery.replace(/\/+$/, '').split('/').pop() ?? '';
    }

    // Strip all separator characters: dashes, underscores, dots, and any
    // whitespace. Covers: printed sticker (HUG-XXXX-XXXX-XXXX), manually
    // typed codes using _, . or spaces, and stray whitespace from scanners.
    s = s.replace(/[-_.\s]/g, '');

    // Strip a "HUG" prefix only when the result is exactly 15 chars.
    // 15 = len("HUG") + TOKEN_LEN(12) — the exact shape of the printed human_code
    // after separators are removed.  A genuine bare 12-char token that happens to
    // start with "HUG" (e.g. HUG2345678AB) is already 12 chars at this point
    // and must NOT be stripped — the length guard prevents corruption.
    if (s.length === 15 && s.startsWith('HUG')) {
        s = s.slice(3);
    }

    return s;
}

// Helper to log errors to D1
export async function logError(env: Env, type: string, message: string, stack?: string, webhookId?: string, payload?: string) {
    try {
        await env.DB.prepare(
            "INSERT INTO webhook_errors (webhook_id, error_type, error_message, stack_trace, payload) VALUES (?, ?, ?, ?, ?)"
        )
            .bind(webhookId || null, type, message, stack || null, payload || null)
            .run();
    } catch (e) {
        // Fallback: log to console if DB logging fails
        console.error("Failed to log error to DB:", e);
    }
}
