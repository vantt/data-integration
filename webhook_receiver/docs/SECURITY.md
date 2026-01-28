# Security Configuration

> HMAC validation, authentication, and security best practices

## HMAC Validation

### Overview

Sapo signs webhooks with HMAC-SHA256. The worker validates signatures to ensure webhooks are authentic.

### Signature Format

Sapo sends signature in header:

```
X-Sapo-Hmac-SHA256: base64_encoded_signature
```

### Validation Logic

```typescript
import { createHmac } from 'crypto';

function validateSignature(
  payload: string,
  signature: string,
  secret: string
): boolean {
  const expectedSignature = createHmac('sha256', secret)
    .update(payload)
    .digest('base64');

  return timingSafeEqual(
    Buffer.from(signature),
    Buffer.from(expectedSignature)
  );
}
```

### Worker Implementation

```typescript
// src/routes.ts
export async function handleWebhook(request: Request, env: Env): Promise<Response> {
  // Get signature from header
  const signature = request.headers.get('X-Sapo-Hmac-SHA256');
  if (!signature) {
    return new Response(JSON.stringify({
      status: 'error',
      message: 'Missing HMAC signature'
    }), { status: 401 });
  }

  // Get raw body
  const body = await request.text();

  // Validate
  const isValid = validateSignature(body, signature, env.HMAC_SECRET);
  if (!isValid) {
    return new Response(JSON.stringify({
      status: 'error',
      message: 'Invalid HMAC signature'
    }), { status: 401 });
  }

  // Process webhook...
}
```

### Configure Secret

In Cloudflare dashboard:

1. Workers & Pages → your worker → Settings → Variables
2. Add secret: `HMAC_SECRET` = your Sapo webhook secret

Or via wrangler:

```bash
npx wrangler secret put HMAC_SECRET
# Enter your secret when prompted
```

---

## Development Mode

For local development, skip HMAC validation:

```typescript
const skipHmac = env.ENVIRONMENT === 'development';

if (!skipHmac) {
  const isValid = validateSignature(body, signature, env.HMAC_SECRET);
  if (!isValid) {
    return errorResponse(401, 'Invalid signature');
  }
}
```

**Warning:** Never deploy with HMAC validation disabled.

---

## Consumer Authentication

The poll/ack endpoints should be protected.

### API Token

```typescript
// src/routes.ts
function authenticateConsumer(request: Request, env: Env): boolean {
  const authHeader = request.headers.get('Authorization');
  if (!authHeader) return false;

  const [type, token] = authHeader.split(' ');
  if (type !== 'Bearer') return false;

  return token === env.CONSUMER_API_TOKEN;
}

export async function handlePoll(request: Request, env: Env): Promise<Response> {
  if (!authenticateConsumer(request, env)) {
    return new Response(JSON.stringify({
      status: 'error',
      message: 'Unauthorized'
    }), { status: 401 });
  }

  // Process poll...
}
```

### Consumer Configuration

```python
# ingestion/.dlt/secrets.toml
[sources.cloudflare_d1]
worker_url = "https://your-worker.workers.dev"
api_token = "your_consumer_token"
```

---

## Rate Limiting

Prevent abuse with rate limiting:

```typescript
// Using Cloudflare Workers rate limiting
export default {
  async fetch(request: Request, env: Env, ctx: ExecutionContext) {
    // Check rate limit
    const ip = request.headers.get('CF-Connecting-IP');
    const { success } = await env.RATE_LIMITER.limit({ key: ip });

    if (!success) {
      return new Response(JSON.stringify({
        status: 'error',
        message: 'Rate limit exceeded'
      }), { status: 429 });
    }

    return handleRequest(request, env, ctx);
  }
};
```

### Configure Rate Limiter

In wrangler.toml:

```toml
[[rate_limiting_rules]]
name = "webhook_rate_limit"
match = {path = "/webhook/*"}
limit = 1000
period = 60
```

---

## IP Allowlisting

Restrict webhook sources to known Sapo IPs:

```typescript
const ALLOWED_IPS = [
  '103.x.x.x',  // Sapo production
  '103.y.y.y',  // Sapo backup
];

function checkAllowedIP(request: Request): boolean {
  const clientIP = request.headers.get('CF-Connecting-IP');
  return ALLOWED_IPS.includes(clientIP);
}
```

**Note:** Get official Sapo IP ranges from their documentation.

---

## Data Protection

### Sensitive Data Handling

```typescript
// Don't log full payloads
console.log(JSON.stringify({
  event: 'webhook_received',
  source: source,
  entity: entity,
  action: action,
  // Don't include: payload
}));
```

### Payload Encryption (Optional)

For extra security, encrypt payloads at rest:

```typescript
import { encrypt, decrypt } from './crypto';

// On receive
const encryptedPayload = await encrypt(payload, env.ENCRYPTION_KEY);
await db.insert({ ...msg, payload: encryptedPayload });

// On poll
const decryptedPayload = await decrypt(row.payload, env.ENCRYPTION_KEY);
```

---

## Audit Logging

Track all security events:

```typescript
async function auditLog(env: Env, event: {
  type: string;
  source_ip: string;
  status: 'success' | 'failure';
  details?: string;
}) {
  await env.AUDIT_LOG.writeDataPoint({
    blobs: [event.type, event.source_ip, event.status],
    doubles: [Date.now()],
    indexes: [event.type]
  });
}

// Usage
await auditLog(env, {
  type: 'hmac_validation_failed',
  source_ip: clientIP,
  status: 'failure',
  details: 'Invalid signature'
});
```

---

## Security Checklist

### Deployment

- [ ] HMAC_SECRET configured as secret (not env var)
- [ ] CONSUMER_API_TOKEN configured as secret
- [ ] ENVIRONMENT set to "production"
- [ ] Rate limiting enabled
- [ ] Audit logging enabled

### Code Review

- [ ] No secrets in code
- [ ] No sensitive data in logs
- [ ] Input validation on all endpoints
- [ ] SQL injection prevention (parameterized queries)

### Monitoring

- [ ] Alert on authentication failures
- [ ] Alert on rate limit hits
- [ ] Regular audit log review

---

## Incident Response

### Suspected Breach

1. **Rotate secrets immediately:**
   ```bash
   npx wrangler secret put HMAC_SECRET
   npx wrangler secret put CONSUMER_API_TOKEN
   ```

2. **Review audit logs:**
   - Check for unusual IP addresses
   - Check for failed authentication attempts

3. **Notify stakeholders:**
   - Security team
   - Sapo support (if webhook secret compromised)

### Recovery

1. Update Sapo webhook configuration with new secret
2. Update consumer with new API token
3. Monitor for any missed webhooks during incident

---

## Related

- [API Documentation](./API.md)
- [Main Documentation](../../docs/README.md)
