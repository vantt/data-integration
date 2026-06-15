# Contact Quality Design

**Date:** 2026-06-15 | **Feature:** Party Identity Contact Quality Tracking | **Status:** Design Frozen

## Problem

Shopee masks customer phone numbers via relay (virtual intermediary). When orders sync into CRM, `contact_number` is the relay number — useless for post-order outreach. Currently, `fact_payments` is empty, and `crm_party_identity` has no way to distinguish contact source quality or track real-contact capture progress.

**KPI:** Shopee → direct contact capture rate (% marketplace orders where team extracted real contact info).

## Solution: Two-Column Schema

Add two immutable-on-creation columns to `crm_party_identity`:

### `source_contact_quality TEXT NOT NULL DEFAULT 'real'`
Set once at creation. Indicates where contact came from.
- `masked` — relay/virtual number (Shopee, Lazada, any marketplace)
- `real` — genuine contact provided upfront (direct channel, manual entry)

### `contact_quality TEXT NOT NULL DEFAULT 'real'`
Mutable. Tracks verification state.
- `masked` — still relay-protected, no real contact yet
- `unverified` — real contact obtained but not validated
- `verified` — live contact confirmed (call/message success)

## Automation Rules

| Event | source_contact_quality | contact_quality |
|-------|------------------------|-----------------|
| Sapo sync Shopee/Lazada order | `masked` | `masked` |
| Staff enters real number into CRM | `masked` | `unverified` |
| Call/message confirmed | `masked` | `verified` |
| Direct channel order (non-marketplace) | `real` | `real` |
| Manual entry, non-marketplace source | `real` | `unverified` |

Marketplace detection: `channel_group = 'marketplace'` (fact_orders) or `source_system = 'sapo'` + channel contains 'shopee'/'lazada'.

## KPI Query

```sql
SELECT
  COUNT(*) FILTER (
    WHERE source_contact_quality = 'masked'
      AND contact_quality IN ('unverified','verified')
  ) AS captured,
  COUNT(*) FILTER (
    WHERE source_contact_quality = 'masked'
  ) AS total_marketplace_contacts,
  ROUND(100.0 * captured / NULLIF(total_marketplace_contacts, 0), 1) AS capture_rate_pct
FROM crm_party_identity
WHERE identity_type = 'phone'
  AND created_at >= :start_date
```

## Design Rationale

- **Two fields:** `source_contact_quality` (immutable audit trail) vs `contact_quality` (mutable progress). Comparing them reveals capture effort.
- **`masked` over `relay`:** `relay` is technical; `masked` describes data state, reusable across all platform masking schemes.
- **`unverified` over `real`:** Avoids confusion—`real` ≠ `verified`. `unverified` = contact obtained but not confirmed.
- **DEFAULT `'real'`:** Non-marketplace contacts unaffected; no existing data migration needed.

## Files to Modify

1. `crm/migrations/0006_party_identity_contact_quality.up.sql` (NEW)
2. `crm/migrations/0006_party_identity_contact_quality.down.sql` (NEW)
3. `crm/app/internal/domain/party.go`
4. `crm/app/internal/adapters/outbound/sqlite/queries/party_queries.sql`
5. `crm/app/internal/adapters/outbound/sqlite/sqlcgen/models.go`
6. `crm/app/internal/adapters/outbound/sqlite/sqlcgen/party_queries.sql.go`
7. `crm/app/internal/adapters/outbound/sqlite/party_repo.go`
