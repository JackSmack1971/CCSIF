---
name: accessibility-review
description: Use when asked for an accessibility review, a11y audit, WCAG assessment, or keyboard navigation and screen reader behavior review of UI code, docs, or a pull request. Trigger on accessibility review, a11y audit, WCAG assessment, keyboard navigation review, screen reader behavior check. NOT for a general visual design review with no accessibility criteria; use frontend-design instead. Requires citing WCAG-informed expectations and repository conventions for every reported risk.
user-invocable: true
context: fork
agent: Explore
when_to_use: Use when maintainers need an evidence-backed accessibility assessment of UI implementation, documentation, design specs, or interaction flows against WCAG-informed expectations and repository conventions.
argument-hint: "[PATH|PR_NUMBER_OR_URL|BASE..HEAD] [--format markdown|json]"
allowed-tools: "Read Grep Glob Bash(git rev-parse:*) Bash(git status:*) Bash(git diff:*) Bash(git show:*) Bash(git log:*) Bash(gh pr view:*) Bash(gh pr diff:*) Bash(gh pr checks:*) Bash(npm run:*) Bash(pnpm run:*) Bash(yarn run:*) Bash(npx:*) Bash(pytest:*)"
---

# Accessibility Review

## Purpose

Review UI code, documentation, or design artifacts for accessibility risks that affect disabled users and assistive-technology users. Produce an evidence-backed report with prioritized findings, likely user impact, references to affected files or artifacts, and practical verification steps using the repository's existing tooling where available.

Use WCAG-informed reasoning, but do not claim formal certification unless the user explicitly requested a standards audit and the required manual and automated evidence is available. Accessibility cannot be proven by automated tools alone; combine source review, interaction reasoning, and targeted test recommendations.

## Trigger Text

Use this skill for requests containing or equivalent to:

- "accessibility review"
- "a11y audit"
- "WCAG"
- "keyboard navigation"
- "screen reader"
- "focus management"
- "color contrast"
- "ARIA review"
- "form accessibility"
- "alt text"

## Inputs

Parse the invocation as:

- `PATH`: optional file, directory, route, doc, screenshot, design artifact, or component scope.
- `PR_NUMBER_OR_URL`: optional pull request identifier to inspect with GitHub CLI.
- `BASE..HEAD`: optional Git revision range to inspect locally.
- `--format markdown|json`: optional; default `markdown`.

If no input is supplied, review the working tree and staged changes against `HEAD`, then clearly label the comparison source. Reject unknown flags rather than guessing intent.

## Workflow

### 1. Establish scope and evidence

1. Confirm the repository root with `git rev-parse --show-toplevel` when reviewing code.
2. Determine whether the review target is a pull request, diff range, working tree, specific path, documentation, design artifact, or described flow.
3. Inventory changed or target files with read-only commands such as `git diff --name-status`, `git diff`, `git show`, `gh pr view`, `gh pr diff`, `Glob`, `Grep`, and `Read`.
4. Identify UI frameworks, component libraries, styling systems, test frameworks, accessibility tooling, design tokens, and documentation conventions from manifests, config, CI, and nearby files.
5. Separate direct evidence from inference. If runtime behavior cannot be executed or design specs are incomplete, state the limitation and recommend the minimum manual checks needed.

### 2. Review semantic structure and keyboard navigation

Check whether the UI exposes meaningful structure and can be operated without a mouse:

- Prefer native HTML elements for controls, headings, landmarks, lists, tables, dialogs, and form fields before custom ARIA patterns.
- Verify heading order, page regions, landmark names, table headers, list semantics, and document/page title behavior when relevant.
- Confirm links navigate and buttons perform actions; avoid clickable `div`/`span` elements unless they fully implement keyboard and semantic behavior.
- Check tab order, reachable controls, skipped hidden elements, focus traps, escape routes, roving tab index patterns, and keyboard shortcuts.
- Verify expected keyboard interactions for menus, tabs, accordions, comboboxes, listboxes, dialogs, drawers, popovers, toasts, carousels, drag-and-drop, and custom widgets.
- Ensure disabled, loading, expanded, selected, pressed, current, and invalid states are represented semantically and visually.

### 3. Review labels, roles, names, focus management, and form errors

Check the accessible names and state model that assistive technologies receive:

- Verify every interactive control has a clear accessible name from visible text, associated labels, `aria-label`, `aria-labelledby`, or equivalent framework abstractions.
- Ensure accessible names match or include visible labels for speech input compatibility.
- Avoid redundant, conflicting, or misleading roles and ARIA attributes, especially when native semantics already provide the role.
- Confirm form inputs have labels, required indicators, instructions, autocomplete where useful, grouping for related controls, and programmatic error associations.
- Check validation timing, error summaries, inline errors, focus movement after submit failures, and recovery instructions.
- Verify dialogs, modals, drawers, menus, and route changes move focus intentionally and restore focus when closed or completed.
- Ensure focus indicators are visible, high contrast, not clipped, and not removed by CSS resets.

### 4. Review color contrast and non-color affordances

Check visual accessibility for text, icons, states, charts, and interaction cues:

- Verify text, placeholder text, disabled-looking enabled controls, icons conveying meaning, focus rings, borders, and state indicators have sufficient contrast against their backgrounds.
- Check both default and interactive states: hover, focus, active, selected, disabled, error, success, warning, and loading.
- Do not rely on color alone to communicate required fields, validation errors, selection, status, links, chart series, or destructive actions.
- Inspect design tokens and theme variants for light mode, dark mode, high-contrast modes, forced-colors mode, and custom brand colors.
- Call out where contrast requires manual measurement with exact foreground/background values if source tokens or rendered styles are not enough.

