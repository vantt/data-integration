# Setup Metabase MCP Server

Configure the Metabase MCP server (`metabase-ai-assistant`) for Claude Code.

## Context

Read `.skills/metabase-automation/SKILL.md` for Metabase API details.
Read `.agents/skills/setup_metabase_mcp/SKILL.md` for full MCP configuration including the `disabledTools` list.

## Steps

1. **Check Prerequisites**:
   - Node.js & npm installed
   - Metabase running at http://127.0.0.1:3000/
   - API Key available (Admin -> Settings -> API Key)

2. **Update Claude Code Settings**:
   Add the `metabase` MCP server to `.claude/settings.local.json`:

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
         "disabled": false
       }
     }
   }
   ```

   See `.agents/skills/setup_metabase_mcp/SKILL.md` for the recommended `disabledTools` list to reduce context noise.

3. **Verify**: Restart Claude Code, then test with `mcp_metabase_db_list`.

## User Arguments

$ARGUMENTS
