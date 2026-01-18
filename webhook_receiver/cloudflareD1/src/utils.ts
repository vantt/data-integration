export interface Env {
    DB: D1Database;
    WEBHOOK_SECRET?: string;
    HMAC_HEADER_NAME?: string;
    CHECK_HMAC?: string;
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
