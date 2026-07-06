-- Migration 0037 DOWN: restore the original all-rows uniqueness.
DROP INDEX IF EXISTS uidx_task_source_ref;

CREATE UNIQUE INDEX IF NOT EXISTS uidx_task_source_ref
  ON crm_task (source, source_ref) WHERE source_ref IS NOT NULL;
