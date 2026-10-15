{{ config(materialized='table', tags=['labels']) }}
{{ label_std_model('channel_format', 'dim_channels', 'channel_key', 'channel_format', tenant_ref('taxonomy_label')) }}
