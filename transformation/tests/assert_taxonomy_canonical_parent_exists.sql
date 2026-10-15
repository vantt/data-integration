-- Every parent_code of taxonomy_canonical is a code of the same domain.
SELECT c.domain, c.code, c.parent_code
FROM {{ ref('taxonomy_canonical') }} c
LEFT JOIN {{ ref('taxonomy_canonical') }} p
       ON p.domain = c.domain AND p.code = c.parent_code
WHERE c.parent_code IS NOT NULL
  AND p.code IS NULL
