# Repository rulesets (settings-as-code)

This directory holds definitions for GitHub repository rulesets. GitHub
does not apply these definitions automatically from the git tree; a
repository admin must import them explicitly with the GitHub API or the
Settings UI. Keeping the definition here makes the intended policy
git-tracked, reviewable, and reversible even though the live setting lives
outside the repository's file tree.

## `main-branch-protection.json`

Protects the default branch (`~DEFAULT_BRANCH`, resolved by GitHub to
whatever branch is configured as default) per issue tracked under
`REMOTE-DEFAULT-BRANCH-UNPROTECTED`:

- Blocks branch deletion and non-fast-forward pushes (no force-push, no
  direct history rewrite) on the default branch.
- Requires all changes to land through a pull request and restricts the
  merge method to squash, matching the "Merge policy" section of the
  repository's root `CONTRIBUTING.md`.
- Sets `required_approving_review_count` to `0` because the repository
  currently has a single verified collaborator with write access (see
  `.github/CODEOWNERS`); the rule still forces every change through a PR
  even though no second reviewer is available to satisfy a nonzero
  approval count. Raise this value the first time a second maintainer is
  added.
- Does not require status checks: no CI workflow exists under
  `.github/workflows/` yet, and requiring a check that cannot run on every
  eligible pull request would block all merges. Add a `required_status_
  checks` rule here once CI is introduced.
- Grants organization admins an always-on bypass so repository
  administration is never locked out by its own protection.

## Applying the ruleset

A repository admin applies this definition out-of-band from any pull
request merge, since GitHub reads ruleset configuration from the API/UI,
not from files in the tree:

```bash
gh api repos/JackSmack1971/CCSIF/rulesets \
  --method POST \
  --input .github/rulesets/main-branch-protection.json
```

Verify afterward with:

```bash
gh api repos/JackSmack1971/CCSIF/rulesets
gh api repos/JackSmack1971/CCSIF/branches/main/protection
```

If the definition changes here, re-apply it with a PUT request to
`repos/{owner}/{repo}/rulesets/{ruleset_id}` (or delete and re-create) so
the live setting matches the checked-in file.
