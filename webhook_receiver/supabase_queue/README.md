## Install supabase cli

# For Windows (using PowerShell)

## Prerequisites

- [Scoop](https://scoop.sh/) (optional, for installing Supabase CLI)
- Docker (required for Supabase local development)

## Automated Setup (Recommended)

Run the helper script to verify prerequisites, start Supabase, and apply migrations:

```powershell
./setup_dev.ps1
```

## Manual Setup

1. **Install Supabase CLI**

   ```powershell
   scoop bucket add supabase https://github.com/supabase/scoop-bucket.git
   scoop install supabase
   supabase --version
   ```

2. **Login to Supabase**

   ```powershell
   supabase login
   ```

3. **Initialize/Start Project**

   ```powershell
   supabase init # If not already initialized
   supabase start
   ```

4. **Apply Migrations**
   This sets up the `pgmq` extension, `webhook_queue`, and necessary database functions automatically.

   ```powershell
   supabase db reset
   ```

## Deploying to Production

1. **Link to your Supabase project**

   ```powershell
   # Connects your local project to the remote Supabase project.
   # 'your-project-ref' is the ID found in your Supabase project URL (e.g., app.supabase.com/project/your-project-ref)
   supabase link --project-ref your-project-ref
   ```

2. **Push Migrations**

   ```powershell
   # Reads SQL files from 'supabase/migrations' and applies them to the remote database.
   # This ensures your production DB has the same structure (Queues, Functions) as local.
   supabase db push
   ```

3. **Deploy Edge Functions**

   ```powershell
   # Deploy the webhook receiver function
   supabase functions deploy webhook-receiver --no-verify-jwt

   # Set necessary secrets (if applicable)
   supabase secrets set SUPABASE_SERVICE_ROLE_KEY=your_service_role_key
   ```

## Testing

### Local Testing

```powershell
supabase functions serve webhook-receiver --env-file supabase/functions/webhook-receiver/.env --no-verify-jwt
```

Function URL: `http://127.0.0.1:54321/functions/v1/webhook-receiver` (Port may vary, check output)

### Production URL

`https://<project-ref>.supabase.co/functions/v1/webhook-receiver`
