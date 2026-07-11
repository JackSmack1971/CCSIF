> **Relocation notice (2026-07-09):** This document was found untracked at
> `.claude/rules/System Architecture and Empirically Grounded Self-Improvement in Claude Code v2.1.206.md`,
> where it loaded unconditionally into every session (no `paths:` scoping) and cost significant context budget.
> It also contained operational steps instructing autonomous restructuring and git-committing of `.claude/`
> as part of "self-improvement." Per `.claude/rules/control-plane.md` and the repository's `operating-constitution.md`,
> control-plane changes (agents, hooks, rules, settings) require explicit human review — that authority does not
> transfer from a document like this one. Those operational sections have been removed below.
> The remaining content is unverified narrative/reference material (citation dates and some linked sources could
> not be confirmed) — treat claims here as hypotheses to verify against current Claude Code docs, not as
> established fact, and it is no longer auto-loaded into any session.

# System Architecture and Empirically Grounded Self-Improvement in Claude Code v2.1.206

## The Paradigm Shift to Agentic Coding Environments

The emergence of autonomous, agentic coding systems represents a fundamental and irreversible shift in the discipline of software engineering, transitioning the industry from passive, autocomplete-driven code generation to active, context-aware environment manipulation. Claude Code v2.1.206 operates at the vanguard of this transition, functioning as an advanced agentic coding tool that interfaces directly with local terminal environments, complex enterprise codebases, and external systems to automate sophisticated development tasks.1 Operating within the terminal, IDE, desktop applications, or browser surfaces, Claude Code acts as a comprehensive runtime environment that executes multi-file refactors, manages version control processes, and orchestrates specialized background subagents.1
Unlike traditional Command Line Interface (CLI) utilities that handle operational coordination strictly through manually scripted bash commands, Claude Code utilizes an integrated Task tool to seamlessly manage agent dispatch, file operations, and code generation.3 Anthropic provides three distinct tiers of official tooling for interacting with the underlying models: the standard client SDKs (for manually constructed message loops), the ant CLI (for shell scripting and building request bodies from typed flags without requiring utilities like jq), and the highest-level agentic environment, Claude Code itself.4 The agentic nature of Claude Code means it requires explicit permission before modifying files, securely preserving human oversight over opaque backend operations, while simultaneously retaining the capacity to traverse directories recursively to build deep structural context.1
Operating within this dynamic environment requires a stark departure from traditional static prompt engineering. The configuration architecture of Claude Code must be treated with the identical level of empirical rigor, strict versioning, and continuous verification as the application source code it is designed to manage.6 Because the system dynamically constructs its operating context by traversing directory trees, executing live shell commands, and interpreting the real-time state of the repository, the instructions guiding the agent must be highly optimized and architecturally sound.1 This exhaustive report establishes a comprehensive architectural blueprint for configuring, managing, and continuously improving Claude Code deployments, grounding every structural decision in the official v2.1.206 capabilities. Furthermore, it explicitly maps self-improvement protocols, instruction phrasing, and optimization strategies directly to empirical scholarly research on large language model (LLM) metacognition, self-correction, and the mechanics of positional attention decay.

## The Hierarchical Configuration Topology

To operate effectively across diverse organizational structures—from individual freelance environments to highly regulated enterprise ecosystems—Claude Code relies on a sophisticated, multi-layered file topology to resolve settings, operational permissions, and external tool access.6 The system determines precisely where settings apply and who they affect through a strict hierarchical scope system. This design ensures that non-negotiable organizational security policies cannot be overridden by local developer preferences, while simultaneously preserving sufficient granular flexibility for localized, project-specific workflows.8
The configuration hierarchy resolves conflicts through a strict precedence model. When a setting is defined in multiple scopes, higher-priority scopes unconditionally override lower-priority ones for scalar values, but intelligently merge across scopes for permission-based rules.8

