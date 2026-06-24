# Plan: Messenger Webhook HMAC Verification

**Status:** Deferred / Not started
(updated 2026-06-24: explicitly deferred — Messenger integration not live; FB app secret not yet provisioned; plan is ready to execute when real token is available)

## Context

`POST /api/conversations/messenger/ingest` (`conversation_handler.py:104`) accepts raw FB Messenger webhook payloads with no authentication. The code comment notes the TODO explicitly. The endpoint is LAN-only but any LAN host can forge payloads.

## Implementation Steps

1. **Env var** — add `CRM_MESSENGER_WEBHOOK_SECRET` to `.env` / Docker compose env. This is the FB App Secret (not page token). Document in `crm/docs/deployment-guide.md`.

2. **Verification function** — add to `conversation_handler.py`:
   ```python
   import hashlib, hmac

   def _verify_fb_signature(body: bytes, header: str | None, secret: str) -> bool:
       """Return True when X-Hub-Signature-256 matches HMAC-SHA256(app_secret, body)."""
       if not header or not header.startswith("sha256="):
           return False
       expected = "sha256=" + hmac.new(
           secret.encode(), body, hashlib.sha256
       ).hexdigest()
       return hmac.compare_digest(expected, header)
   ```

3. **Wire into handler** — at the top of `messenger_ingest()`, before JSON parse:
   ```python
   secret = os.environ.get("CRM_MESSENGER_WEBHOOK_SECRET", "")
   if secret:
       sig = request.headers.get("X-Hub-Signature-256")
       if not _verify_fb_signature(body, sig, secret):
           raise HTTPException(status_code=401, detail="invalid signature")
   ```
   Secret absent → skip check (preserves local-dev / staging without FB). Secret present → hard reject on mismatch.

4. **Tests** — add to `test_crm_conversation_handler.py` (or new file):
   - valid signature → 200
   - wrong signature → 401
   - missing header when secret set → 401
   - missing secret env var → skips check, returns 200

5. **Activation gate** — deploy with `CRM_MESSENGER_WEBHOOK_SECRET` unset until the FB app goes live. Set it in Docker compose / Fly secrets when the Messenger integration is activated.

## Files to touch

- `crm/src/adapters/inbound/http/conversation_handler.py` — add `_verify_fb_signature` + wire
- `.env.example` — document `CRM_MESSENGER_WEBHOOK_SECRET=`
- `crm/src/tests/test_crm_conversation_handler.py` — new tests

## Risk

Low — the guard is a no-op until the secret is set, so there is no regression for the current LAN-only setup.
