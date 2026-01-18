# Cloudflare Webhook Deployment Guide

This guide details the steps to deploy the `webhook-receiver` Cloudflare Worker and its associated D1 database.

## Prerequisites

- **Node.js**: Ensure Node.js (v16+) is installed.
- **Cloudflare Account**: You need a Cloudflare account.
- **Wrangler CLI**: Installed globally or via `npm` (included in `devDependencies`).

## Step 1: Installation

Navigate to the project directory and install dependencies:

```bash
cd data-integration/data_webhook_receiver/cloudflare_webhook
npm install
```

## Step 2: Cloudflare Login

If you haven't used Wrangler before, you need to log in to your Cloudflare account:

```bash
npx wrangler login
```

Allow the browser to open and authorize Wrangler.

## Step 3: D1 Database Setup

1. **Create the D1 Database**:
   Run the following command to create a new D1 database named `webhook-db`:

   ```bash
   npx wrangler d1 create fgcare-webhook-db
   ```

2. **Update `wrangler.toml`**:
   The previous command will output a `database_id`. Copy this ID and update your `wrangler.toml` file:

   ```toml
   [[d1_databases]]
   binding = "DB"
   database_name = "fgcare-webhook-db"
   database_id = "YOUR_GENERATED_ID_HERE"
   ```

3. **Initialize the Schema**:
   Apply the database schema to create the necessary tables:

   ```bash
   npx wrangler d1 execute fgcare-webhook-db --file=./schema.sql
   ```

   _Note: For local development testing, you can add `--local` to the command._

## Step 4: Environment Secrets

The worker uses HMAC validation to secure webhooks. You must set the `WEBHOOK_SECRET` environment variable.

1. **Enable HMAC Verification**:
   By default, HMAC verification is **disabled**. To enable it, set `CHECK_HMAC` to `true`.

   ```bash
   npx wrangler secret put CHECK_HMAC
   ```

   (Set value to `true`)

2. **Set `WEBHOOK_SECRET`**:

   ```bash
   npx wrangler secret put WEBHOOK_SECRET
   ```

   Enter your secret value when prompted.

3. **(Optional) Set `HMAC_HEADER_NAME`**:
   If your webhook source uses a custom header for the signature (default is `x-hub-signature-256`), set it here:

   ```bash
   npx wrangler secret put HMAC_HEADER_NAME
   ```

   (Set value to `x-hub-signature-256`)

## Step 5: Deployment

Deploy the worker to Cloudflare:

```bash
npm run deploy
```

This command runs `wrangler deploy`, uploading your worker and binding it to the D1 database.

## Step 6: Verification

After deployment, `wrangler` will output your worker's URL (e.g., `https://webhook-receiver.<your-subdomain>.workers.dev`).

### Test with CURL

**Webhooks (Ingest):**

```bash
curl -X POST https://<YOUR_WORKER_URL>/webhook/test_source/user/create \
  -H "Content-Type: application/json" \
  -H "x-hub-signature-256: <CALCULATED_HMAC_SHA256>" \
  -d '{"foo":"bar"}'
```

_Note: You will need to generate a valid HMAC SHA256 signature matching your `WEBHOOK_SECRET` for the request to be accepted._

**Poll (Consume):**

```bash
curl "https://<YOUR_WORKER_URL>/poll?limit=5"
```

## Troubleshooting

- **Database Errors**: Ensure your `database_id` in `wrangler.toml` matches the one in Cloudflare.
- **Auth Errors (401)**: Verify that `WEBHOOK_SECRET` is set correctly and that you are generating the HMAC signature correctly in your test requests.