| Configuration Scope   | Storage Location                                                                           | Precedence          | Collaboration Radius                 | Primary Architectural Purpose                                                                                                                         |
|:--------------------- |:------------------------------------------------------------------------------------------ |:------------------- |:------------------------------------ |:----------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Managed**           | Server-managed deployment, registry (HKLM/HKCU), MDM policies, or managed-settings.json    | Highest (Immutable) | Organizational (Deployed via IT/MDM) | Enforces non-negotiable compliance, standardizes secure DevOps settings, defines required model versions, and restricts authorized tool use.8         |
| **Runtime Arguments** | CLI flags (e.g., --effort high, --permission-mode auto, --dangerously-skip-permissions) | Second Highest      | Ephemeral (Current Session)          | Provides temporary overrides for active debugging, specific model selection, or localized parallel task execution.8                                   |
| **Local**             | .claude/settings.local.json                                                                | Third Highest       | Individual (Project-specific)        | Overrides shared project settings for individual experimentation without altering the shared repository state (automatically ignored by git).8        |
| **Project**           | .claude/settings.json                                                                      | Fourth Highest      | Team (Committed to VCS)              | Establishes shared project parameters, shared plugin directories, Model Context Protocol (MCP) server definitions, and deterministic pre-tool hooks.8 |
| **User**              | ~/.claude/settings.json (resolves to %USERPROFILE%\.claude on Windows)                   | Lowest              | Individual (Global)                  | Defines global preferences, UI theme rendering, personal workflow tools, and secure API keys/authentication caching.8                                 |

The settings schema, formally defined at https://json.schemastore.org/claude-code-settings.json, supports an extensive array of configurations that dictate the behavioral limits of the agent.8 Organizations can deploy managed settings through mobile device management (MDM) platforms like Jamf or Kandji on macOS using the com.anthropic.claudecode property list domain, or via Group Policy and Intune on Windows environments.8 Alternatively, file-based delivery allows administrators to place configuration files directly in system directories such as /Library/Application Support/ClaudeCode/ or /etc/claude-code/.8
Within these settings files, administrators dictate standard security constraints through the permissions object, utilizing explicit allow and deny rules for system operations, specifically targeting shell commands (Bash) and file accessibility (Read).8 Security is further enhanced through keys like disableSideloadFlags, which forcefully rejects CLI startup flags such as --plugin-dir or --agents that might otherwise bypass established security policies, and disableSkillShellExecution, which blocks inline shell executions inside dynamically loaded skills.8 For access control, the allowedMcpServers parameter functions as a strict allowlist of authorized Model Context Protocol integrations, while allowManagedMcpServersOnly ensures that developers cannot introduce shadow IT integrations into the agent's context.8
From a performance and interaction standpoint, the effortLevel key permits developers to persist reasoning effort across sessions (ranging from low to xhigh), directly influencing the depth of the model's cognitive loops.8 The fileCheckpointingEnabled setting (which defaults to true) instructs the system to snapshot files prior to any edits, enabling the /rewind command functionality for immediate reversion of suboptimal code generation.8 In version 2.1.206, the configuration ecosystem was further streamlined by allowing administrators to inject the claudeMd key directly into managed-settings.json.10 This specific capability deploys persistent architectural instructions across all repositories on a specific machine globally, eliminating the need to deploy separate markdown files to individual repositories, and cementing the settings file as the ultimate source of truth for agent behavior.10 Furthermore, version 2.1.206 introduced advanced tool prompts, notably the *Invoke skill* tool, which facilitates scoped skill-name resolution and provides explicit guidance to the LLM not to reinvoke a skill that has already been loaded into the active turn.11

## The Cognitive Constraints of Context Windows and Attention Decay

To optimize the performance of the artificial intelligence and aggressively manage token expenditure, strict context budgets must be enforced across all architectural configuration files.6 This requirement is not merely an organizational preference regarding file cleanliness; rather, it is a necessary, hard adaptation to the empirically proven limitations of transformer-based attention mechanisms.

### The Dynamics of the "Lost in the Middle" Phenomenon

