---
name: grill-with-docs
description: Use when running a documentation-grounded interview to stress-test a plan or design, capturing ADRs and a glossary as citations accumulate. Trigger on queries that say grill this against our docs, stress-test my design with citations, run a grill-with-docs session, cross-examine this proposal using existing documentation. NOT for a plan interrogation without doc citations, use grilling instead. Distinct keywords glossary, citations, interview, decisions, architecture.
disable-model-invocation: true
allowed-tools: Read, Write, Edit, Grep, Glob, Skill
---

Run a `/grilling` session, using the `/domain-modeling` skill, capturing ADRs and a glossary entry for each settled decision.

## Process

- [ ] Start the `/grilling` interview session on the plan or design under review.
- [ ] Apply the `/domain-modeling` skill to surface entities, terms, and decisions worth recording.
- [ ] Record each settled decision as an ADR and each new term in the glossary as the session proceeds.
- [ ] Verify every claim, answer, and citation raised during the interview is grounded in the ADRs or glossary entries actually produced, not asserted from memory.

## Completion gate

The session is complete only when every open question raised in the interview has either been resolved and recorded in an ADR or glossary entry, or explicitly deferred with a stated reason. Do not consider the grilling session complete while ungrounded claims or unresolved decisions remain.
