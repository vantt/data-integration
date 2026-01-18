import { describe, it, expect, beforeAll } from 'vitest';
import { verifySignature } from './utils';

describe('verifySignature', () => {
    const secret = 'my_secret_key';
    const body = 'hello world';
    let expectedHex: string;
    let expectedBase64: string;

    beforeAll(async () => {
        const encoder = new TextEncoder();
        const key = await crypto.subtle.importKey(
            "raw",
            encoder.encode(secret),
            { name: "HMAC", hash: "SHA-256" },
            false,
            ["sign"]
        );
        const signatureBuffer = await crypto.subtle.sign(
            "HMAC",
            key,
            encoder.encode(body)
        );
        
        const signatureArray = Array.from(new Uint8Array(signatureBuffer));
        expectedHex = signatureArray.map(b => b.toString(16).padStart(2, '0')).join('');
        expectedBase64 = btoa(String.fromCharCode(...signatureArray));
    });

    it('validates correct hex signature', async () => {
        const isValid = await verifySignature(secret, expectedHex, body, 'hex');
        expect(isValid).toBe(true);
    });

    it('rejects incorrect hex signature', async () => {
        const isValid = await verifySignature(secret, expectedHex.replace(/[a-f0-9]/, 'x'), body, 'hex'); // ensure we change a char
        // Note: 'x' is invalid hex, so it might fail parsing or fail verify. Both returns false.
        expect(isValid).toBe(false);
    });

    it('validates correct base64 signature', async () => {
        const isValid = await verifySignature(secret, expectedBase64, body, 'base64');
        expect(isValid).toBe(true);
    });

    it('rejects incorrect base64 signature', async () => {
        const isValid = await verifySignature(secret, 'not_valid_base64', body, 'base64');
        expect(isValid).toBe(false);
    });

    it('rejects base64 signature when expecting hex', async () => {
        const isValid = await verifySignature(secret, expectedBase64, body, 'hex');
        expect(isValid).toBe(false);
    });

     it('rejects hex signature when expecting base64', async () => {
        const isValid = await verifySignature(secret, expectedHex, body, 'base64');
        // Hex string is valid base64, but decodes to wrong bytes
        expect(isValid).toBe(false);
    });
});
