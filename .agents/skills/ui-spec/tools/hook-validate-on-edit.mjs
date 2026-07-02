// hook-validate-on-edit.mjs — Claude Code PostToolUse hook (Edit|Write).
// Reads the hook input JSON from stdin; if the edited file is a markdown file
// under crm/docs/ui-spec/, runs the ui-spec validator against that spec root.
// Exit 0 = pass or not applicable. Exit 2 = validation errors (fed back to the model).

import { spawnSync } from "node:child_process";
import { fileURLToPath } from "node:url";
import { dirname, resolve, sep } from "node:path";

// Repo root: env when the harness provides it, else derived from this file's
// location (.agents/skills/ui-spec/tools/ -> four levels up).
const TOOLS_DIR = dirname(fileURLToPath(import.meta.url));
const REPO_ROOT = process.env.CLAUDE_PROJECT_DIR
  ? resolve(process.env.CLAUDE_PROJECT_DIR)
  : resolve(TOOLS_DIR, "..", "..", "..", "..");

const SPEC_ROOT = resolve(REPO_ROOT, "crm", "docs", "ui-spec");

let raw = "";
try { raw = (await import("node:fs")).readFileSync(0, "utf8"); } catch { process.exit(0); }

let filePath = "";
try {
  const input = JSON.parse(raw || "{}");
  filePath = input?.tool_input?.file_path || input?.tool_response?.filePath || "";
} catch { process.exit(0); }

if (!filePath || !filePath.toLowerCase().endsWith(".md")) process.exit(0);

// Scope gate: only markdown inside the crm spec root (generated/ excluded — build output).
const abs = resolve(filePath);
const specPrefix = SPEC_ROOT + sep;
if (!abs.startsWith(specPrefix)) process.exit(0);
if (abs.startsWith(resolve(SPEC_ROOT, "generated") + sep)) process.exit(0);

const res = spawnSync(process.execPath, [resolve(TOOLS_DIR, "validate.mjs"), "--root", SPEC_ROOT], {
  encoding: "utf8",
  timeout: 60_000,
});

if (res.status !== 0) {
  // stderr + exit 2 -> PostToolUse blocking feedback, injected back to the model.
  const out = `${res.stdout ?? ""}${res.stderr ?? ""}`.trim();
  console.error(`ui-spec validate FAILED after editing ${filePath}:\n${out}\nFix the errors above (source: .md files, not generated/).`);
  process.exit(2);
}
process.exit(0);
