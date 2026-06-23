import { describe, it, expect, beforeAll } from 'vitest';
import { verifySignature, normalizeToken } from './utils';

describe('normalizeToken', () => {
    // Parity test matrix — mirrors tokens.py:normalize_input() with broadened separator set.
    // The Worker stores tokens as bare 12-char strings; any input form a human or scanner
    // might produce should reduce to that form.

    it('bare token passes through unchanged', () => {
        expect(normalizeToken('7K2NQ9XRWAB4')).toBe('7K2NQ9XRWAB4');
    });

    it('lowercase bare token is uppercased', () => {
        expect(normalizeToken('7k2nq9xrwab4')).toBe('7K2NQ9XRWAB4');
    });

    it('grouped code (dashes) strips dashes', () => {
        expect(normalizeToken('7K2N-Q9XR-WAB4')).toBe('7K2NQ9XRWAB4');
    });

    it('human code with HUG- prefix strips prefix and dashes', () => {
        expect(normalizeToken('HUG-7K2N-Q9XR-WAB4')).toBe('7K2NQ9XRWAB4');
    });

    it('HUG- prefix lowercase is handled', () => {
        expect(normalizeToken('hug-7k2n-q9xr-wab4')).toBe('7K2NQ9XRWAB4');
    });

    it('full scan URL extracts token from last path segment', () => {
        expect(normalizeToken('https://hug.fjp.vn/h/7K2NQ9XRWAB4')).toBe('7K2NQ9XRWAB4');
    });

    it('full URL with query and fragment is stripped to token', () => {
        expect(normalizeToken('https://hug.fjp.vn/h/7K2NQ9XRWAB4?foo=1#bar')).toBe('7K2NQ9XRWAB4');
    });

    it('URL-encoded spaces (%20) are decoded before processing', () => {
        expect(normalizeToken('HUG%207K2N%20Q9XR%20WAB4')).toBe('7K2NQ9XRWAB4');
    });

    it('underscore separators are stripped', () => {
        expect(normalizeToken('7K2N_Q9XR_WAB4')).toBe('7K2NQ9XRWAB4');
    });

    it('dot separators are stripped', () => {
        expect(normalizeToken('7K2N.Q9XR.WAB4')).toBe('7K2NQ9XRWAB4');
    });

    it('12-char token starting with HUG is NOT stripped (length guard)', () => {
        // HUG2345678AB is a valid 12-char token — stripping HUG would corrupt it.
        // The 15-char length guard in normalizeToken ensures this is returned as-is.
        // (H-U-G-2-3-4-5-6-7-8-A-B = 12 chars)
        expect(normalizeToken('HUG2345678AB')).toBe('HUG2345678AB');
    });

    it('garbage input is returned as-is (length != 12 caught by caller guard)', () => {
        expect(normalizeToken('XXXX')).toBe('XXXX');
    });
});

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
