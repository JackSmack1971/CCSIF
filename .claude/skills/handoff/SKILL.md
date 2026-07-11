---
name: handoff
description: Use when compacting the current conversation into a handoff document so a fresh agent or new session can continue the work. Trigger on queries that say create a handoff document, hand off this session to another agent, compact this conversation for a new session, prepare a context transfer document for the next agent. NOT for writing specs, ADRs, or implementation plans use adr-authoring or to-spec instead. Distinct keywords handoff, conversation, session, redact, credentials.
argument-hint: "What will the next session be used for?"
disable-model-invocation: true
allowed-tools: Read, Bash, Write
---

Write a handoff document summarising the current conversation so a fresh agent can continue the work. Save to the temporary directory of the user's OS - not the current workspace.

Include a "suggested skills" section in the document, which suggests skills that the agent should invoke.

Do not duplicate content already captured in other artifacts (specs, plans, ADRs, issues, commits, diffs). Reference them by path or URL instead.

Redact any sensitive information, such as API keys, passwords, or personally identifiable information.

If the user passed arguments, treat them as a description of what the next session will focus on and tailor the doc accordingly.

## Checklist

- [ ] Summarize the current conversation and outstanding work accurately
- [ ] Reference existing specs, plans, ADRs, issues, commits, and diffs by path or URL instead of duplicating their content
- [ ] Redact API keys, passwords, tokens, and personally identifiable information
- [ ] Add a "suggested skills" section naming skills the next agent should invoke
- [ ] Save the document to the OS temporary directory, not the current workspace
- [ ] Verify the saved handoff document before finishing

## Validation

Before finishing, re-read the saved handoff document and verify it is complete and accurate: confirm the summary matches the actual conversation state, every referenced artifact path or URL resolves correctly, no secrets or personally identifiable information remain in the text, and the file was written to the OS temporary directory rather than the workspace.

## Completion gate

Do not consider the handoff complete until the document has been written, verified against the checklist above, and its saved path has been reported back to the user. If verification finds missing context, an unredacted secret, or an incorrect path, fix the document before stopping.
