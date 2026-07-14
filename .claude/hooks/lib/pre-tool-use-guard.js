#!/usr/bin/env node
'use strict';

/*
 * Deterministic PreToolUse guard (Phase 6A determinism-ladder rung 4).
 * Invoked by pre-tool-use.sh with the Claude Code PreToolUse JSON payload
 * on stdin. Covers:
 *   - Protected-path file/command matching (secrets, CI/CD, migrations,
 *     auth, payment/trading, production config, the append-only ledger,
 *     lockfiles) -> `block` (exit 2) or `ask` (native permission prompt)
 *     depending on category severity.
 *   - Git guardrails: force push, remote ref deletion, hard reset, clean,
 *     force branch delete, history rewrites -> `ask`, so Claude Code
 *     surfaces the native interactive approval prompt to the real user
 *     (rung 4 hands off to the human; it does not invent its own approval
 *     channel). settings.json's `permissions.deny` (rung 5, unconditional,
 *     no override) already hard-blocks the most common literal spellings;
 *     this guard's job is the bypass variants a simple string-prefix deny
 *     rule misses: `-f` shorthand, `--force-with-lease`, compound/quoted
 *     commands, env-var-prefixed invocations.
 *   - Path traversal (`..` segments) -> `block`, unconditionally, since a
 *     relative escape attempt has no legitimate case in this guard's scope.
 *
 * Every decision (allow/ask/block/error) is logged as one JSONL line to
 * `.claude/state/logs/guardrail-events.jsonl` with a correlation id and
 * processing latency, per the Phase 6A measurement requirement.
 *
 * This is a heuristic, path/command-pattern guard layered on top of native
 * permissions.deny rules. It is not the sole security boundary, so on
 * malformed/unparseable input it fails OPEN (allows the call) rather than
 * blocking every tool call in the session — a parser bug here must not be
 * able to freeze the whole agent. Treat this as defense in depth, not a
 * substitute for reviewing diffs that touch these areas. The secrets-path
 * regex is intentionally over-broad (it will also flag a benign filename
 * like `credentials-policy.md`) — this is a deliberate fail-closed choice,
 * documented as a probabilistic-precision / deterministic-recall tradeoff;
 * repeated blocks on the same benign path are the false-block-review signal
 * `phase6a_metrics.py` surfaces for a rung-4 refinement (never silently
 * loosened here).
 */

const fs = require('fs');
const path = require('path');
const crypto = require('crypto');

const ROOT = path.resolve(__dirname, '..', '..', '..');
const LOG_DIR = path.join(ROOT, '.claude', 'state', 'logs');
const EVENT_LOG = path.join(LOG_DIR, 'guardrail-events.jsonl');

const PROTECTED_AREAS = [
  {
    label: 'secrets/credentials',
    severity: 'block',
    re: /(^|[\\/])(\.env(\..+)?|[^\\/]*\.pem|[^\\/]*\.key|[^\\/]*credentials[^\\/]*|[^\\/]*service-account[^\\/]*)$/i,
  },
  {
    label: 'GitHub governance path',
    severity: 'block',
    re: /(^|[\\/])\.github[\\/]/i,
  },
  {
    label: 'security policy file',
    severity: 'block',
    re: /(^|[\\/])SECURITY\.md$/i,
  },
  {
    label: 'control-plane rule',
    severity: 'block',
    re: /(^|[\\/])\.claude[\\/]rules[\\/]/i,
  },
  {
    label: 'CI/CD deployment workflow',
    severity: 'block',
    re: /(^|[\\/])\.gitlab-ci\.ya?ml$|(^|[\\/])Jenkinsfile$|(^|[\\/])azure-pipelines\.ya?ml$|(^|[\\/])\.circleci[\\/]/i,
  },
  {
    label: 'database migration',
    severity: 'block',
    re: /(^|[\\/])(migrations|db[\\/]migrate|alembic[\\/]versions)[\\/]/i,
  },
  {
    label: 'authentication/authorization',
    severity: 'block',
    re: /(^|[\\/])(auth|authn|authz|authentication|authorization)[\\/]/i,
  },
  {
    label: 'payment/trading logic',
    severity: 'block',
    re: /(^|[\\/])(payments?|billing|trading)[\\/]/i,
  },
  {
    label: 'production configuration',
    severity: 'block',
    re: /(^|[\\/])(production|prod)[._-][^\\/]*\.(json|ya?ml|env|conf|toml)$|(^|[\\/])config[\\/](production|prod)\./i,
  },
  {
    label: 'append-only ledger',
    severity: 'block',
    re: /(^|[\\/])\.claude[\\/]state[\\/]ledger\.md$/i,
  },
  {
    label: 'lockfile mass-edit',
    severity: 'ask',
    re: /(^|[\\/])(package-lock\.json|yarn\.lock|pnpm-lock\.ya?ml|Cargo\.lock|poetry\.lock|Gemfile\.lock|composer\.lock)$/i,
  },
];