### 5. Review screen-reader behavior and dynamic updates

Reason through what screen-reader and assistive-technology users will experience:

- Confirm dynamic content changes are announced with appropriate live regions, status messages, alerts, or focus changes.
- Avoid over-announcing frequent updates, duplicate labels, hidden decorative text, or hidden content that remains exposed to assistive technology.
- Check loading states, skeletons, search/filter results, pagination changes, async saves, validation results, toasts, notifications, and route transitions.
- Verify hidden content uses the correct mechanism for intent: visually hidden but announced, visually visible but hidden from assistive tech, or removed from all users.
- Ensure virtualized lists, infinite scrolling, data grids, and custom selects preserve names, roles, states, counts, and predictable navigation.

### 6. Review motion, timing, and reduced-motion handling

Check whether time and animation create barriers:

- Verify animations, transitions, parallax, auto-playing media, carousels, skeleton shimmer, and scroll effects respect `prefers-reduced-motion` or repository equivalents.
- Ensure users can pause, stop, hide, extend, or avoid auto-advancing content and time limits unless the time limit is essential.
- Check that flashing, blinking, and rapid visual updates do not create seizure or vestibular risks.
- Confirm focus is not moved unexpectedly by animations, delayed rendering, route transitions, or auto-dismiss behavior.

### 7. Review images, icons, alt text, and decorative content

Check non-text content alternatives and decorative handling:

- Verify informative images have concise, context-appropriate alt text or adjacent accessible descriptions.
- Ensure decorative images and icons are hidden from assistive technology without removing visible meaning for sighted users.
- Check icon-only buttons and links for accessible names that describe the action, not the icon shape.
- Review logos, charts, diagrams, screenshots, avatars, user-generated images, QR codes, CAPTCHA alternatives, and file previews for appropriate text alternatives.
- Ensure SVGs do not expose stray file names, paths, duplicate titles, or meaningless groups to screen readers.

### 8. Recommend tests using existing tooling

Prefer repository-supported checks over generic commands. Look for and use existing evidence from:

- Package scripts and configs for linting, typechecking, unit tests, component tests, Playwright, Cypress, Storybook, Axe, jest-axe, Testing Library, pa11y, Lighthouse, eslint-plugin-jsx-a11y, stylelint accessibility plugins, or framework-specific a11y tooling.
- Existing test files and patterns near the reviewed component or route.
- CI workflows and documented verification commands.

Recommend the narrowest meaningful automated checks plus required manual checks. Include exact commands only when supported by repository evidence. Always distinguish:

- **Automated:** static lint, component assertions, Axe scans, route smoke tests, contrast tooling, story accessibility checks.
- **Manual keyboard:** tab order, activation keys, escape paths, focus restoration, visible focus, shortcut conflicts.
- **Manual screen reader:** at least one desktop and/or mobile screen reader appropriate to the product when feasible.
- **Visual/manual design:** contrast measurement, zoom/reflow, reduced motion, forced-colors/high-contrast mode, non-color state recognition.

## Severity Guidance

Classify findings by user impact and confidence:

- `blocker`: Prevents completion of a core task for keyboard, screen-reader, low-vision, motion-sensitive, or cognitive-accessibility users.
- `high`: Creates a major barrier, misleading assistive-technology output, inaccessible validation, lost focus, insufficient contrast for essential content, or no accessible alternative.
- `medium`: Degrades efficiency or clarity, affects secondary flows, or relies on assumptions that need targeted verification.
- `low`: Minor polish, redundant output, documentation gap, or a best-practice improvement with limited direct user impact.

Use confidence labels such as `high`, `medium`, or `low` when evidence is incomplete. Do not reduce severity merely because automated tooling did not catch the issue.

## Output Format

Use this structure unless the user asks for another format:

```markdown
## Accessibility Review Scope
- Target:
- Comparison source:
- Evidence inspected:
- Tooling detected:
- Limitations:

## Findings
| Severity | Area | Finding | User impact | Evidence | Recommendation |
| --- | --- | --- | --- | --- | --- |
| high | Keyboard | ... | ... | ... | ... |

## Checklist Coverage
- Semantic structure and keyboard navigation: Covered / Not applicable / Needs manual verification
- Labels, roles, names, focus management, and form errors: Covered / Not applicable / Needs manual verification
- Color contrast and non-color affordances: Covered / Not applicable / Needs manual verification
- Screen-reader behavior and dynamic updates: Covered / Not applicable / Needs manual verification
- Motion, timing, and reduced-motion handling: Covered / Not applicable / Needs manual verification
- Images, icons, alt text, and decorative content: Covered / Not applicable / Needs manual verification
- Test recommendations using existing tooling: Covered / Not applicable / Needs manual verification

## Recommended Verification
1. Command or check: `...`
   - Type: Automated / Manual keyboard / Manual screen reader / Visual manual
   - Expected evidence:
   - If unavailable locally:

## Open Questions / Assumptions
- ...
```

For JSON output, include equivalent fields for scope, findings, checklist coverage, recommended verification, limitations, and assumptions.

## Guardrails

- Prefer native semantics and repository conventions over generic ARIA-heavy rewrites.
- Do not invent file paths, scripts, design tokens, routes, or testing tools that are not supported by evidence.
- Do not claim WCAG conformance, legal compliance, or certification from partial review evidence.
- Do not rely solely on automated scanners; note manual keyboard and screen-reader checks for interaction-heavy UI.
- Do not expose secrets, private user data, or sensitive screenshots in the report.
- Do not modify source files, generated assets, pull requests, issues, labels, branches, or deployment state unless the user explicitly asks for implementation rather than review.
