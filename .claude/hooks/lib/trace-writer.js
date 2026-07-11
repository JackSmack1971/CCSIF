#!/usr/bin/env node
'use strict';

/*
 * Best-effort trace writer for the `self-improve` skill.
 * Invoked by post-tool-use.sh (PostToolUse) and stop.sh (Stop) with the
 * Claude Code hook JSON payload on stdin. Never throws past main() and
 * never exits non-zero — tracing must not block the tool call or session
 * it is observing. Schema written matches
 * .claude/skills/self-improve/references/input-discovery.md section 4.
 */

const fs = require('fs');
const path = require('path');

const SECRET_PATTERNS = [
  /(api[_-]?key|secret|token|password|passwd|authoriz(?:ation)?)\s*[:=]\s*['"]?[A-Za-z0-9_\-.\/+=]{6,}['"]?/gi,
  /sk-[A-Za-z0-9]{10,}/g,
  /gh[pousr]_[A-Za-z0-9]{20,}/g,
  /AKIA[0-9A-Z]{16}/g,
  /Bearer\s+[A-Za-z0-9\-_.]{10,}/gi,
];

function redact(str) {
  if (typeof str !== 'string') return str;
  let out = str;
  for (const pattern of SECRET_PATTERNS) {
    out = out.replace(pattern, '<redacted>');
  }
  return out;
}

function truncate(str, max) {
  if (typeof str !== 'string') return str;
  if (str.length <= max) return str;
  return str.slice(0, max) + '…(truncated)';
}

function safeText(value, max) {
  if (value === null || value === undefined) return null;
  const s = typeof value === 'string' ? value : JSON.stringify(value);
  return truncate(redact(s), max);
}

function commandGist(cmd) {
  if (typeof cmd !== 'string' || !cmd.trim()) return null;
  return truncate(redact(cmd), 120);
}

function isEnvDumpCommand(cmd) {
  if (typeof cmd !== 'string') return false;
  const trimmed = cmd.trim();
  const firstToken = trimmed.split(/\s+/)[0] || '';
  if (firstToken === 'env' || firstToken === 'printenv') return true;
  if ((firstToken === 'set' || firstToken === 'export') && trimmed === firstToken) return true;
  return false;
}

function readStdinJson() {
  try {
    const raw = fs.readFileSync(0, 'utf8');
    if (!raw || !raw.trim()) return null;
    return JSON.parse(raw);
  } catch (_) {
    return null;
  }
}

// Bounded read of only the tail of the transcript — sessions can be long-running
// and this runs on every tool call, so never read the whole file.
function tailLines(transcriptPath, maxBytes) {
  maxBytes = maxBytes || 65536;
  let fd;
  try {
    const stat = fs.statSync(transcriptPath);
    const size = stat.size;
    const start = size > maxBytes ? size - maxBytes : 0;
    const length = size - start;
    const buf = Buffer.alloc(length);
    fd = fs.openSync(transcriptPath, 'r');
    fs.readSync(fd, buf, 0, length, start);
    fs.closeSync(fd);
    let text = buf.toString('utf8');
    if (start > 0) {
      // We started mid-file: drop the partial first line.
      const idx = text.indexOf('\n');
      text = idx >= 0 ? text.slice(idx + 1) : '';
    }
    const rawLines = text.split('\n').filter(Boolean);
    const parsed = [];
    for (const line of rawLines) {
      try {
        parsed.push(JSON.parse(line));
      } catch (_) {
        // Skip unparsable lines silently — tolerate schema/format divergence.
      }
    }
    return parsed;
  } catch (_) {
    try {
      if (fd !== undefined) fs.closeSync(fd);
    } catch (_) {
      // ignore
    }
    return [];
  }
}

// Scan backward for the most recent genuine human text turn. Claude Code
// transcripts re-inject tool_result blocks under role "user" too, so a
// "user" entry whose content contains a tool_result is NOT a real human
// message and must be skipped rather than misread as the task.
function findLastUserTaskText(lines) {
  for (let i = lines.length - 1; i >= 0; i--) {
    const entry = lines[i];
    const msg = entry && (entry.message || entry);
    if (!msg || msg.role !== 'user') continue;
    const content = msg.content;
    if (typeof content === 'string') {
      const trimmed = content.trim();
      if (trimmed) return trimmed;
      continue;
    }
    if (Array.isArray(content)) {
      const hasToolResult = content.some((b) => b && b.type === 'tool_result');
      if (hasToolResult) continue;
      const text = content
        .filter((b) => b && b.type === 'text' && typeof b.text === 'string')
        .map((b) => b.text)
        .join(' ')
        .trim();
      if (text) return text;
    }
  }
  return null;
}

// Scan backward for the most recent assistant Skill tool_use invocation.
function findLastSkillInvocation(lines) {
  const candidateKeys = ['skill', 'skill_name', 'skillName', 'name'];
  for (let i = lines.length - 1; i >= 0; i--) {
    const entry = lines[i];
    const msg = entry && (entry.message || entry);
    if (!msg || msg.role !== 'assistant') continue;
    const content = msg.content;
    if (!Array.isArray(content)) continue;
    for (const block of content) {
      if (block && block.type === 'tool_use' && block.name === 'Skill') {
        const input = block.input || {};
        for (const key of candidateKeys) {
          if (typeof input[key] === 'string' && input[key].trim()) {
            return input[key].trim();
          }
        }
        return null;
      }
    }
  }
  return null;
}

// Any tool_result in the tail window that looks like a failure — used by
// Stop to decide success vs. partial for the completed task turn.
// Returns { failed, component } — component is the file path implicated by
// the failing tool call (via its matching tool_use block), or null when the
// tool had no path input (e.g. bare Bash), matching deriveComponent's contract.
function findAnyToolFailure(lines, windowSize) {
  windowSize = windowSize || 100;
  const start = Math.max(0, lines.length - windowSize);
  for (let i = lines.length - 1; i >= start; i--) {
    const entry = lines[i];
    const msg = entry && (entry.message || entry);
    if (!msg || msg.role !== 'user') continue;
    const content = msg.content;
    if (!Array.isArray(content)) continue;
    for (const block of content) {
      if (block && block.type === 'tool_result') {
        const text =
          typeof block.content === 'string'
            ? block.content
            : Array.isArray(block.content)
            ? block.content.map((c) => (c && c.text) || '').join(' ')
            : '';
        const failed = block.is_error === true || /error|exception|traceback/i.test(text);
        if (failed) {
          return { failed: true, component: findToolUseComponent(lines, i, block.tool_use_id) };
        }
      }
    }
  }
  return { failed: false, component: null };
}

// Given the index of the failing tool_result entry and its tool_use_id, scan
// backward for the matching assistant tool_use block to attribute a
// file-path component to the failure.
function findToolUseComponent(lines, resultIndex, toolUseId) {
  if (!toolUseId) return null;
  for (let i = resultIndex; i >= 0; i--) {
    const entry = lines[i];
    const msg = entry && (entry.message || entry);
    if (!msg || msg.role !== 'assistant' || !Array.isArray(msg.content)) continue;
    for (const block of msg.content) {
      if (block && block.type === 'tool_use' && block.id === toolUseId) {
        return deriveComponent(block.input, process.cwd());
      }
    }
  }
  return null;
}

// The error|exception|traceback text scan is only a valid failure signal for
// Bash, where stdout is the sole outcome channel. For content-bearing tools
// (Read, Grep, Glob, ...) the response body is the target file's own text,
// and scanning it for those words misclassifies any successful read of a
// file that merely discusses errors (e.g. this skill's own reference docs).
function classifyPostToolOutcome(toolResponse, toolName) {
  try {
    if (toolResponse == null) return 'success';
    if (typeof toolResponse === 'string') {
      if (toolName !== 'Bash') return 'success';
      return /error|exception|traceback/i.test(toolResponse) ? 'failure' : 'success';
    }
    if (typeof toolResponse === 'object') {
      if (toolResponse.error || toolResponse.is_error) return 'failure';
      if (typeof toolResponse.stderr === 'string' && toolResponse.stderr.trim().length > 0) {
        return 'failure';
      }
      if (toolName !== 'Bash') return 'success';
      const bodyText =
        typeof toolResponse.output === 'string'
          ? toolResponse.output
          : typeof toolResponse.content === 'string'
          ? toolResponse.content
          : JSON.stringify(toolResponse);
      if (/error|exception|traceback/i.test(bodyText)) return 'failure';
      return 'success';
    }
  } catch (_) {
    // fall through
  }
  return 'success';
}

// Extract a short, redacted snippet of the actual failure detail (stderr or
// matched error/exception/traceback text) so a `tool_failure` note is
// diagnosable on its own instead of only echoing the input command.
function failureSnippet(toolResponse) {
  try {
    if (toolResponse == null) return null;
    if (typeof toolResponse === 'string') return truncate(redact(toolResponse), 200);
    if (typeof toolResponse === 'object') {
      const text =
        (typeof toolResponse.stderr === 'string' && toolResponse.stderr.trim()) ||
        (typeof toolResponse.output === 'string' && toolResponse.output) ||
        (typeof toolResponse.content === 'string' && toolResponse.content) ||
        '';
      return text ? truncate(redact(text), 200) : null;
    }
  } catch (_) {
    // fall through
  }
  return null;
}

// Best-effort file-path attribution. Never leaks an absolute path outside
// cwd; path-less tools (e.g. bare Bash) yield null, matching the schema's
// "component is a file path" contract.
function deriveComponent(toolInput, cwd) {
  if (!toolInput || typeof toolInput !== 'object') return null;
  const rawPath = toolInput.file_path || toolInput.path || toolInput.notebook_path;
  if (!rawPath || typeof rawPath !== 'string') return null;
  try {
    const rel = path.relative(cwd, rawPath);
    if (!rel || rel.startsWith('..') || path.isAbsolute(rel)) {
      return path.basename(rawPath);
    }
    return rel.split(path.sep).join('/');
  } catch (_) {
    return path.basename(String(rawPath));
  }
}

function buildPostToolUseEntry(payload, facts) {
  const cwd = typeof payload.cwd === 'string' ? payload.cwd : process.cwd();
  const toolName = payload.tool_name || null;
  const toolInput = payload.tool_input || {};
  const toolResponse = payload.tool_response;
  const outcome = classifyPostToolOutcome(toolResponse, toolName);
  const errorClass = outcome === 'failure' ? 'tool_failure' : null;
  const component = deriveComponent(toolInput, cwd);

  let notes;
  if (toolName === 'Bash') {
    const cmd = toolInput.command;
    if (isEnvDumpCommand(cmd)) {
      notes = 'env/secret-listing command; response omitted';
    } else {
      const gist = commandGist(cmd);
      const detail = outcome === 'failure' ? failureSnippet(toolResponse) : null;
      notes = `Bash command (${outcome}): ${gist || '(no command captured)'}${
        detail ? ` | failure detail: ${detail}` : ''
      }`;
    }
  } else {
    notes = `${toolName || 'tool'} call (${outcome})${component ? ' on ' + component : ''}`;
  }

  return {
    ts: new Date().toISOString(),
    task: safeText(facts.taskText, 300),
    skill: facts.skill || null,
    outcome,
    error_class: errorClass,
    component: component ? safeText(component, 200) : null,
    notes: safeText(notes, 400) || 'PostToolUse event',
  };
}

function buildStopEntry(payload, facts) {
  return {
    ts: new Date().toISOString(),
    task: safeText(facts.taskText, 300),
    skill: facts.skill || null,
    outcome: facts.outcome,
    error_class: facts.errorClass,
    component: facts.component ? safeText(facts.component, 200) : null,
    notes: safeText(facts.notes, 400) || 'Stop event summary',
  };
}

function writeEntry(cwd, entry) {
  const dir = path.join(cwd, '.claude', 'traces');
  fs.mkdirSync(dir, { recursive: true });
  const dateStr = new Date().toISOString().slice(0, 10);
  const filePath = path.join(dir, `${dateStr}.jsonl`);
  fs.appendFileSync(filePath, JSON.stringify(entry) + '\n');
}

function main() {
  const payload = readStdinJson();
  if (!payload || typeof payload !== 'object') return;

  const cwd = typeof payload.cwd === 'string' ? payload.cwd : process.cwd();
  const eventName = payload.hook_event_name;
  const lines = typeof payload.transcript_path === 'string' ? tailLines(payload.transcript_path) : [];
  const taskText = findLastUserTaskText(lines);
  const skill = findLastSkillInvocation(lines);

  let entry;
  if (eventName === 'PostToolUse') {
    entry = buildPostToolUseEntry(payload, { taskText, skill });
  } else if (eventName === 'Stop') {
    const failure = findAnyToolFailure(lines);
    entry = buildStopEntry(payload, {
      taskText,
      skill,
      outcome: failure.failed ? 'partial' : 'success',
      errorClass: failure.failed ? 'tool_failure' : null,
      component: failure.component,
      notes: `Task turn completed${skill ? ' via skill ' + skill : ''}${
        failure.failed ? '; at least one tool call failed' : ''
      }.`,
    });
  } else {
    return;
  }

  writeEntry(cwd, entry);
}

try {
  main();
} catch (_) {
  // Fail open: tracing must never surface an error or a non-zero exit.
}
