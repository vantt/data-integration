---
name: setup-metabase-mcp
description: Set up and configure the Metabase MCP server for AI coding agents such as Claude Code, Antigravity, or Codex.
---

# Setup Metabase MCP

This skill guides you through checking and configuring the Metabase MCP server using `metabase-ai-assistant`.

## Configuration Details

### 1. Prerequisites

- Node.js and npm installed.
- Metabase instance running, default `http://127.0.0.1:3000/`.
- Metabase API key available from Admin Settings or User Account Settings.

### 2. Configuration

Add the `metabase` MCP server entry to the agent config file:

- Claude Code: `.claude/settings.local.json` under `mcpServers`.
- Antigravity: `mcp_config.json`.

Use the `disabledTools` list to exclude high-volume or irrelevant tools that can clutter the context window.

```json
{
  "mcpServers": {
    "metabase": {
      "command": "npx",
      "args": ["-y", "metabase-ai-assistant"],
      "env": {
        "METABASE_URL": "http://127.0.0.1:3000/",
        "METABASE_API_KEY": "<YOUR_API_KEY>"
      },
      "disabled": false,
      "disabledTools": [
        "db_test_speed",
        "mb_question_create",
        "mb_dashboard_create",
        "mb_question_create_parametric",
        "mb_dashboard_add_card",
        "web_fetch_metabase_docs",
        "web_explore_metabase_docs",
        "web_search_metabase_docs",
        "web_metabase_api_reference",
        "mb_metric_create",
        "mb_dashboard_add_filter",
        "mb_dashboard_layout_optimize",
        "mb_auto_describe",
        "ai_sql_optimize",
        "ai_sql_explain",
        "db_table_create",
        "db_view_create",
        "db_matview_create",
        "db_index_create",
        "db_table_ddl",
        "db_view_ddl",
        "db_ai_list",
        "db_ai_drop",
        "db_schema_analyze",
        "db_relationships_detect",
        "ai_relationships_suggest",
        "mb_relationships_create",
        "activity_log_init",
        "activity_session_summary",
        "activity_operation_stats",
        "activity_database_usage",
        "activity_error_analysis",
        "activity_performance_insights",
        "activity_timeline",
        "activity_cleanup",
        "definition_tables_init",
        "definition_search_terms",
        "definition_get_metric",
        "definition_get_template",
        "definition_global_search",
        "parametric_question_create",
        "parametric_dashboard_create",
        "parametric_template_preset",
        "db_vacuum_analyze",
        "db_query_explain",
        "db_table_stats",
        "db_index_usage",
        "mb_visualization_settings",
        "mb_visualization_recommend",
        "mb_collection_create",
        "mb_collection_move",
        "mb_action_create",
        "mb_action_list",
        "mb_action_execute",
        "mb_alert_create",
        "mb_alert_list",
        "mb_pulse_create",
        "mb_embed_url_generate",
        "mb_embed_settings",
        "mb_user_list",
        "mb_user_get",
        "mb_user_create",
        "mb_user_update",
        "mb_user_disable",
        "mb_permission_group_list",
        "mb_permission_group_create",
        "mb_permission_group_delete",
        "mb_permission_group_add_user",
        "mb_permission_group_remove_user",
        "mb_collection_permissions_get",
        "mb_collection_permissions_update",
        "mb_card_update",
        "mb_card_delete",
        "mb_card_archive",
        "mb_dashboard_update",
        "mb_dashboard_delete",
        "mb_dashboard_card_update",
        "mb_dashboard_card_remove",
        "mb_card_copy",
        "mb_card_clone",
        "mb_dashboard_copy",
        "mb_collection_copy",
        "mb_segment_create",
        "mb_segment_list",
        "mb_bookmark_create",
        "mb_bookmark_list",
        "mb_bookmark_delete",
        "db_sync_schema",
        "mb_cache_invalidate",
        "mb_meta_query_performance",
        "mb_meta_content_usage",
        "mb_meta_user_activity",
        "mb_meta_database_usage",
        "mb_meta_dashboard_complexity",
        "mb_meta_info",
        "mb_meta_table_dependencies",
        "mb_meta_impact_analysis",
        "mb_meta_optimization_recommendations",
        "mb_meta_error_patterns",
        "mb_meta_export_workspace",
        "mb_meta_import_preview",
        "mb_meta_compare_environments",
        "mb_meta_auto_cleanup"
      ]
    }
  }
}
```

### 3. Verification Steps

After updating the configuration:

1. Restart the MCP client.
2. Run `mcp_metabase_db_list` to verify connectivity.
3. Check `mcp_metabase_db_schemas` for the target database.