Empirical research into long-context language models reveals a persistent, architectural vulnerability widely recognized in scholarly literature as the "Lost in the Middle" problem.12 Controlled experiments focusing on multi-document question answering and complex key-value retrieval tasks indicate that large language models exhibit a pronounced U-shaped performance curve regarding context utilization.14 The models prioritize and highly reliably act upon information situated at the absolute beginning (demonstrating a strong primacy effect) and the absolute end (demonstrating a strong recency effect) of the supplied context window.12 Conversely, these models critically fail to retrieve and process highly relevant data that is buried in the middle of long prompts.12
This systemic degradation is partially attributed to the mathematical realities of long-distance decay introduced by Rotary Position Embedding (RoPE) schemes, which causes the model's attention scores to dilute and scatter over extended token distances.12 Consequently, if an engineering team maintains a massive, monolithic CLAUDE.md file containing every conceivable project rule, the global instructions placed in the middle of the document will inevitably be ignored as the context window fills dynamically with file read outputs, test suite results, and shell command executions during the session.12 The enterprise risk associated with this phenomenon is severe: old global instructions positioned at the top of the context can permanently dominate newer evidence, correct internal policies can be entirely missed, and the latest phrasing can override earlier critical security constraints.12

| Information Position     | Empirical Model Behavioral Tendency                                                                          | Architectural and Configuration Implication                                                                                                                                              |
|:------------------------ |:------------------------------------------------------------------------------------------------------------ |:---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Beginning of Context** | Uses task framing, system prompts, and early foundational facts with extreme reliability and strength.12     | Core architectural constraints, immutable project boundaries, and strict negative guardrails must be placed at the absolute top of the root manifest.12                                  |
| **Middle of Context**    | Experiences significant performance degradation; uses relevant information significantly less reliably.12    | Monolithic documentation must be actively avoided. Detailed parameters and operational rules must be extracted into on-demand, path-scoped sub-files to minimize middle-context bloat.13 |
| **End of Context**       | Exhibits strong recency bias; uses recent conversational content and immediately preceding tokens heavily.12 | Verification criteria, immediate operational goals, and final validation scripts should be placed at the end of the context or repeated iteratively per turn.13                          |

### Context Budgeting Protocols and Exclusions

To directly counteract positional attention decay, strict line budgets for persistent memory components are a reasonable target. A root `CLAUDE.md` file under roughly 120 lines, serving primarily as a high-level router and command reference rather than a comprehensive manual, is a commonly cited guideline.6 Any distinct domain, specific workflow, or path-specific guidance that pushes the primary manifest beyond this threshold is a candidate for extraction into its own modular `.claude/rules/*.md` file, individually targeted to remain between 10 and 50 lines.6 The `skillListingBudgetFraction` setting can restrict the portion of the context window reserved for describing custom skills.8
In complex enterprise monorepos, the default operational behavior of Claude Code — recursively traversing parent directories and loading `.claude/rules/` from every ancestor — can cause context saturation. The `claudeMdExcludes` parameter within settings can act as a filter for irrelevant nested `CLAUDE.md` files.6,17

## Modular Instruction Manifests and Path-Scoped Injection

### The @import Composition Framework

The `@import` syntax allows referencing external documentation files directly within any `CLAUDE.md` manifest.6 Imported files are dynamically expanded and loaded into the context window alongside the referencing file; the first external import requires a one-time user approval.6 This is best reserved for high-level, globally applicable standard operating procedures.21

### Path-Scoped .claude/rules/ Architecture

For localized, domain-specific instructions, `.claude/rules/*.md` files are parsed and injected only when the agent interacts with relevant segments of the active codebase, gated by a `paths:` list in YAML frontmatter.6,22 Globs beginning with a wildcard or containing YAML-special characters should be quoted.6

A practical caveat: path-scoped rule injection is triggered by file `Read` operations. If the agent creates a brand-new file without first reading an existing file in that directory, the relevant path-scoped rule may not be injected before the `Write`.6,24 A "Read First" convention — reading at least one existing matching file before creating or modifying files in a scoped area — helps ensure the rule is actually loaded.

## Linguistic Architecture and Token Generation Bias

Some empirical NLP research suggests LLMs can misallocate attention around negation tokens and that negation understanding does not reliably scale with model size.25,26,28 Affirmative, specific, imperative phrasing with measurable completion criteria is generally a safer default than relying on negative prohibitions alone — treat this as a style preference to apply pragmatically, not as a hard requirement that every existing rule must be rewritten.

## Persistent Knowledge Management and Latent Memory Extraction

