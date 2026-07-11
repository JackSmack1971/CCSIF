---
name: to-spec
description: Use when converting the current conversation into a formal spec document (PRD) with problem statement, user stories, implementation decisions, and testing decisions, then publishing it to the project issue tracker with the ready-for-agent label. Trigger on queries that say write the spec, turn this into a spec, publish this as a PRD, create a spec from our discussion, file this as a ticket. NOT for interviewing the user to gather requirements from scratch, discuss directly with the user instead. Distinct keywords conversation, synthesis, specification, triage, publish, issue-tracker.
disable-model-invocation: true
when_to_use: Use when you want to synthesize the current conversation into a PRD and publish it to the issue tracker. Do not use for requirements interviews; discuss directly with the user instead.
argument-hint: "[spec topic]"
allowed-tools: Read, Glob, Grep, Bash
---

This skill takes the current conversation context and codebase understanding and produces a spec (you may know this document as a PRD). Do NOT interview the user — just synthesize what you already know.

The issue tracker and triage label vocabulary should have been provided to you — run `/setup-matt-pocock-skills` if not.

## Process

1. Explore the repo to understand the current state of the codebase, if you haven't already. Use the project's domain glossary vocabulary throughout the spec, and respect any ADRs in the area you're touching.

2. Sketch out the seams at which you're going to test the feature. Existing seams should be preferred to new ones. Use the highest seam possible. If new seams are needed, propose them at the highest point you can. The fewer seams across the codebase, the better - the ideal number is one.

Check with the user that these seams match their expectations.

3. Write the spec using the template below, then publish it to the project issue tracker. Apply the `ready-for-agent` triage label - no need for additional triage.

## Checklist

- [ ] Explored the repo (or confirmed prior exploration) and used the project's domain glossary and ADRs
- [ ] Sketched the test seams, preferring existing and fewest possible, and confirmed them with the user
- [ ] Wrote the spec using the template below
- [ ] Published the spec to the project issue tracker with the `ready-for-agent` label

Completion gate: do not consider this skill complete until the spec is published to the issue tracker with the `ready-for-agent` label applied and the user has confirmed the proposed test seams match their expectations.

<spec-template>

## Problem Statement

The problem that the user is facing, from the user's perspective.

## Solution

The solution to the problem, from the user's perspective.

## User Stories

A LONG, numbered list of user stories. Each user story should be in the format of:

1. As an <actor>, I want a <feature>, so that <benefit>

<user-story-example>
1. As a mobile bank customer, I want to see balance on my accounts, so that I can make better informed decisions about my spending
</user-story-example>

This list of user stories should be extremely extensive and cover all aspects of the feature.

## Implementation Decisions

A list of implementation decisions that were made. This can include:

- The modules that will be built/modified
- The interfaces of those modules that will be modified
- Technical clarifications from the developer
- Architectural decisions
- Schema changes
- API contracts
- Specific interactions

Do NOT include specific file paths or code snippets. They may end up being outdated very quickly.

Exception: if a prototype produced a snippet that encodes a decision more precisely than prose can (state machine, reducer, schema, type shape), inline it within the relevant decision and note briefly that it came from a prototype. Trim to the decision-rich parts — not a working demo, just the important bits.

## Testing Decisions

A list of testing decisions that were made. Include:

- A description of what makes a good test (only test external behavior, not implementation details)
- Which modules will be tested
- Prior art for the tests (i.e. similar types of tests in the codebase)

## Out of Scope

A description of the things that are out of scope for this spec.

## Further Notes

Any further notes about the feature.

</spec-template>
