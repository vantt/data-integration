{{ config(materialized='table', tags=['labels']) }}
{{ label_std_model('channel_category', 'dim_channels', 'channel_key', 'channel_category', tenant_ref('taxonomy_label')) }}
