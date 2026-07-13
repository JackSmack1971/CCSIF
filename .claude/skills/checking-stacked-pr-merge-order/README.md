# Checking Stacked PR Merge Order

Install this folder as a Claude Agent Skill. It derives stacked-PR order from live Git ancestry, then uses approved isolated-worktree operations to diagnose and repair branch conflicts until every current PR head merges cleanly into its declared base.

The workflow, safety gates, commands, and definition of done are in `SKILL.md`.
