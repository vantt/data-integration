-- Strip +84 prefix from crm_party.primary_phone
UPDATE crm_party
SET primary_phone = '0' || substr(primary_phone, 4)
WHERE primary_phone LIKE '+84%';

-- Strip +84 prefix from crm_party_identity phone values
UPDATE crm_party_identity
SET identity_value = '0' || substr(identity_value, 4)
WHERE identity_type IN ('phone', 'phone_secondary')
  AND identity_value LIKE '+84%';
