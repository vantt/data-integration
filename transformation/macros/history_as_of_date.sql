{#-
  history_as_of_date(ts)

  ICT calendar day a capture taken at `ts` (TIMESTAMPTZ) stands for: the ICT date of
  ts - history_day_cutoff_hour. With the default 6, the 03:01 nightly capture of day D+1 records
  the end of day D, and a manual capture at 10:00 on day D records day D (and is replaced by the
  next nightly). The rule lives here, not in raw, so changing it only needs a rebuild.
-#}
{% macro history_as_of_date(ts) -%}
CAST(timezone('Asia/Ho_Chi_Minh', {{ ts }}) - to_hours({{ var('history_day_cutoff_hour') | int }}) AS DATE)
{%- endmacro %}
