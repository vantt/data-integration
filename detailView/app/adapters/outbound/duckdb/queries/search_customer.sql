-- Resolve customers by exact id, digits-normalised phone, or exact email (case-insensitive).
-- Phone match strips non-digits from both sides so '0901-234-567' matches '0901234567'.
-- Capped to 10 hits in the adapter.
SELECT
    customer_id,
    full_name,
    phone,
    value_group
FROM dim_customers
WHERE customer_id = ?
   OR (? <> '' AND regexp_replace(COALESCE(phone, ''), '[^0-9]', '', 'g') = ?)
   OR (? <> '' AND LOWER(COALESCE(email, '')) = LOWER(?))
LIMIT 10;