// `(?!&)` excludes fd-duplication redirections (`2>&1`, `1>&2`, `>&2`), which
// duplicate a stream and never write to a file, from the "mutating" trigger.
// A real file-write redirect (`>file`, `>>file`, `&>file`) is unaffected.
// This carve-out is itself a recorded Phase 6 ladder refinement: an earlier
// version of this rung-4 rule blocked legitimate stderr-redirect commands
// twice before the exclusion was added (see `.claude/state/ledger.md`).
const MUTATING_BASH_TOKEN = /(^|[;&|]\s*)(rm|mv|cp|sed\s+-i|tee|truncate|dd)\b|>>?(?!=)(?!&)/;

const GIT_DESTRUCTIVE_RULES = [
  {
    id: 'git-force-push',
    severity: 'ask',
    test: (tokens) =>
      hasSubcommand(tokens, 'push') &&
      tokens.some((t) => t === '-f' || t === '--force' || t.startsWith('--force-with-lease')),
  },
  {
    id: 'git-remote-ref-delete',
    severity: 'ask',
    test: (tokens) =>
      hasSubcommand(tokens, 'push') &&
      (tokens.includes('--delete') ||
        tokens.some((t) => t.startsWith(':') && t.length > 1)),
  },
  {
    id: 'git-reset-hard',
    severity: 'ask',
    test: (tokens) => hasSubcommand(tokens, 'reset') && tokens.includes('--hard'),
  },
  {
    id: 'git-clean-force',
    severity: 'ask',
    test: (tokens) =>
      hasSubcommand(tokens, 'clean') && tokens.some((t) => /^-[a-z]*f[a-z]*$/i.test(t) || t === '--force'),
  },
  {
    id: 'git-branch-force-delete',
    severity: 'ask',
    test: (tokens) => hasSubcommand(tokens, 'branch') && tokens.includes('-D'),
  },
  {
    id: 'git-tag-delete',
    severity: 'ask',
    test: (tokens) => hasSubcommand(tokens, 'tag') && (tokens.includes('-d') || tokens.includes('--delete')),
  },
  {
    id: 'git-history-rewrite',
    severity: 'ask',
    test: (tokens) =>
      hasSubcommand(tokens, 'filter-branch') ||
      hasSubcommand(tokens, 'filter-repo') ||
      (hasSubcommand(tokens, 'rebase') && !tokens.includes('--abort') && !tokens.includes('--continue')),
  },
  {
    id: 'git-stash-destroy',
    severity: 'ask',
    test: (tokens) => hasSubcommand(tokens, 'stash') && (tokens.includes('drop') || tokens.includes('clear')),
  },
  {
    id: 'git-reflog-expire',
    severity: 'ask',
    test: (tokens) => hasSubcommand(tokens, 'reflog') && tokens.includes('expire'),
  },
];

function hasSubcommand(tokens, name) {
  return tokens[0] === 'git' && tokens.slice(1).includes(name);
}

function matchProtectedArea(targetPath) {
  if (typeof targetPath !== 'string' || !targetPath) return null;
  const normalized = targetPath.replace(/\\/g, '/');
  for (const area of PROTECTED_AREAS) {
    if (area.re.test(normalized)) return area;
  }
  return null;
}

function isPathTraversal(targetPath) {
  if (typeof targetPath !== 'string' || !targetPath) return false;
  const normalized = targetPath.replace(/\\/g, '/');
  return normalized.split('/').includes('..');
}

function readStdinJson() {
  try {
    const raw = fs.readFileSync(0, 'utf8');
    if (!raw || !raw.trim()) return { payload: null, error: null };
    return { payload: JSON.parse(raw), error: null };
  } catch (err) {
    return { payload: null, error: err && err.message ? err.message : 'unreadable stdin' };
  }
}

// Conservative shell tokenizer: splits on top-level `&&`, `||`, `;`, `|`
// (not inside quotes), then whitespace-splits each segment (quotes
// stripped). This is intentionally conservative — it is used only to
// *detect* destructive git subcommands, never to execute anything, so
// over-splitting toward more scrutiny is the safe failure direction.
function splitCommandSegments(command) {
  const segments = [];
  let current = '';
  let quote = null;
  for (let i = 0; i < command.length; i += 1) {
    const ch = command[i];
    if (quote) {
      current += ch;
      if (ch === quote) quote = null;
      continue;
    }
    if (ch === '"' || ch === "'") {
      quote = ch;
      current += ch;
      continue;
    }
    if (ch === '&' && command[i + 1] === '&') {
      segments.push(current);
      current = '';
      i += 1;
      continue;
    }
    if (ch === '|' && command[i + 1] === '|') {
      segments.push(current);
      current = '';
      i += 1;
      continue;
    }
    if (ch === ';' || ch === '|' || ch === '\n') {
      segments.push(current);
      current = '';
      continue;
    }
    current += ch;
  }
  segments.push(current);
  return segments.map((s) => s.trim()).filter(Boolean);
}

