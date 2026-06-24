"""CRM operational tooling (backup / restore-verify).

Standalone, import-callable modules so they can later be wired into a scheduler
(Dagster op via a CRM admin endpoint, host cron, etc.) without a rewrite.
"""
