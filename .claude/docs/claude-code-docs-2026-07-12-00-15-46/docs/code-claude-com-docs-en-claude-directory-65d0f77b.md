---
title: "Explore the .claude directory - Claude Code Docs"
source_url: "https://code.claude.com/docs/en/claude-directory"
host: "code.claude.com"
depth: 1
selector: "article,main,[role=main]"
fetched_at: "2026-07-12T00:15:32.586Z"
---
Claude Code reads instructions, settings, skills, subagents, and memory from your project directory and from `~/.claude` in your home directory. Commit project files to git to share them with your team; files in `~/.claude` are personal configuration that applies across all your projects. On Windows, `~/.claude` resolves to `%USERPROFILE%\.claude`. If you set [`CLAUDE_CONFIG_DIR`](https://code.claude.com/docs/en/env-vars), every `~/.claude` path on this page lives under that directory instead. Most users only edit `CLAUDE.md` and `settings.json`. The rest of the directory is optional: add skills, rules, or subagents as you need them.

##

[​

](https://code.claude.com/docs/en/claude-directory#explore-the-directory)

Explore the directory

Click files in the tree to see what each one does, when it loads, and an example.

##

[​

](https://code.claude.com/docs/en/claude-directory#what%E2%80%99s-not-shown)

What’s not shown

The explorer covers files you author and edit. A few related files live elsewhere:

| File | Location | Purpose |
| --- | --- | --- |
| `managed-settings.json` | System-level, varies by OS | Enterprise-enforced settings that you can’t override. See [server-managed settings](https://code.claude.com/docs/en/server-managed-settings). |
| `CLAUDE.local.md` | Project root | Your private preferences for this project, loaded alongside CLAUDE.md. Create it manually and add it to `.gitignore`. |
| Installed plugins | `~/.claude/plugins` | Cloned marketplaces, installed plugin versions, and per-plugin data, managed by `claude plugin` commands. Orphaned versions are deleted 7 days after a plugin update or uninstall. See [plugin caching](https://code.claude.com/docs/en/plugins-reference#plugin-caching-and-file-resolution). |

`~/.claude` also holds data Claude Code writes as you work: transcripts, prompt history, file snapshots, caches, and logs. See [application data](https://code.claude.com/docs/en/claude-directory#application-data) below.

##

[​

](https://code.claude.com/docs/en/claude-directory#choose-the-right-file)

Choose the right file

Different kinds of customization live in different files. Use this table to find where a change belongs.

| You want to | Edit | Scope | Reference |
| --- | --- | --- | --- |
| Give Claude project context and conventions | `CLAUDE.md` | project or global | [Memory](https://code.claude.com/docs/en/memory) |
| Allow or block specific tool calls | `settings.json` `permissions` or `hooks` | project or global | [Permissions](https://code.claude.com/docs/en/permissions), [Hooks](https://code.claude.com/docs/en/hooks) |
| Run a script before or after tool calls | `settings.json` `hooks` | project or global | [Hooks](https://code.claude.com/docs/en/hooks) |
| Set environment variables for the session | `settings.json` `env` | project or global | [Settings](https://code.claude.com/docs/en/settings#available-settings) |
| Keep personal overrides out of git | `settings.local.json` | project only | [Settings scopes](https://code.claude.com/docs/en/settings#settings-files) |
| Add a prompt or capability you invoke with `/name` | `skills/<name>/SKILL.md` | project or global | [Skills](https://code.claude.com/docs/en/skills) |
| Define a specialized subagent with its own tools | `agents/*.md` | project or global | [Subagents](https://code.claude.com/docs/en/sub-agents) |
| Orchestrate many subagents from a script | `workflows/*.js` | project or global | [Dynamic workflows](https://code.claude.com/docs/en/workflows) |
| Connect external tools over MCP | `.mcp.json` | project only | [MCP](https://code.claude.com/docs/en/mcp) |
| Change how Claude formats responses | `output-styles/*.md` | project or global | [Output styles](https://code.claude.com/docs/en/output-styles) |

##

[​

](https://code.claude.com/docs/en/claude-directory#file-reference)

File reference

This table lists every file the explorer covers. Project-scope files live in your repo under `.claude/` (or at the root for `CLAUDE.md`, `.mcp.json`, and `.worktreeinclude`). Global-scope files live in `~/.claude/` and apply across all projects.

Several things can override what you put in these files:

-   [Managed settings](https://code.claude.com/docs/en/server-managed-settings) deployed by your organization take precedence over everything
-   CLI flags like `--permission-mode` or `--settings` override `settings.json` for that session
-   Some environment variables take precedence over their equivalent setting, but this varies: check the [environment variables reference](https://code.claude.com/docs/en/env-vars) for each one

See [settings precedence](https://code.claude.com/docs/en/settings#settings-precedence) for the full order.

Click a filename to open that node in the explorer above.

| File | Scope | Commit | What it does | Reference |
| --- | --- | --- | --- | --- |
| [`CLAUDE.md`](https://code.claude.com/docs/en/claude-directory#ce-claude-md) | Project and global | ✓ | Instructions loaded every session | [Memory](https://code.claude.com/docs/en/memory) |
| [`rules/*.md`](https://code.claude.com/docs/en/claude-directory#ce-rules) | Project and global | ✓ | Topic-scoped instructions, optionally path-gated | [Rules](https://code.claude.com/docs/en/memory#organize-rules-with-claude/rules/) |
| [`settings.json`](https://code.claude.com/docs/en/claude-directory#ce-settings-json) | Project and global | ✓ | Permissions, hooks, env vars, model defaults | [Settings](https://code.claude.com/docs/en/settings) |
| [`settings.local.json`](https://code.claude.com/docs/en/claude-directory#ce-settings-local-json) | Project only |  | Your personal overrides, gitignored when Claude Code creates it | [Settings scopes](https://code.claude.com/docs/en/settings#settings-files) |
| [`.mcp.json`](https://code.claude.com/docs/en/claude-directory#ce-mcp-json) | Project only | ✓ | Team-shared MCP servers | [MCP scopes](https://code.claude.com/docs/en/mcp#mcp-installation-scopes) |
| [`.worktreeinclude`](https://code.claude.com/docs/en/claude-directory#ce-worktreeinclude) | Project only | ✓ | Gitignored files to copy into new worktrees | [Worktrees](https://code.claude.com/docs/en/worktrees#copy-gitignored-files-into-worktrees) |
| [`skills/<name>/SKILL.md`](https://code.claude.com/docs/en/claude-directory#ce-skills) | Project and global | ✓ | Reusable prompts invoked with `/name` or auto-invoked | [Skills](https://code.claude.com/docs/en/skills) |
| [`commands/*.md`](https://code.claude.com/docs/en/claude-directory#ce-commands) | Project and global | ✓ | Single-file prompts; same mechanism as skills | [Skills](https://code.claude.com/docs/en/skills) |
| [`output-styles/*.md`](https://code.claude.com/docs/en/claude-directory#ce-output-styles) | Project and global | ✓ | Custom system-prompt sections | [Output styles](https://code.claude.com/docs/en/output-styles) |
| [`agents/*.md`](https://code.claude.com/docs/en/claude-directory#ce-agents) | Project and global | ✓ | Subagent definitions with their own prompt and tools | [Subagents](https://code.claude.com/docs/en/sub-agents) |
| [`workflows/*.js`](https://code.claude.com/docs/en/claude-directory#ce-workflows) | Project and global | ✓ | Dynamic workflow scripts written by Claude and saved from `/workflows`; each file becomes a `/<name>` command | [Dynamic workflows](https://code.claude.com/docs/en/workflows) |
| [`agent-memory/<name>/`](https://code.claude.com/docs/en/claude-directory#ce-agent-memory) | Project and global | ✓ | Persistent memory for subagents | [Persistent memory](https://code.claude.com/docs/en/sub-agents#enable-persistent-memory) |
| [`~/.claude.json`](https://code.claude.com/docs/en/claude-directory#ce-claude-json) | Global only |  | App state, OAuth, UI toggles, personal MCP servers | [Global config](https://code.claude.com/docs/en/settings#global-config-settings) |
| [`projects/<project>/memory/`](https://code.claude.com/docs/en/claude-directory#ce-global-projects) | Global only |  | Auto memory: Claude’s notes to itself across sessions | [Auto memory](https://code.claude.com/docs/en/memory#auto-memory) |
| [`keybindings.json`](https://code.claude.com/docs/en/claude-directory#ce-keybindings) | Global only |  | Custom keyboard shortcuts | [Keybindings](https://code.claude.com/docs/en/keybindings) |
| [`themes/*.json`](https://code.claude.com/docs/en/claude-directory#ce-themes) | Global only |  | Custom color themes | [Custom themes](https://code.claude.com/docs/en/terminal-config#create-a-custom-theme) |

##

[​

](https://code.claude.com/docs/en/claude-directory#troubleshoot-configuration)

Troubleshoot configuration

If a setting, hook, or file isn’t taking effect, see [Debug your configuration](https://code.claude.com/docs/en/debug-your-config) for the inspection commands and a symptom-first lookup table.

##

[​

](https://code.claude.com/docs/en/claude-directory#application-data)

Application data

Beyond the config you author, `~/.claude` holds data Claude Code writes during sessions. These files are plaintext. Anything that passes through a tool lands in a transcript on disk: file contents, command output, pasted text.

###

[​

](https://code.claude.com/docs/en/claude-directory#cleaned-up-automatically)

Cleaned up automatically

Files in the paths below are deleted on startup once they’re older than [`cleanupPeriodDays`](https://code.claude.com/docs/en/settings#available-settings). The default is 30 days.

| Path under `~/.claude/` | Contents |
| --- | --- |
| `projects/<project>/<session>.jsonl` | Full conversation transcript: every message, tool call, and tool result |
| `projects/<project>/<session>/subagents/` | [Subagent](https://code.claude.com/docs/en/sub-agents) conversation transcripts, removed with the parent session transcript when it ages out |
| `projects/<project>/<session>/tool-results/` | Large tool outputs spilled to separate files |
| `file-history/<session>/` | Pre-edit snapshots of files Claude changed, used for [checkpoint restore](https://code.claude.com/docs/en/checkpointing) |
| `plans/` | Plan files written during [plan mode](https://code.claude.com/docs/en/permission-modes#analyze-before-you-edit-with-plan-mode) |
| `debug/` | Per-session debug logs, written only when you start with `--debug` or run `/debug` |
| `paste-cache/`, `image-cache/` | Contents of large pastes and attached images |
| `session-env/` | Per-session environment metadata |
| `tasks/` | Per-session task lists written by the task tools |
| `shell-snapshots/` | Captured shell environment used by the Bash tool. Removed on clean exit. The sweep clears any left after a crash. |
| `backups/` | Timestamped copies of `~/.claude.json` taken before config migrations |
| `feedback-bundles/` | Redacted transcript archives written by `/feedback` on third-party providers, for sending to your Anthropic account team |
| `todos/`, `statsig/`, `logs/` | Legacy directories from older versions. No longer written. The sweep removes their contents and then the empty directory. |

###

[​

](https://code.claude.com/docs/en/claude-directory#kept-until-you-delete-them)

Kept until you delete them

The following paths are not covered by automatic cleanup and persist indefinitely.

| Path under `~/.claude/` | Contents |
| --- | --- |
| `history.jsonl` | Every prompt you’ve typed, with timestamp and project path. Used for up-arrow recall. |
| `stats-cache.json` | Aggregated token and cost counts shown by `/usage` |
| `remote-settings.json` | Cached copy of [server-managed settings](https://code.claude.com/docs/en/server-managed-settings) for your organization. Only present when your organization has configured them. Refreshed on each launch. |

Other small cache and lock files appear depending on which features you use and are safe to delete.

###

[​

](https://code.claude.com/docs/en/claude-directory#plaintext-storage)

Plaintext storage

Transcripts and history are not encrypted at rest. OS file permissions are the only protection. If a tool reads a `.env` file or a command prints a credential, that value is written to `projects/<project>/<session>.jsonl`. To reduce exposure:

-   Lower `cleanupPeriodDays` to shorten how long transcripts are kept
-   Set the [`CLAUDE_CODE_SKIP_PROMPT_HISTORY`](https://code.claude.com/docs/en/env-vars) environment variable to skip writing transcripts and prompt history in any mode. In non-interactive mode, you can instead pass `--no-session-persistence` alongside `-p`, or set `persistSession: false` in the Agent SDK.
-   Use [permission rules](https://code.claude.com/docs/en/permissions) to deny reads of credential files

###

[​

](https://code.claude.com/docs/en/claude-directory#clear-local-data)

Clear local data

Run `claude project purge` to delete the state Claude Code holds for one project. The command requires Claude Code v2.1.124 or later. It deletes:

-   Transcripts and auto memory under `projects/`
-   Per-session `tasks/`, `debug/`, and `file-history/` entries
-   Matching prompt lines in `history.jsonl`
-   The project’s entry in `~/.claude.json`

The command prints the full deletion plan and asks for confirmation before removing anything. Preview the plan without deleting anything:

```
claude project purge ~/work/my-repo --dry-run
```

Delete with a single confirmation prompt:

```
claude project purge ~/work/my-repo
```

Omit the path to pick a project from an interactive list. Skip the confirmation prompt for use in scripts:

```
claude project purge ~/work/my-repo --yes
```

Pass `--all` instead of a path to purge state for every project at once, which deletes `history.jsonl` outright rather than filtering it. Pass `-i` to step through the deletion plan one item at a time. The command leaves `shell-snapshots/` and `backups/` alone because those are not project-scoped, and warns about them in the plan output. It exits with status 1 if no state matches the given path. You can also delete any of the application-data paths above by hand. New sessions are unaffected. The table below shows what you lose for past sessions.

| Delete | You lose |
| --- | --- |
| `~/.claude/projects/` | Resume, continue, and rewind for past sessions |
| `~/.claude/history.jsonl` | Up-arrow prompt recall |
| `~/.claude/file-history/` | Checkpoint restore for past sessions |
| `~/.claude/stats-cache.json` | Historical totals shown by `/usage` |
| `~/.claude/remote-settings.json` | Nothing. Re-fetched on next launch. |
| `~/.claude/debug/`, `~/.claude/plans/`, `~/.claude/paste-cache/`, `~/.claude/image-cache/`, `~/.claude/session-env/`, `~/.claude/tasks/`, `~/.claude/shell-snapshots/`, `~/.claude/backups/` | Nothing user-facing |
| `~/.claude/todos/`, `~/.claude/statsig/`, `~/.claude/logs/` | Nothing. Legacy directories not written by current versions. |

Don’t delete `~/.claude.json`, `~/.claude/settings.json`, or `~/.claude/plugins/`: those hold your auth, preferences, and installed plugins.

##

[​

](https://code.claude.com/docs/en/claude-directory#related-resources)

Related resources

-   [Manage Claude’s memory](https://code.claude.com/docs/en/memory): write and organize CLAUDE.md, rules, and auto memory
-   [Configure settings](https://code.claude.com/docs/en/settings): set permissions, hooks, environment variables, and model defaults
-   [Create skills](https://code.claude.com/docs/en/skills): build reusable prompts and workflows
-   [Configure subagents](https://code.claude.com/docs/en/sub-agents): define specialized agents with their own context

Was this page helpful?

YesNo

[Extend Claude Code](https://code.claude.com/docs/en/features-overview)[Explore the context window](https://code.claude.com/docs/en/context-window)

⌘I
