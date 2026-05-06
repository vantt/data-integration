#!/usr/bin/env node
/**
 * One-time setup: deploy data-pipeline lesson-reminder hook to this Claude environment.
 *
 * Idempotent — safe to re-run. Does two things:
 *   1. Copies hook source → $HOME/.claude/hooks/
 *   2. Merges hook entry → .claude/settings.local.json (project-scoped)
 *
 * Usage:
 *   node .skills/data-pipeline/scripts/setup-lesson-reminder-hook.cjs
 */

const fs = require('fs');
const path = require('path');
const os = require('os');

const HOOK_NAME = 'data-pipeline-lesson-reminder.cjs';
const SKILL_ROOT = path.resolve(__dirname, '..');
const SRC = path.join(SKILL_ROOT, 'hooks', HOOK_NAME);
const DEST_DIR = path.join(os.homedir(), '.claude', 'hooks');
const DEST = path.join(DEST_DIR, HOOK_NAME);

// Repo root = 3 levels up from .skills/data-pipeline/scripts/
const REPO_ROOT = path.resolve(__dirname, '..', '..', '..');
const SETTINGS_LOCAL = path.join(REPO_ROOT, '.claude', 'settings.local.json');

const HOOK_ENTRY = {
  matcher: 'Bash',
  hooks: [
    {
      type: 'command',
      command: 'node "$HOME/.claude/hooks/data-pipeline-lesson-reminder.cjs"',
      timeout: 10,
    },
  ],
};

// --- 1. Copy hook to $HOME/.claude/hooks/ ---
if (!fs.existsSync(DEST_DIR)) {
  fs.mkdirSync(DEST_DIR, { recursive: true });
}

fs.copyFileSync(SRC, DEST);
console.log(`✓ Hook deployed → ${DEST}`);

// --- 2. Merge into .claude/settings.local.json ---
let settings = {};
if (fs.existsSync(SETTINGS_LOCAL)) {
  try {
    settings = JSON.parse(fs.readFileSync(SETTINGS_LOCAL, 'utf8'));
  } catch (e) {
    console.error('  ✗ Could not parse settings.local.json:', e.message);
    process.exit(1);
  }
}

if (!settings.hooks) settings.hooks = {};
if (!settings.hooks.PostToolUse) settings.hooks.PostToolUse = [];

// Check if entry already exists (idempotent)
const alreadyWired = settings.hooks.PostToolUse.some(
  (g) => g.matcher === 'Bash' &&
    Array.isArray(g.hooks) &&
    g.hooks.some((h) => h.command && h.command.includes(HOOK_NAME))
);

if (!alreadyWired) {
  // Prepend so it runs before other Bash hooks
  settings.hooks.PostToolUse.unshift(HOOK_ENTRY);
  fs.writeFileSync(SETTINGS_LOCAL, JSON.stringify(settings, null, 2) + '\n');
  console.log(`✓ Hook wired → ${SETTINGS_LOCAL}`);
} else {
  console.log(`  (already wired in settings.local.json — skipped)`);
}

console.log('\nSetup complete. Reload hooks with /hooks or restart Claude Code.');
