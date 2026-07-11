#!/usr/bin/env node
'use strict';

/*
 * Deterministic PreToolUse guard for repo-sensitive paths:
 * secrets, credentials, database migrations, auth, payment/trading logic,
 * CI/CD deployment workflows, and production config. Invoked by
 * pre-tool-use.sh with the Claude Code PreToolUse JSON payload on stdin.
 *
 * Exit 2 + a reason on stderr blocks the tool call (Claude Code PreToolUse
 * contract). Exit 0 allows it.
 *
 * This is a heuristic, path/command-pattern guard layered on top of the
 * native permissions.deny rules in .claude/settings.json (which already
 * hard-block destructive commands like `rm -rf`, `git reset --hard`). It is
 * not the sole security boundary, so on malformed/unparseable input it
 * fails OPEN (allows the call) rather than blocking every tool call in the
 * session — a parser bug here must not be able to freeze the whole agent.
 * Treat this as defense in depth, not a substitute for reviewing diffs that
 * touch these areas.
 */

const PROTECTED_AREAS = [
  {
    label: 'secrets/credentials',
    re: /(^|[\\/])(\.env(\..+)?|[^\\/]*\.pem|[^\\/]*\.key|[^\\/]*credentials[^\\/]*|[^\\/]*service-account[^\\/]*)$/i,
  },
  {
    label: 'CI/CD deployment workflow',
    re: /(^|[\\/])\.github[\\/]workflows[\\/]|(^|[\\/])\.gitlab-ci\.ya?ml$|(^|[\\/])Jenkinsfile$|(^|[\\/])azure-pipelines\.ya?ml$|(^|[\\/])\.circleci[\\/]/i,
  },
  {
    label: 'database migration',
    re: /(^|[\\/])(migrations|db[\\/]migrate|alembic[\\/]versions)[\\/]/i,
  },
  {
    label: 'authentication/authorization',
    re: /(^|[\\/])(auth|authn|authz|authentication|authorization)[\\/]/i,
  },
  {
    label: 'payment/trading logic',
    re: /(^|[\\/])(payments?|billing|trading)[\\/]/i,
  },
  {
    label: 'production configuration',
    re: /(^|[\\/])(production|prod)[._-][^\\/]*\.(json|ya?ml|env|conf|toml)$|(^|[\\/])config[\\/](production|prod)\./i,
  },
];

// `(?!&)` excludes fd-duplication redirections (`2>&1`, `1>&2`, `>&2`), which
// duplicate a stream and never write to a file, from the "mutating" trigger.
// A real file-write redirect (`>file`, `>>file`, `&>file`) is unaffected.
const MUTATING_BASH_TOKEN = /(^|[;&|]\s*)(rm|mv|cp|sed\s+-i|tee|truncate|dd)\b|>>?(?!=)(?!&)/;

function matchProtectedArea(targetPath) {
  if (typeof targetPath !== 'string' || !targetPath) return null;
  const normalized = targetPath.replace(/\\/g, '/');
  for (const area of PROTECTED_AREAS) {
    if (area.re.test(normalized)) return area.label;
  }
  return null;
}

function readStdinJson() {
  try {
    const fs = require('fs');
    const raw = fs.readFileSync(0, 'utf8');
    if (!raw || !raw.trim()) return null;
    return JSON.parse(raw);
  } catch (_) {
    return null;
  }
}

function checkFileTool(toolInput) {
  const candidate = toolInput.file_path || toolInput.path || toolInput.notebook_path;
  return matchProtectedArea(candidate);
}

function checkBashTool(toolInput) {
  const cmd = toolInput.command;
  if (typeof cmd !== 'string' || !cmd.trim()) return null;
  if (!MUTATING_BASH_TOKEN.test(cmd)) return null;
  // Test whitespace-delimited tokens (not the raw command string) so a
  // protected path is recognized regardless of where it falls in the
  // command — matchProtectedArea anchors on token start/`/` and `$`, which
  // only lines up against a single path-shaped token, not a full sentence.
  const tokens = cmd.split(/\s+/);
  for (const token of tokens) {
    const cleaned = token.replace(/^[>|]+/, '').replace(/^['"]|['"]$/g, '');
    const hit = matchProtectedArea(cleaned);
    if (hit) return hit;
  }
  return null;
}

function main() {
  const payload = readStdinJson();
  if (!payload || typeof payload !== 'object') {
    // Can't determine what's being called — fail open, see header note.
    process.exit(0);
  }

  const toolName = payload.tool_name;
  const toolInput = payload.tool_input && typeof payload.tool_input === 'object' ? payload.tool_input : {};

  let hit = null;
  if (toolName === 'Write' || toolName === 'Edit' || toolName === 'NotebookEdit') {
    hit = checkFileTool(toolInput);
  } else if (toolName === 'Bash') {
    hit = checkBashTool(toolInput);
  }

  if (hit) {
    process.stderr.write(
      `Blocked: this ${toolName} call targets a Protected Area (${hit}) declared in CLAUDE.md. ` +
        `Per the repository constitution, Tier 1 changes to Protected Areas require explicit human ` +
        `approval before apply. If this change is approved, ask the user to confirm explicitly, then retry.\n`
    );
    process.exit(2);
  }

  process.exit(0);
}

main();
