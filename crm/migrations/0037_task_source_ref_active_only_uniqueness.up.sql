-- Migration 0037 UP: scope uidx_task_source_ref to active tasks only.
--
-- The original index (0004) enforces (source, source_ref) uniqueness across ALL
-- rows regardless of status. That's correct for one-shot sources like
-- 'action_queue' (source_ref=action_id never recurs), but wrong for
-- 'action_queue_claim' (source_ref=party_id): claim -> unclaim (cancelled) ->
-- claim again is a normal, repeatable cycle. get_customer_claim() already only
-- treats NOT IN ('done','cancelled') as an active claim — the index must match
-- or every re-claim after an unclaim/completion hits a UNIQUE constraint
-- violation (500, task never created).
DROP INDEX IF EXISTS uidx_task_source_ref;

CREATE UNIQUE INDEX IF NOT EXISTS uidx_task_source_ref
  ON crm_task (source, source_ref)
  WHERE source_ref IS NOT NULL AND status NOT IN ('done', 'cancelled');
