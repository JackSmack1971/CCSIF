---
title: "Orchestrate subagents at scale with dynamic workflows - Claude Code Docs"
source_url: "https://code.claude.com/docs/en/workflows"
host: "code.claude.com"
depth: 2
selector: "article,main,[role=main]"
fetched_at: "2026-07-12T00:15:43.061Z"
---
Dynamic workflows require Claude Code v2.1.154 or later and are available on all paid plans, with Anthropic API access, and on Amazon Bedrock, Google Cloud’s Agent Platform, and Microsoft Foundry. On Pro, turn them on from the Dynamic workflows row in `/config`.

A dynamic workflow is a JavaScript script that orchestrates [subagents](https://code.claude.com/docs/en/sub-agents) at scale. Claude writes the script for the task you describe, and a runtime executes it in the background while your session stays responsive. Reach for a workflow when a task needs more agents than one conversation can coordinate, or when you want the orchestration codified as a script you can read and rerun. Examples include a codebase-wide bug sweep, a 500-file migration, a research question that needs sources cross-checked against each other, and a hard plan worth drafting from several independent angles before you commit to one.

##

[​

](https://code.claude.com/docs/en/workflows#when-to-use-a-workflow)

When to use a workflow

[Subagents](https://code.claude.com/docs/en/sub-agents), [skills](https://code.claude.com/docs/en/skills), [agent teams](https://code.claude.com/docs/en/agent-teams), and workflows can all run a multi-step task. The difference is who holds the plan:

|  | Subagents | Skills | Agent teams | Workflows |
| --- | --- | --- | --- | --- |
| What it is | A worker Claude spawns | Instructions Claude follows | A lead agent supervising peer sessions | A script the runtime executes |
| Who decides what runs next | Claude, turn by turn | Claude, following the prompt | The lead agent, turn by turn | The script |
| Where intermediate results live | Claude’s context window | Claude’s context window | A shared task list | Script variables |
| What’s repeatable | The worker definition | The instructions | The team definition | The orchestration itself |
| Scale | A few delegated tasks per turn | Same as subagents | A handful of long-running peers | Dozens to hundreds of agents per run |
| Interruption | Restarts the turn | Restarts the turn | Teammates keep running | Resumable in the same session |

A workflow moves the plan into code. With subagents, skills, and agent teams, Claude is the orchestrator: it decides turn by turn what to spawn or assign next, and every result lands in a context window. A workflow script holds the loop, the branching, and the intermediate results itself, so Claude’s context holds only the final answer. Moving the plan into code also lets a workflow apply a repeatable quality pattern, not just run more agents: it can have independent agents adversarially review each other’s findings before they’re reported, or draft a plan from several angles and weigh them against each other, so you get a more trustworthy result than a single pass.

##

[​

](https://code.claude.com/docs/en/workflows#run-a-bundled-workflow)

Run a bundled workflow

The quickest way to see a workflow in action is to run `/deep-research`, the [built-in workflow](https://code.claude.com/docs/en/workflows#bundled-workflows) Claude Code includes for investigating a question across many sources. You’ll see agents work through a set of phases in the background while your session stays free, and get one report at the end instead of a turn-by-turn transcript.

1

[

](https://code.claude.com/docs/en/workflows#)

Run the workflow

Run `/deep-research` with a question you want investigated. It fans out web searches across several angles, fetches and cross-checks the sources it finds, and synthesizes a cited report.

```
/deep-research What changed in the Node.js permission model between v20 and v22?
```

2

[

](https://code.claude.com/docs/en/workflows#)

Allow workflows

Claude Code asks whether to allow the workflow. Select **Yes** to continue. The exact prompt depends on your permission mode. See [Approve the plan before it runs](https://code.claude.com/docs/en/workflows#approve-the-plan-before-it-runs) for the per-mode options.

3

[

](https://code.claude.com/docs/en/workflows#)

Watch progress

The run starts in the background. Run `/workflows`, use the arrow keys to select the run, and press Enter to open its progress view:

```
/workflows
```

The view shows each phase with its agent count, token total, and elapsed time. Drill into any phase to see its agents and what each one found. See [Watch the run](https://code.claude.com/docs/en/workflows#watch-the-run) for the full set of controls.You can also watch from the task panel below the input box: a one-line progress summary appears there while the run is going. Press the down arrow to focus it, then Enter to expand.

4

[

](https://code.claude.com/docs/en/workflows#)

Read the report

When the run finishes, the report lands in your session. It cites the sources each claim came from, with claims that didn’t survive cross-checking already filtered out.As of v2.1.196, when the verifier agents can’t check a claim, such as after a rate limit or API error, the report lists that claim as unverified instead of counting it as refuted.

To run a workflow for your own task, [have Claude write one](https://code.claude.com/docs/en/workflows#have-claude-write-a-workflow), and once a run does what you wanted you can [save it](https://code.claude.com/docs/en/workflows#save-the-workflow-for-reuse) as a command of your own.

###

[​

](https://code.claude.com/docs/en/workflows#bundled-workflows)

Bundled workflows

Claude Code includes `/deep-research` as a built-in workflow:

| Command | What it does |
| --- | --- |
| `/deep-research <question>` | Fans out web searches on a question across several angles, fetches and cross-checks the sources it finds, votes on each claim, and returns a cited report with claims that didn’t survive cross-checking filtered out. Requires the [WebSearch tool](https://code.claude.com/docs/en/tools-reference#websearch-tool-behavior) to be available |

[Workflows you save](https://code.claude.com/docs/en/workflows#save-the-workflow-for-reuse) yourself become commands the same way and appear in `/` autocomplete alongside the bundled ones.

###

[​

](https://code.claude.com/docs/en/workflows#watch-the-run)

Watch the run

Workflows run in the background, so the session stays responsive while agents work. Run `/workflows` at any time to list running and completed workflows, then select one to open its progress view.

```
/workflows
```

The progress view shows each phase with its agent counts, token totals, and elapsed time. The footer lists the key for each action:

| Key | Action |
| --- | --- |
| `↑` / `↓` | Select a phase or agent |
| `Enter` or `→` | Drill into the selected phase, then into an agent to read its prompt, recent tool calls, and result |
| `Esc` | Back out one level |
| `j` / `k` | Scroll within the agent detail when it overflows |
| `f` | Filter the agent list in the selected phase by status. Press again to cycle |
| `p` | Pause or resume the run |
| `x` | Stop the selected agent, or stop the whole workflow when focus is on the run |
| `r` | Restart the selected running agent |
| `s` | [Save](https://code.claude.com/docs/en/workflows#save-the-workflow-for-reuse) the run’s script as a command |

##

[​

](https://code.claude.com/docs/en/workflows#have-claude-write-a-workflow)

Have Claude write a workflow

You can have Claude write a workflow for your task in two ways:

-   [Ask for a workflow](https://code.claude.com/docs/en/workflows#ask-for-a-workflow-in-your-prompt) in your prompt, either in your own words or by including the keyword `ultracode`, and Claude writes one for the task.
-   [Let Claude decide with ultracode](https://code.claude.com/docs/en/workflows#let-claude-decide-with-ultracode): set `/effort ultracode` and Claude plans a workflow for every substantive task in the session.

You can also run a workflow command that already exists: a [bundled workflow](https://code.claude.com/docs/en/workflows#bundled-workflows) like `/deep-research`, or one you’ve [saved](https://code.claude.com/docs/en/workflows#save-the-workflow-for-reuse).

###

[​

](https://code.claude.com/docs/en/workflows#ask-for-a-workflow-in-your-prompt)

Ask for a workflow in your prompt

To run a single task as a workflow without changing the session’s effort level, include the keyword `ultracode` in your prompt. Asking in your own words, for example “use a workflow” or “run a workflow”, also works: Claude treats a direct request as the same opt-in. Before v2.1.160 the literal trigger keyword was `workflow`; natural-language requests work in both versions.

```
ultracode: audit every API endpoint under src/routes/ for missing auth checks
```

Claude Code highlights the keyword in your input and Claude writes a workflow script for the task instead of working through it turn by turn. If you didn’t mean to start a workflow, press `Option+W` on macOS or `Alt+W` on Windows and Linux to dismiss the highlight for this prompt, or press backspace while the cursor is right after the highlighted keyword. To stop the keyword from triggering at all, turn off Ultracode keyword trigger in `/config`. If the run does what you wanted, you can [save it as a command](https://code.claude.com/docs/en/workflows#save-the-workflow-for-reuse) afterward. If you already have an orchestrator built another way, such as a folder of subagent prompts or a skill that fans work out, you can point Claude at it and ask for a workflow that does the same thing.

###

[​

](https://code.claude.com/docs/en/workflows#let-claude-decide-with-ultracode)

Let Claude decide with ultracode

Ultracode is a Claude Code setting that combines `xhigh` [reasoning effort](https://code.claude.com/docs/en/model-config#adjust-effort-level) with automatic workflow orchestration. With it on, Claude plans a workflow for each substantive task instead of waiting for you to ask.

```
/effort ultracode
```

To start a session with ultracode already on, launch with `claude --effort ultracode`. Requires Claude Code v2.1.203 or later. With ultracode on, Claude decides when a task warrants a workflow. A single request can turn into several workflows in a row: one to understand the code, one to make the change, and one to verify it. This applies to every task in the session, so each request uses more tokens and takes longer than at lower effort levels. Ultracode lasts for the current session and resets when you start a new one. Drop back with `/effort high` when you return to routine work. It’s available on models that support `xhigh` [effort](https://code.claude.com/docs/en/model-config#adjust-effort-level); on other models the `/effort` menu doesn’t offer it.

###

[​

](https://code.claude.com/docs/en/workflows#approve-the-plan-before-it-runs)

Approve the plan before it runs

In the CLI, the per-run prompt shows the planned phases and these options:

-   **Yes, run it**: start the run
-   **Yes, and don’t ask again for `<name>` in `<path>`**: start, and skip this prompt for this workflow in this project from now on
-   **View raw script**: read the script before deciding
-   **No**: cancel

`Ctrl+G` opens the script in your editor. `Tab` lets you adjust the prompt before the run starts. Whether you see this prompt depends on your [permission mode](https://code.claude.com/docs/en/permission-modes):

| Permission mode | When you’re prompted |
| --- | --- |
| Default, accept edits | Every run, unless you’ve selected **Yes, and don’t ask again** for that workflow in this project |
| Auto | First launch only. Any **Yes** records consent in your user settings, and later launches start without prompting. Skipped entirely when ultracode is on |
| Bypass permissions, `claude -p`, Agent SDK | Never. The run starts immediately |

In the Desktop app, an approval card shows the workflow name, the phase list, and a token-usage caution, with **Once**, **Always**, and **Deny** actions. The progress view appears in the Background tasks side pane. Your permission mode controls only the launch prompt above. The subagents the workflow spawns always run in `acceptEdits` mode and inherit your [tool allowlist](https://code.claude.com/docs/en/settings#permission-settings), regardless of your session’s mode. File edits are auto-approved. Shell commands, web fetches, and MCP tools that aren’t in your allowlist can still prompt you mid-run. To avoid this on a long run, add the commands the agents need to your allowlist before starting. In `claude -p` and the Agent SDK there is no one to prompt, so tool calls follow your configured permission rules without interactive confirmation.

###

[​

](https://code.claude.com/docs/en/workflows#save-the-workflow-for-reuse)

Save the workflow for reuse

When Claude writes a workflow for a task you’ll repeat, you can save that run’s script as a command. A process like a review you run on every branch then runs the same orchestration each time. Run `/workflows`, select the run you want to keep, and press `s`. In the save dialog, Tab toggles between the two save locations:

-   `.claude/workflows/` in your project: shared with everyone who clones the repo
-   `~/.claude/workflows/` in your home directory: available in every project, visible only to you

Press Enter to save. The workflow runs as `/<name>` in future sessions from either location. In a monorepo with several `.claude/` directories, you can keep workflows alongside the package they apply to. As of v2.1.178, saving to the project location writes to the closest `.claude/workflows/` directory that already exists between your working directory and the repository root, or to the repository root if none exists yet. Project workflows also load from every `.claude/workflows/` along that path, and when more than one defines the same name Claude Code runs the one closest to the working directory. If a project workflow and a personal workflow share a name, the project one runs.

###

[​

](https://code.claude.com/docs/en/workflows#pass-input-to-a-saved-workflow)

Pass input to a saved workflow

A saved workflow can accept input through the `args` parameter. The script reads it as a global named `args`. Use this to supply a research question, a list of target paths, or a configuration object at invocation time instead of editing the script for each run. The following prompt runs a saved workflow with a list of issue numbers:

```
> Run /triage-issues on issues 1024, 1025, and 1030
```

Claude passes the list as structured data, so the script can call array and object methods on `args` directly without parsing it first. If `args` is omitted, the global is `undefined` inside the script.

##

[​

](https://code.claude.com/docs/en/workflows#example-workflow-prompts)

Example workflow prompts

A workflow fits best when the task is larger than one agent can hold in context, or when the same step needs to run across many items. The prompts below show common shapes. Each one asks Claude to write and run a workflow for that task; you don’t write the script yourself.

###

[​

](https://code.claude.com/docs/en/workflows#audit-many-files-for-the-same-issue)

Audit many files for the same issue

Fan out one agent per file, then collect and verify the findings.

```
> use a workflow to audit every route handler under src/routes/ for missing authentication checks, and adversarially verify each finding before reporting it
```

###

[​

](https://code.claude.com/docs/en/workflows#keep-fixing-until-a-check-passes)

Keep fixing until a check passes

Run a checker, fix what failed, and repeat until it passes or stops making progress.

```
> use a workflow to run npx tsc --noEmit and keep fixing the reported errors until the type check passes or two rounds in a row make no progress
```

###

[​

](https://code.claude.com/docs/en/workflows#migrate-many-files-in-parallel)

Migrate many files in parallel

Discover the files to migrate, transform each one in an isolated copy so edits don’t conflict, and verify each result.

```
> use a workflow to migrate every component under src/components/ from styled-components to Tailwind, working on each file in its own isolated copy
```

###

[​

](https://code.claude.com/docs/en/workflows#review-every-changed-file-and-write-one-summary)

Review every changed file and write one summary

Run a reviewer per file, then hand all the findings to one agent that ranks and deduplicates them.

```
> use a workflow to review every file changed in this PR for correctness issues, then merge the per-file findings into one ranked summary
```

###

[​

](https://code.claude.com/docs/en/workflows#research-a-topic-across-many-sources)

Research a topic across many sources

Fan out readers across changelogs, issues, and docs, then synthesize. The bundled `/deep-research` workflow does this; you can also describe a narrower version.

```
> use a workflow to research how our three competitors handle rate limiting: read their public docs and recent changelog entries in parallel, then compare the approaches
```

###

[​

](https://code.claude.com/docs/en/workflows#find-issues-until-the-list-stops-growing)

Find issues until the list stops growing

Keep searching in rounds and stop when new rounds turn up nothing new.

```
> use a workflow to find flaky tests in this repo: run the suite repeatedly, record which tests fail intermittently, and stop once two rounds in a row find nothing new
```

###

[​

](https://code.claude.com/docs/en/workflows#what-the-saved-script-looks-like)

What the saved script looks like

When you [save a workflow](https://code.claude.com/docs/en/workflows#save-the-workflow-for-reuse), the file in `.claude/workflows/` holds a `meta` block followed by a script body that orchestrates subagents. You usually don’t need to edit it, but here is the shape of a small one so you can recognize what Claude generated:

```
export const meta = {
  name: 'audit-routes',
  description: 'Audit every route handler for missing auth checks',
}

const found = await agent('List every .ts file under src/routes/.', {
  schema: { type: 'object', required: ['files'], properties: { files: { type: 'array', items: { type: 'string' } } } },
})

const audits = await pipeline(found.files, file =>
  agent(`Audit ${file} for missing authentication checks.`, { label: file }),
)

return audits.filter(Boolean)
```

The body is plain JavaScript with top-level `await`. `agent()` spawns one subagent and `pipeline()` runs one per item in a list. If you want to edit a script by hand, ask Claude to walk you through the change, or see the Workflow tool entry in the [Agent SDK reference](https://code.claude.com/docs/en/agent-sdk/typescript) for the full set of options.

##

[​

](https://code.claude.com/docs/en/workflows#how-a-workflow-runs)

How a workflow runs

The workflow runtime executes the script in an isolated environment, separate from your conversation. Intermediate results stay in script variables instead of landing in Claude’s context. Every run writes its script to a file under your session’s directory in `~/.claude/projects/`. Claude receives the path when the run starts, so you can ask for it. You can open that file to read the orchestration Claude wrote, diff it against a previous run’s script, or edit it and ask Claude to relaunch from the edited version. The runtime tracks each agent’s result as the run progresses, which is what makes a run [resumable](https://code.claude.com/docs/en/workflows#resume-after-a-pause) within the same session.

###

[​

](https://code.claude.com/docs/en/workflows#behavior-and-limits)

Behavior and limits

The runtime applies the following constraints:

| Constraint | Why |
| --- | --- |
| No mid-run user input | Only agent permission prompts can pause a run. For sign-off between stages, run each stage as its own workflow |
| No direct filesystem or shell access from the workflow itself | Agents read, write, and run commands. The script coordinates the agents |
| Up to 16 concurrent agents, fewer on machines with limited CPU cores | Bounds local resource use |
| 1,000 agents total per run | Prevents runaway loops |

##

[​

](https://code.claude.com/docs/en/workflows#manage-runs)

Manage runs

Once a run starts, you manage it from the `/workflows` view, or by expanding its progress line in the task panel below the input box.

###

[​

](https://code.claude.com/docs/en/workflows#resume-after-a-pause)

Resume after a pause

If you stop a run, you can resume it: agents that already completed return their cached results, and the rest run live. Resume a paused run from `/workflows` by selecting it and pressing `p`, or ask Claude to relaunch the workflow with the same script. Resume works within the same Claude Code session. If you exit Claude Code while a workflow is running, the next session starts the workflow fresh.

###

[​

](https://code.claude.com/docs/en/workflows#cost)

Cost

A workflow spawns many agents, so a single run can use meaningfully more tokens than working through the same task in conversation. Runs count toward your plan’s usage and rate limits like any other session. To gauge the spend before committing to a large task, run the workflow on a small slice first: one directory instead of the whole repo, or a narrow question instead of a broad one. The `/workflows` view shows each agent’s token usage as the run progresses, and you can stop the run there at any time without losing completed work. The runtime’s [agent caps](https://code.claude.com/docs/en/workflows#behavior-and-limits) limit how many agents a single run can spawn, which bounds the cost of a runaway script. To keep every run smaller by default, [set a size guideline](https://code.claude.com/docs/en/workflows#set-a-size-guideline) in `/config`. Claude Code also flags a run that grows unusually large. When a workflow schedules more than 25 agents, or its projected token total passes 1.5 million, its progress line in the task panel below the input box shows a `Large workflow` warning. The warning points you to [`/workflows`](https://code.claude.com/docs/en/workflows#watch-the-run), where you can stop the run. Requires Claude Code v2.1.203 or later. The warning is advisory: it doesn’t pause or limit the run. Two settings change when you see it:

-   If you [set a size guideline](https://code.claude.com/docs/en/workflows#set-a-size-guideline), the guideline’s agent count replaces the 25-agent threshold.
-   Sessions with [ultracode](https://code.claude.com/docs/en/workflows#let-claude-decide-with-ultracode) on don’t show the warning, because turning ultracode on already opts you in to large runs.

Every agent in a workflow uses your session’s model unless the script routes a stage to a different one. To control the model cost:

-   Check `/model` before a large run if you usually switch to a smaller model for routine work
-   Ask Claude to use a smaller model for stages that don’t need the strongest one when you describe the task

###

[​

](https://code.claude.com/docs/en/workflows#set-a-size-guideline)

Set a size guideline

The Dynamic workflow size setting in `/config` keeps the workflows Claude writes to a smaller scale by default. Claude Code sends the setting to Claude as advice, so a prompt that calls for a different scale still overrides it. Requires Claude Code v2.1.202 or later. Each value sets the agent count Claude aims for in the scripts it writes.

| Value | Guidance sent to Claude |
| --- | --- |
| `unrestricted` | No guideline. This is the default. |
| `small` | Aim for fewer than 5 agents. |
| `medium` | Aim for fewer than 15 agents. |
| `large` | Aim for fewer than 50 agents. |

Changes take effect on the next prompt. The [runtime agent caps](https://code.claude.com/docs/en/workflows#behavior-and-limits) still apply regardless of the setting.

###

[​

](https://code.claude.com/docs/en/workflows#turn-workflows-off)

Turn workflows off

Workflows are available in the CLI, the Desktop app, the IDE extensions, [non-interactive mode](https://code.claude.com/docs/en/headless) with `claude -p`, and the [Agent SDK](https://code.claude.com/docs/en/agent-sdk/overview). The same disable settings apply on every surface. To turn workflows off for yourself:

-   Toggle Dynamic workflows off in `/config`. Persists across sessions.
-   Set `"disableWorkflows": true` in `~/.claude/settings.json`. Persists across sessions.
-   Set `CLAUDE_CODE_DISABLE_WORKFLOWS=1`. Read at startup, so it applies wherever you set it.

To turn workflows off for your whole organization, set `"disableWorkflows": true` in [managed settings](https://code.claude.com/docs/en/server-managed-settings), or use the toggle on the [Claude Code admin settings](https://claude.ai/admin-settings/claude-code) page. When workflows are disabled, the bundled workflow commands are unavailable, the `ultracode` keyword no longer triggers a run, and `ultracode` is removed from the `/effort` menu.

##

[​

](https://code.claude.com/docs/en/workflows#related-resources)

Related resources

-   [Run agents in parallel](https://code.claude.com/docs/en/agents): compare subagents, agent view, agent teams, and workflows
-   [Create custom subagents](https://code.claude.com/docs/en/sub-agents): the worker primitive workflows orchestrate
-   [Manage costs](https://code.claude.com/docs/en/costs): how multi-agent runs count toward usage limits

Was this page helpful?

YesNo

[Run agent teams](https://code.claude.com/docs/en/agent-teams)[Isolate sessions with worktrees](https://code.claude.com/docs/en/worktrees)

⌘I
