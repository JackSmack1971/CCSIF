---
name: research
description: Use when the user wants a single background agent to investigate a question against primary sources such as official documentation source code specs and first party APIs then capture the findings as one cited Markdown file in the repository. Trigger on queries that say research this topic for me, find the primary source for this claim, look up how this API actually works, delegate this reading legwork to a background agent, write the findings into a markdown note. NOT for multi source fan out web research with adversarial claim verification and a synthesized report use deep-research instead.
allowed-tools: Agent, WebSearch, WebFetch, Read, Grep, Glob, Write
---

Spin up a **background agent** to do the research, so you keep working while it reads.

Its job:

- [ ] Investigate the question against **primary sources** — official docs, source code, specs, first-party APIs — not a secondary write-up of them. Follow every claim back to the source that owns it.
- [ ] Cross-check each claim against its primary source before writing it down; if the primary source cannot be located or the source disagrees with a secondary summary, verify against the source and note the discrepancy rather than silently trusting the summary.
- [ ] Write the findings to a single Markdown file, citing each claim's source.
- [ ] Save it where the repo already keeps such notes; match the existing convention, and if there is none, put it somewhere sensible and say where.

Completion gate: do not report the task done until the Markdown file exists on disk and every claim in it cites the primary source it was verified against. If a primary source cannot be found or verified within a reasonable search effort, stop and report that gap explicitly instead of writing an unverified claim.
