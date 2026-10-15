-- Every (domain, label_std) of the tenant's taxonomy_label is a code of taxonomy_canonical:
-- labels are anchored only to codes that exist.
SELECT l.domain, l.label, l.label_std
FROM {{ tenant_ref('taxonomy_label') }} l
LEFT JOIN {{ ref('taxonomy_canonical') }} c
       ON c.domain = l.domain AND c.code = l.label_std
WHERE c.code IS NULL
