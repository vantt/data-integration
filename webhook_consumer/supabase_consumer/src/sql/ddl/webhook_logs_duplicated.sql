-- ARCHIVED: system migrated to Cloudflare D1; this file is no longer used

-- Table: public.webhook_logs_duplicated

-- DROP TABLE IF EXISTS public.webhook_logs_duplicated;

CREATE TABLE IF NOT EXISTS public.webhook_logs_duplicated
(
    _id serial primary key,
	webhook_id text COLLATE pg_catalog."default" NOT NULL,
    entity_type text COLLATE pg_catalog."default" NOT NULL,
    entity_id text COLLATE pg_catalog."default" NOT NULL,
    action_group text COLLATE pg_catalog."default" NOT NULL,
    action text COLLATE pg_catalog."default" NOT NULL,
    source_system text COLLATE pg_catalog."default" NOT NULL,
    source_timestamp timestamp with time zone NOT NULL,
    payload_hash text COLLATE pg_catalog."default" NOT NULL,
    payload jsonb NOT NULL,
    status text COLLATE pg_catalog."default" NOT NULL,
    processing_priority text COLLATE pg_catalog."default" NOT NULL DEFAULT 'medium'::text,
    retry_count integer NOT NULL DEFAULT 0,
    next_retry_at timestamp with time zone,
    processing_history jsonb NOT NULL DEFAULT '[]'::jsonb,
    created_at timestamp with time zone NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamp with time zone NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT webhook_logs_duplicated_pkey PRIMARY KEY (_id),
    CONSTRAINT webhook_logs_duplicated_entity_type_check CHECK (entity_type = ANY (ARRAY['order'::text, 'customer'::text, 'shipment'::text, 'product'::text, 'payment'::text])),
    CONSTRAINT webhook_logs_duplicated_action_group_check CHECK (action_group = ANY (ARRAY['crud'::text, 'status'::text, 'lifecycle'::text, 'system'::text, 'financial'::text, 'security'::text, 'ownership'::text, 'workflow'::text])),
    CONSTRAINT webhook_logs_duplicated_source_system_check CHECK (source_system = ANY (ARRAY['sapo'::text, 'smaxai'::text, 'shopee'::text, 'fb'::text, 'gads'::text, 'tiktok'::text])),
    CONSTRAINT webhook_logs_duplicated_status_check CHECK (status = ANY (ARRAY['received'::text, 'validated'::text, 'processing'::text, 'completed'::text, 'failed'::text])),
    CONSTRAINT webhook_logs_duplicated_processing_priority_check CHECK (processing_priority = ANY (ARRAY['high'::text, 'medium'::text, 'low'::text]))
)

TABLESPACE pg_default;

ALTER TABLE IF EXISTS public.webhook_logs_duplicated
    OWNER to postgres;
-- Index: idx_webhook_logs_duplicated_action

-- DROP INDEX IF EXISTS public.idx_webhook_logs_duplicated_action;

CREATE INDEX IF NOT EXISTS idx_webhook_logs_duplicated_action
    ON public.webhook_logs_duplicated USING btree
    (action_group COLLATE pg_catalog."default" ASC NULLS LAST, action COLLATE pg_catalog."default" ASC NULLS LAST)
    TABLESPACE pg_default;
-- Index: idx_webhook_logs_duplicated_entity

-- DROP INDEX IF EXISTS public.idx_webhook_logs_duplicated_entity;

CREATE INDEX IF NOT EXISTS idx_webhook_logs_duplicated_entity
    ON public.webhook_logs_duplicated USING btree
    (entity_type COLLATE pg_catalog."default" ASC NULLS LAST, entity_id COLLATE pg_catalog."default" ASC NULLS LAST)
    TABLESPACE pg_default;
-- Index: idx_webhook_logs_duplicated_payload_hash

-- DROP INDEX IF EXISTS public.idx_webhook_logs_duplicated_payload_hash;

CREATE INDEX IF NOT EXISTS idx_webhook_logs_duplicated_payload_hash
    ON public.webhook_logs_duplicated USING hash
    (payload_hash COLLATE pg_catalog."default")
    TABLESPACE pg_default;
-- Index: idx_webhook_logs_duplicated_status

-- DROP INDEX IF EXISTS public.idx_webhook_logs_duplicated_status;

CREATE INDEX IF NOT EXISTS idx_webhook_logs_duplicated_status
    ON public.webhook_logs_duplicated USING btree
    (status COLLATE pg_catalog."default" ASC NULLS LAST, processing_priority COLLATE pg_catalog."default" ASC NULLS LAST)
    TABLESPACE pg_default;
-- Index: idx_webhook_logs_duplicated_timestamps

-- DROP INDEX IF EXISTS public.idx_webhook_logs_duplicated_timestamps;

CREATE INDEX IF NOT EXISTS idx_webhook_logs_duplicated_timestamps
    ON public.webhook_logs_duplicated USING btree
    (source_timestamp ASC NULLS LAST, created_at ASC NULLS LAST)
    TABLESPACE pg_default;

-- Trigger: update_webhook_logs_duplicated_updated_at

-- DROP TRIGGER IF EXISTS update_webhook_logs_duplicated_updated_at ON public.webhook_logs_duplicated;

CREATE OR REPLACE TRIGGER update_webhook_logs_duplicated_updated_at
    BEFORE UPDATE 
    ON public.webhook_logs_duplicated
    FOR EACH ROW
    EXECUTE FUNCTION public.update_updated_at_column();