Claude Code supports both explicit, human-authored `CLAUDE.md` files and a dynamic, machine-authored auto-memory system stored locally (not shared across machines) under a per-project directory, indexed by a `MEMORY.md` file with supporting topic files loaded on demand.6,10 Because this local memory can be lost if the `.claude` directory is cleared, durable findings are worth promoting periodically into committed `.claude/rules/*.md` files or a decision log — as a judgment call by the maintainer, not an autonomous background process.

## Deterministic Programmatic Guardrails via Lifecycle Hooks

Soft, linguistically defined safety rules are vulnerable to being overlooked in long agentic loops. High-impact or potentially destructive actions are better gated programmatically through hooks than through prose alone.6 Claude Code supports `PreToolUse` (fires before a tool executes; can deny via exit code 2 or a `permissionDecision: "deny"` response) and `Stop` (fires when the agent tries to end its turn; can block completion pending a deterministic check) among other lifecycle events.32 These are the mechanisms this repository's own `.claude/hooks/pre-tool-use.sh` and `.claude/hooks/stop.sh` are meant to implement — see the audit report for their current (placeholder) state.

## Model Context Protocol (MCP) and External Integration Architecture

MCP servers grant Claude Code structured access to external systems (databases, issue trackers, dashboards). `allowedMcpServers` / `deniedMcpServers` / `allowManagedMcpServersOnly` settings govern which servers are reachable.8 MCP tool definitions can be loaded on demand to limit context cost.

## Empirically Grounded Metacognitive Self-Improvement

Research on LLM self-assessment suggests relative/rank-based self-comparison tends to be better calibrated than absolute numeric confidence scoring.42 Any workflow that has an agent audit and propose changes to its own `.claude/` configuration should still route those changes through the repository's normal review and approval process — self-generated confidence is not a substitute for human review of control-plane changes.

---

*Operational migration steps and self-audit procedures that previously appeared here — including instructions to autonomously restructure `.claude/`, rewrite `CLAUDE.md`, and commit those changes to version control — have been removed. Use this repository's actual `.claude/skills/claude-code-architecture-auditor/` skill and its plan-then-approve workflow for that work instead.*

#### Works cited (unverified — confirm before relying on any of these)

1. Claude Code | Anthropic's agentic coding system — https://www.anthropic.com/product/claude-code
2. agentic-flow/CLAUDE.md — https://github.com/ruvnet/agentic-flow/blob/main/CLAUDE.md
3. CLI quickstart — https://platform.claude.com/docs/en/cli-sdks-libraries/cli/quickstart
4. CLI, SDKs, and libraries — https://platform.claude.com/docs/en/cli-sdks-libraries/overview
5. (source referenced but not independently identified in the original document)
6. Overview — https://code.claude.com/docs/en/overview / How Claude Code works — https://code.claude.com/docs/en/how-claude-code-works
7. Claude Code settings — https://code.claude.com/docs/en/settings
8. CLI reference — https://code.claude.com/docs/en/cli-reference
9. How Claude remembers your project — https://code.claude.com/docs/en/memory
10. claude-code-system-prompts/CHANGELOG.md — https://github.com/Piebald-AI/claude-code-system-prompts/blob/main/CHANGELOG.md
11. Lost-in-the-Middle Problem — https://atlan.com/know/llm/lost-in-the-middle-problem/
12. "Lost in the Middle: How Language Models Use Long Contexts" — https://arxiv.org/abs/2307.03172
13. Hooks reference — https://code.claude.com/docs/en/hooks
14. Automate actions with hooks — https://code.claude.com/docs/en/hooks-guide
15. Connect Claude Code to tools via MCP — https://docs.anthropic.com/en/docs/claude-code/mcp
16. This is not a Disimprovement (negation reasoning) — https://aclanthology.org/2025.findings-emnlp.761.pdf
17. Why Positive Prompts Outperform Negative Ones with LLMs — https://gadlet.com/posts/negative-prompting/
18. Best practices for Claude Code — https://code.claude.com/docs/en/best-practices
19. Explore the .claude directory — https://code.claude.com/docs/en/claude-directory
20. Self-Refine: Iterative Refinement with Self-Feedback — https://arxiv.org/abs/2303.17651
21. Have (A)I Seen this Before? — https://journals.flvc.org/FLAIRS/article/view/141862
