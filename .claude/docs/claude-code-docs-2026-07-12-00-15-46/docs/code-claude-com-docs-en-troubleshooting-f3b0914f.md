---
title: "Troubleshooting - Claude Code Docs"
source_url: "https://code.claude.com/docs/en/troubleshooting"
host: "code.claude.com"
depth: 1
selector: "article,main,[role=main]"
fetched_at: "2026-07-12T00:15:40.627Z"
---
This page covers performance, stability, and search problems once Claude Code is running. For other issues, start with the page that matches where you’re stuck:

| Symptom | Go to |
| --- | --- |
| `command not found`, install fails, PATH issues, `EACCES`, TLS errors | [Troubleshoot installation and login](https://code.claude.com/docs/en/troubleshoot-install) |
| Update or install download fails with `The connection dropped while downloading the update` or `aborted` | [Error reference](https://code.claude.com/docs/en/errors#the-connection-dropped-while-downloading-the-update) |
| Login loops, OAuth errors, `403 Forbidden`, “organization disabled”, Amazon Bedrock, Google Cloud’s Agent Platform, or Microsoft Foundry credentials | [Troubleshoot installation and login](https://code.claude.com/docs/en/troubleshoot-install#login-and-authentication) |
| Settings not applying, hooks not firing, MCP servers not loading | [Debug your configuration](https://code.claude.com/docs/en/debug-your-config) |
| `API Error: 5xx`, `529 Overloaded`, `429`, request validation errors | [Error reference](https://code.claude.com/docs/en/errors) |
| `model not found` or `you may not have access to it` | [Error reference](https://code.claude.com/docs/en/errors#theres-an-issue-with-the-selected-model) |
| VS Code extension not connecting or detecting Claude | [VS Code integration](https://code.claude.com/docs/en/vs-code#fix-common-issues) |
| JetBrains plugin or IDE not detected | [JetBrains integration](https://code.claude.com/docs/en/jetbrains#troubleshooting) |
| High CPU or memory, slow responses, hangs, search not finding files | [Performance and stability](https://code.claude.com/docs/en/troubleshooting#performance-and-stability) below |

If you’re not sure which applies, run `/doctor` inside Claude Code for an automated check of your installation, settings, extensions, and context usage; it proposes fixes it can apply after you confirm. If `claude` won’t start at all, run `claude doctor` from your shell instead. Run `/mcp` to check MCP server status.

##

[​

](https://code.claude.com/docs/en/troubleshooting#performance-and-stability)

Performance and stability

These sections cover issues related to resource usage, responsiveness, and search behavior.

###

[​

](https://code.claude.com/docs/en/troubleshooting#high-cpu-or-memory-usage)

High CPU or memory usage

Claude Code is designed to work with most development environments, but may consume significant resources when processing large codebases. If you’re experiencing performance issues:

1.  Use `/compact` regularly to reduce context size
2.  Close and restart Claude Code between major tasks
3.  Consider adding large build directories to your `.gitignore` file
4.  Restart with [`claude --safe-mode`](https://code.claude.com/docs/en/cli-reference#cli-flags) to check whether a plugin, MCP server, or hook is the source. It disables all customizations for the session; if usage drops, see [Debug your configuration](https://code.claude.com/docs/en/debug-your-config#test-against-a-clean-configuration) to find which one

If memory usage stays high after these steps, run `/heapdump` to write a JavaScript heap snapshot and a memory breakdown to `~/Desktop`. On Linux without a Desktop folder, the files are written to your home directory. The breakdown shows resident set size, JS heap, array buffers, and unaccounted native memory, which helps identify whether the growth is in JavaScript objects or in native code. To inspect retainers, open the `.heapsnapshot` file in Chrome DevTools under Memory → Load. Attach both files when reporting a memory issue on [GitHub](https://github.com/anthropics/claude-code/issues).

###

[​

](https://code.claude.com/docs/en/troubleshooting#auto-compaction-stops-with-a-thrashing-error)

Auto-compaction stops with a thrashing error

If you see `Autocompact is thrashing: the context refilled to the limit...`, automatic compaction succeeded but a file or tool output immediately refilled the context window several times in a row. Claude Code stops retrying to avoid wasting API calls on a loop that isn’t making progress. To recover:

1.  Ask Claude to read the oversized file in smaller chunks, such as a specific line range or function, instead of the whole file
2.  Run `/compact` with a focus that drops the large output, for example `/compact keep only the plan and the diff`
3.  Move the large-file work to a [subagent](https://code.claude.com/docs/en/sub-agents) so it runs in a separate context window
4.  Run `/clear` if the earlier conversation is no longer needed

###

[​

](https://code.claude.com/docs/en/troubleshooting#command-hangs-or-freezes)

Command hangs or freezes

If Claude Code seems unresponsive:

1.  Press Ctrl+C to attempt to cancel the current operation
2.  If unresponsive, you may need to close the terminal and restart

Restarting doesn’t lose your conversation. Run `claude --resume` in the same directory to pick the session back up.

###

[​

](https://code.claude.com/docs/en/troubleshooting#garbled-or-corrupted-text-in-an-editor%E2%80%99s-integrated-terminal)

Garbled or corrupted text in an editor’s integrated terminal

If characters render as boxes, smears, or the wrong glyphs when running Claude Code in the VS Code, Cursor, or Devin Desktop integrated terminal, the terminal’s GPU renderer is likely the cause. Run `/terminal-setup` inside Claude Code to set `terminal.integrated.gpuAcceleration` to `"off"`, or set it manually in your editor settings and reload the window. See [Terminal configuration](https://code.claude.com/docs/en/terminal-config) for the other settings `/terminal-setup` writes.

###

[​

](https://code.claude.com/docs/en/troubleshooting#search-and-discovery-issues)

Search and discovery issues

If the Search tool, `@file` mentions, custom agents, or custom skills aren’t finding files, the bundled `ripgrep` binary may not run on your system. Install your platform’s `ripgrep` package and tell Claude Code to use it instead:

-   macOS

-   Ubuntu/Debian

-   Alpine

-   Arch

-   Windows


```
brew install ripgrep
```

```
sudo apt install ripgrep
```

```
apk add ripgrep
```

```
pacman -S ripgrep
```

```
winget install BurntSushi.ripgrep.MSVC
```

Then set `USE_BUILTIN_RIPGREP=0` in your [environment](https://code.claude.com/docs/en/env-vars).

###

[​

](https://code.claude.com/docs/en/troubleshooting#slow-or-incomplete-search-results-on-wsl)

Slow or incomplete search results on WSL

Disk read performance penalties when [working across file systems on WSL](https://learn.microsoft.com/en-us/windows/wsl/filesystems) may result in fewer-than-expected matches when using Claude Code on WSL. Search still functions, but returns fewer results than on a native filesystem.

`claude doctor` shows Search as OK in this case.

**Solutions:**

1.  **Submit more specific searches**: reduce the number of files searched by specifying directories or file types: “Search for JWT validation logic in the auth-service package” or “Find use of md5 hash in JS files”.
2.  **Move project to Linux filesystem**: if possible, ensure your project is located on the Linux filesystem (`/home/`) rather than the Windows filesystem (`/mnt/c/`).
3.  **Use native Windows instead**: consider running Claude Code natively on Windows instead of through WSL, for better file system performance.

##

[​

](https://code.claude.com/docs/en/troubleshooting#get-more-help)

Get more help

If you’re experiencing issues not covered here:

1.  Run `/doctor` for a setup checkup and `/mcp` to check MCP server status
2.  Use the `/feedback` command within Claude Code to report problems directly to Anthropic
3.  Check the [GitHub repository](https://github.com/anthropics/claude-code) for known issues
4.  Ask Claude directly about its capabilities and features. Claude has built-in access to its documentation.

Was this page helpful?

YesNo

[Troubleshoot installation and login](https://code.claude.com/docs/en/troubleshoot-install)[Debug configuration](https://code.claude.com/docs/en/debug-your-config)

⌘I
