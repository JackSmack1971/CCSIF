<!-- issue-to-pr-source:#<issue-number> -->

## Summary

<what changed and why, in plain language>

## Linked Issue

Closes #<issue-number>

## Verification

```text
<exact commands run and their outcome — not "tests pass", the actual command and result>
```

## Risk

<blast radius if this is wrong; "low" is not a substitute for stating what could break>

## Rollback

<revert this PR / other explicit rollback path>

## Checklist

- [ ] Focused diff scoped to this issue only
- [ ] Tests added or updated for the change
- [ ] Docs updated if behavior changed
- [ ] No secrets, debug output, or unrelated formatting churn
- [ ] Verification commands above were actually run against the final diff
