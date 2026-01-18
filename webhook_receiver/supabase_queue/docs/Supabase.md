# Supabase Edge Function & Webhook Implementation Guide

## Setup & Installation

### 1. Install Supabase CLI

```bash
# Install Supabase CLI globally using npm
npm install -g supabase

# Install Supabase using scoop on windows
scoop bucket add supabase https://github.com/supabase/scoop-bucket.git
scoop install supabase

# Login to Supabase
supabase login
```

### 2. Project Setup

```bash
# Create and initialize a new Supabase project
supabase init

# Start Supabase locally
supabase start

# Link to your existing Supabase project
supabase link --project-ref your-project-ref

```

### 3. Enable PGMQ

First, in the Integration section, enable Queue feature (PGMQ extension)
Then Run in Supabase SQL editor:

```sql
-- Enable PGMQ extension
create extension if not exists pgmq;

-- Create a queue for webhook
select pgmq.create_queue('webhook_queue');

-- Create function to queue webhooks
create or replace function queue_webhook(webhook_data jsonb)
returns void as $$
begin
  perform pgmq.send(
    queue_name => 'webhook_queue',
    msg => webhook_data
  );
end;
$$ language plpgsql security definer;

-- Grant access
grant execute on function queue_webhook to service_role;
```

## Edge Function Implementation

### 1. Create Edge Function

We name this function: **webhook**

```bash
# Create edge function directory structure
mkdir -p supabase/functions/webhook
cd supabase/functions/webhook

# Create necessary files
touch index.ts  # Main function code
touch .env     # Environment variables for local development
```

The function's access url will be in the format:

```bash
https://<project-ref>.supabase.co/functions/v1/FUNCTION_NAME
```

### 2. Edit `webhook` function

```typescript
// this is just sample content for this edge function

// supabase/functions/webhook/index.ts
import { serve } from "https://deno.fresh.dev/std@v1/http/server.ts";
import { createClient } from "https://esm.sh/@supabase/supabase-js@2";

serve(async (req: Request) => {
  try {
    if (req.method === 'OPTIONS') {
      return new Response('ok', {
        headers: {
          'Access-Control-Allow-Origin': '*',
          'Access-Control-Allow-Methods': 'POST',
          'Access-Control-Allow-Headers': 'authorization, x-client-info, apikey, content-type',
        }
      });
    }

    // Extract entity_type and entity_action from URL path
    const path = new URL(req.url).pathname;
    const [, , , , entity_type, entity_action] = path.split('/');

    const supabaseClient = createClient(
      Deno.env.get('SUPABASE_URL') ?? '',
      Deno.env.get('SUPABASE_SERVICE_ROLE_KEY') ?? ''
    );

    const payload = {
      ...await req.json(),
      entity_type,
      action: `${entity_type}.${entity_action}`
    };

    const { error } = await supabaseClient.rpc('queue_webhook', {
      webhook_data: payload
    });

    if (error) throw error;

    return new Response(JSON.stringify({ status: 'queued' }), { 
      status: 200,
      headers: {
        'Content-Type': 'application/json',
        'Access-Control-Allow-Origin': '*'
      }
    });

  } catch (error) {
    console.error('Error:', error);
    return new Response(JSON.stringify({ error: 'Server error' }), { 
      status: 500,
      headers: {
        'Content-Type': 'application/json',
        'Access-Control-Allow-Origin': '*'
      }
    });
  }
});
```

### 3. Deploy Edge Function

```bash
# Test locally first
supabase functions serve webhook --env-file supabase/functions/webhook/.env --no-verify-jwt

# Deploy the webhook function
supabase functions deploy webhook --no-verify-jwt

# Set secrets
supabase secrets set SUPABASE_SERVICE_ROLE_KEY=your_service_role_key

# List all edge functions
supabase functions list

```



## Testing

### 1. Test Edge Function Locally

```bash
# Start function locally
supabase functions serve webhook

# Test with curl
curl -i -X POST http://localhost:54321/functions/v1/webhook/order/create \
-H "Content-Type: application/json" \
-H "Authorization: Bearer your-local-service-role-key" \
-d '{
  "amount": 99.99,
  "customer_id": "cust_123"
}'
```

### 2. Test Deployed Function

```bash
curl -i -X POST https://[PROJECT_REF].supabase.co/functions/v1/webhook/order/create \
-H "Content-Type: application/json" \
-H "Authorization: Bearer your-service-role-key" \
-d '{
  "amount": 99.99,
  "customer_id": "cust_123"
}'
```

## URL Patterns

- Base URL: `https://[PROJECT_REF].supabase.co/functions/v1/webhook`
- Entity URLs: `https://[PROJECT_REF].supabase.co/functions/v1/webhook/[source_system]/[entity_type]/[entity_action]`

Examples:

- `webhook/sapo/order/create`
- `webhook/sapo/payment/process`
- `webhook/sapo/shipment/update`

## Monitoring & Maintenance

### Check Queue Status

```sql
-- View current queue messages
SELECT * FROM pgmq.get_queue_messages('webhook_queue');

-- View message history
SELECT * FROM pgmq.get_queue_message_history('webhook_queue');

-- Check failed messages
SELECT * FROM pgmq.get_dead_letter_messages('webhook_queue');
```

### Common Issues & Solutions

1. Queue Not Found
   - Ensure PGMQ extension is enabled
   - Verify queue creation SQL ran successfully

2. Authentication Errors
   - Check service role key is set correctly
   - Verify Authorization header in requests

3. Consumer Connection Issues
   - Verify Supabase URL and credentials
   - Check local PostgreSQL connection
   - Ensure proper network access

## Best Practices

1. Always handle CORS properly in Edge Functions
2. Use service role key for system operations
3. Implement proper error handling and logging
4. Monitor queue size and processing rates
5. Implement retry logic in consumer
6. Keep webhook payloads minimal
7. Use appropriate timeout values
