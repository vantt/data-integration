# Global Agent Rules

**IMPORTANT:** _MUST READ_ and _MUST COMPLY_ with all _INSTRUCTIONS_ in project based on the context.

## Review Policy

- **Implementation Plan Approval**: Even if the general review policy is set to `Auto-proceeded`, you MUST ALWAYS obtain explicit user approval for any `implementation_plan.md` before proceeding to execution. Do not auto-proceed with implementation plans under any circumstances.

## Multi-Project Repository Structure: `data-integration2`

**CRITICAL:** `data-integration2` is a monorepo containing THREE main independent functional areas with specific sub-projects:

### 1. DLT Pipelines (`data-integration2/dlt`)

- **Purpose:** General data extraction pipelines (e.g., Sapo orders).
- **Tech:** Python, `dlt` (Data Load Tool), `playwright`.
- **Context:** Python-based ETL scripts.
- **Dependencies:** Independent `requirements.txt` in `/dlt/`.

### 2. Webhook Receiver (`data-integration2/webhook_receiver`)

- **Purpose:** Service endpoints to receive and buffer incoming webhooks.
- **Implementations:**
  - **`cloudflareD1` (Recommended):**
    - **Tech:** TypeScript, Cloudflare Workers, SQLite (D1).
    - **Path:** `/webhook_receiver/cloudflareD1/`
    - **Docs:** `/webhook_receiver/cloudflareD1/README.md`
  - **`supabase_queue` (Legacy):**
    - **Tech:** Supabase Edge Functions, PostgreSQL (PGMQ).
    - **Path:** `/webhook_receiver/supabase_queue/`

### 3. Webhook Consumer (`data-integration2/webhook_consumer`)

- **Purpose:** Workers that polling/consume buffered webhooks and load them into the warehouse.
- **Implementations:**
  - **`cloudflared1_consumer`:**
    - **Tech:** Python, `dlt`.
    - **Mechanism:** Polls the Cloudflare Worker API.
    - **Path:** `/webhook_consumer/cloudflared1_consumer/`
  - **`supabase_consumer`:**
    - **Tech:** TypeScript, Node.js.
    - **Path:** `/webhook_consumer/supabase_consumer/`

---

## AI Agent Rules for Multi-Project Repos

**BEFORE performing ANY operation:**

1.  **Verify Current Context:** Always check which sub-project/folder the user is working on.
2.  **Check Working Directory:** Use `pwd` or context clues to determine the location.
3.  **Respect Project Boundaries:**
    - **DLT** files ONLY in `/dlt/`
    - **Receiver** files ONLY in `/webhook_receiver/`
    - **Consumer** files ONLY in `/webhook_consumer/`
    - **NEVER** mix dependencies (e.g., do not verify `package.json` if working in a Python `dlt` folder).

**When User Context is Ambiguous:**

- Ask which implementation they are working on (e.g., "Are you working on the Cloudflare D1 receiver or the Supabase queue?").
- Do NOT assume - always clarify before making changes.

**File Operations Safety:**

- **NEVER** move files between sub-projects without explicit instruction.
- **When searching:** Scope grep/search to the relevant sub-project directory to avoid false positives from sibling projects.
