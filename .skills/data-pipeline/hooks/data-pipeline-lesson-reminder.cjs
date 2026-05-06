#!/usr/bin/env node
/**
 * PostToolUse hook: Remind to record data-pipeline lessons after fix commits.
 *
 * Fires after Bash. Detects `git commit` where the message starts with `fix:`
 * or `fix(`, then injects a reminder to check and append to lessons-learned.md.
 */

try {
  const fs = require('fs');
  const path = require('path');

  const stdin = fs.readFileSync(0, 'utf8');
  const hookData = JSON.parse(stdin || '{}');
  const cmd = (hookData.tool_input || {}).command || '';

  // Only act on git commit commands
  if (!/git\s+commit/.test(cmd)) {
    console.log(JSON.stringify({ continue: true }));
    process.exit(0);
  }

  // Extract commit message from -m flag
  const mMatch = cmd.match(/-m\s+["']([^"']+)["']/);
  const msg = mMatch ? mMatch[1] : '';

  // Only act on fix: commits
  if (!/^fix[\(:]/i.test(msg)) {
    console.log(JSON.stringify({ continue: true }));
    process.exit(0);
  }

  // Find last lesson number from lessons-learned.md
  const cwd = hookData.cwd || process.cwd();
  const lessonsPath = path.join(cwd, '.skills', 'data-pipeline', 'lessons-learned.md');
  let lastLesson = 'unknown';
  try {
    const content = fs.readFileSync(lessonsPath, 'utf8');
    const matches = content.match(/^### (L\d+)/gm);
    if (matches && matches.length > 0) {
      lastLesson = matches[matches.length - 1].replace('### ', '');
    }
  } catch (_) {
    // lessons-learned.md not found or unreadable — still remind
  }

  const reminder = [
    `\n\n📝 **LESSON TRIGGER — fix commit detected**`,
    `Commit: "${msg}"`,
    `Last recorded lesson: ${lastLesson}`,
    ``,
    `→ If the root cause is non-trivial, append a new lesson to \`.skills/data-pipeline/lessons-learned.md\``,
    `→ Use the Self-Learning Protocol format (Symptom / Root cause / Fix / Rules / Reference)`,
    `→ Run: \`grep "^### L" .skills/data-pipeline/lessons-learned.md | tail -5\` to see recent lessons`,
  ].join('\n');

  console.log(JSON.stringify({
    continue: true,
    hookSpecificOutput: {
      hookEventName: 'PostToolUse',
      additionalContext: reminder,
    },
  }));

} catch (e) {
  // Fail-open: never block a commit
  process.exit(0);
}