function tokenize(segment) {
  const tokens = [];
  let current = '';
  let quote = null;
  for (let i = 0; i < segment.length; i += 1) {
    const ch = segment[i];
    if (quote) {
      if (ch === quote) {
        quote = null;
      } else {
        current += ch;
      }
      continue;
    }
    if (ch === '"' || ch === "'") {
      quote = ch;
      continue;
    }
    if (/\s/.test(ch)) {
      if (current) tokens.push(current);
      current = '';
      continue;
    }
    current += ch;
  }
  if (current) tokens.push(current);
  return tokens;
}

// Strips leading `VAR=value` environment-variable assignments and common
// invocation wrappers (`sudo`, `command`, `exec`) so `GIT_TRACE=1 git push
// -f` and `sudo git push -f` are still recognized as `git push -f`.
function normalizeLeadingTokens(tokens) {
  let out = tokens.slice();
  let changed = true;
  while (changed) {
    changed = false;
    if (out.length && /^[A-Za-z_][A-Za-z0-9_]*=/.test(out[0])) {
      out = out.slice(1);
      changed = true;
      continue;
    }
    if (out.length && (out[0] === 'sudo' || out[0] === 'command' || out[0] === 'exec')) {
      out = out.slice(1);
      changed = true;
    }
  }
  return out;
}

function checkGitGuardrails(command) {
  if (typeof command !== 'string' || !command.trim()) return null;
  for (const rawSegment of splitCommandSegments(command)) {
    const tokens = normalizeLeadingTokens(tokenize(rawSegment));
    if (tokens[0] !== 'git') continue;
    for (const rule of GIT_DESTRUCTIVE_RULES) {
      if (rule.test(tokens)) {
        return { label: `git guardrail: ${rule.id}`, severity: rule.severity };
      }
    }
  }
  return null;
}

function checkFileTool(toolInput) {
  const candidate = toolInput.file_path || toolInput.path || toolInput.notebook_path;
  if (isPathTraversal(candidate)) {
    return { label: 'path traversal', severity: 'block' };
  }
  return matchProtectedArea(candidate);
}

function checkBashTool(toolInput) {
  const cmd = toolInput.command;
  if (typeof cmd !== 'string' || !cmd.trim()) return null;

  const gitHit = checkGitGuardrails(cmd);
  if (gitHit) return gitHit;

  if (!MUTATING_BASH_TOKEN.test(cmd)) return null;
  // Test whitespace-delimited tokens (not the raw command string) so a
  // protected path is recognized regardless of where it falls in the
  // command — matchProtectedArea anchors on token start/`/` and `$`, which
  // only lines up against a single path-shaped token, not a full sentence.
  const tokens = cmd.split(/\s+/);
  for (const token of tokens) {
    const cleaned = token.replace(/^[>|]+/, '').replace(/^['"]|['"]$/g, '');
    if (isPathTraversal(cleaned)) {
      return { label: 'path traversal', severity: 'block' };
    }
    const hit = matchProtectedArea(cleaned);
    if (hit) return hit;
  }
  return null;
}

function logEvent(event) {
  try {
    fs.mkdirSync(LOG_DIR, { recursive: true });
    fs.appendFileSync(EVENT_LOG, JSON.stringify(event) + '\n', 'utf8');
  } catch (_) {
    // Logging must never block or crash the guard.
  }
}

function main() {
  const start = Date.now();
  const correlationId = crypto.randomUUID();
  const { payload, error } = readStdinJson();

  if (error || !payload || typeof payload !== 'object') {
    logEvent({
      ts: new Date().toISOString(),
      correlation_id: correlationId,
      tool_name: null,
      decision: 'error',
      category: null,
      reason: error || 'empty or non-object payload',
      duration_ms: Date.now() - start,
    });
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

  if (!hit) {
    logEvent({
      ts: new Date().toISOString(),
      correlation_id: correlationId,
      tool_name: toolName || null,
      decision: 'allow',
      category: null,
      reason: null,
      duration_ms: Date.now() - start,
    });
    process.exit(0);
  }

  if (hit.severity === 'ask') {
    const reason =
      `This ${toolName} call matches ${hit.label}, a Phase 6A determinism-ladder rung-4 guardrail. ` +
      `Requires explicit human approval before proceeding.`;
    logEvent({
      ts: new Date().toISOString(),
      correlation_id: correlationId,
      tool_name: toolName,
      decision: 'ask',
      category: hit.label,
      reason,
      duration_ms: Date.now() - start,
    });
    process.stdout.write(
      JSON.stringify({
        hookSpecificOutput: {
          hookEventName: 'PreToolUse',
          permissionDecision: 'ask',
          permissionDecisionReason: reason,
        },
      })
    );
    process.exit(0);
  }

  const reason = `Blocked: this ${toolName} call targets ${hit.label}. Halt immediately on this first protected-area block; do not retry with another tool, path spelling, shell redirection, or workaround. Per the repository constitution, this requires explicit human approval before apply.`;
  logEvent({
    ts: new Date().toISOString(),
    correlation_id: correlationId,
    tool_name: toolName,
    decision: 'block',
    category: hit.label,
    reason,
    duration_ms: Date.now() - start,
  });
  process.stderr.write(reason + '\n');
  process.exit(2);
}

main();
