

-- Static dimension for status analysis
-- Static dimension for status analysis
SELECT md5('OPEN') as status_key, 'OPEN' as status_code, 'Open Orders' as description
UNION ALL SELECT md5('COMPLETED'), 'COMPLETED', 'Completed Orders'
UNION ALL SELECT md5('CANCELLED'), 'CANCELLED', 'Cancelled Orders'
UNION ALL SELECT md5('ARCHIVED'), 'ARCHIVED', 'Archived Orders'
UNION ALL SELECT md5('DRAFT'), 'DRAFT', 'Draft Orders'