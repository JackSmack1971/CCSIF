---
name: alignment-interview
description: Use when surfacing requirements, assumptions, constraints, and success criteria for a new unit of work before anything is built, in either open-ended or interrogative mode. Trigger on queries that say let's brainstorm this feature, interview me about requirements, what are we actually trying to build, surface assumptions before we start, run the align gate. NOT for stress-testing an already-written plan against existing documentation citations use grill-with-docs instead, and NOT for synthesizing a conversation into a formal spec use to-spec instead. Distinct keywords open-ended, interrogative, assumptions, success-criteria, gate-one.
when_to_use: Use before any non-trivial unit of work to surface requirements, assumptions, constraints, and success criteria from scratch. Do not use to stress-test an existing plan against docs (grill-with-docs) or to synthesize a conversation into a PRD (to-spec).
argument-hint: "[topic] [--mode open|interrogative]"
allowed-tools: Read, Grep, Glob, Write, Edit, AskUserQuestion
---

# Alignment Interview

Gate 1 (Align) of the five-gate lifecycle (`.claude/rules/20-lifecycle-gates.md`). Two modes, one skill:

- **open** — exploratory brainstorming; propose options and let the user narrow them.
- **interrogative** — relentless requirements interrogation; assume nothing, ask until every open question is closed.

## Process

- [ ] Pick the mode from the invocation (`/brainstorm` → open, `/grill` → interrogative) or the argument hint.
- [ ] Read `docs/CONTEXT.md` and any ADRs in the relevant area first, so questions build on settled vocabulary and decisions instead of re-litigating them.
- [ ] In open mode: propose 2-4 concrete directions with trade-offs, and ask the user to pick or blend rather than accepting the first framing.
- [ ] In interrogative mode: ask about scope boundaries, non-goals, failure modes, and who is affected, until no material ambiguity remains.
- [ ] State every assumption explicitly as you form it — an unstated assumption is a defect (`.claude/rules/10-karpathy-guidelines.md`).
- [ ] Record settled requirements, constraints, and success criteria as you go; add or update a `docs/CONTEXT.md` glossary entry for any new domain term, and draft an ADR for any decision that would be expensive to reverse.

## Checklist

- [ ] Mode selected and declared before the first question
- [ ] Existing `docs/CONTEXT.md` and relevant ADRs read before asking anything
- [ ] Every assumption stated explicitly, not left implicit
- [ ] Success criteria are observable, not vague ("build the login screen" is not a success criterion; "user can complete login and land on the dashboard within 2s" is)
- [ ] New domain terms and reversible-decision ADRs recorded as they settle

## Completion gate

Do not consider the align gate complete until requirements, assumptions, constraints, and observable success criteria are all stated explicitly in the conversation or a saved note, and every open question is either resolved or explicitly deferred with a stated reason. An interview that ends with an unstated assumption has not met this gate.
