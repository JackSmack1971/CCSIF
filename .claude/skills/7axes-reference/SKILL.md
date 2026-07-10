---
name: 7axes-reference
description: Use when performing any 7-Axes axis audit, validating auditor JSON output, or synthesizing 7-Axes results, as the shared reference for axis definitions, scoring anchors, rule ID taxonomy, and the strict JSON output contract. Trigger on queries that say what is the 7 axes rule id format, 7 axes scoring anchors, 7 axes JSON contract, or axis severity levels. NOT for running the audit itself use 7axes-audit instead. Distinct keywords rule id taxonomy, scoring anchors, severity levels, coverage claimed, acceptance criteria.
when_to_use: Load as the shared reference when authoring or validating a 7-Axes axis auditor or synthesizing axis JSON outputs; it is not invoked directly to run an audit.
argument-hint: "(reference only, no invocation arguments)"
allowed-tools: Read
---

# 7-Axes Reference (ISO/IEC 25010 + DORA/SPACE aligned)

## Axes & Rule ID Prefixes

| Axis | Rule prefix | Core question |
|---|---|---|
| readability | RD- | Can a new engineer understand this in one pass? |
| maintainability | MT- | How expensive is safe change? (coupling, duplication, dead code) |
| reliability | RL- | Does it fail loudly, partially, and recoverably? (error handling, edge cases) |
| security_compliance | SC- | Injection, secrets, authz, unsafe deps, data handling |
| performance_scalability | PF- | Hot paths, N+1, unbounded growth, blocking I/O |
| testability_coverage | TS- | Can behavior be verified? Seams, determinism, coverage gaps |
| operability_observability | OP- | Can prod issues be diagnosed? Logs, metrics, config, health |

## Rule IDs
`<PREFIX>-<kebab-slug>`, e.g. `RL-unhandled-promise`, `SC-hardcoded-secret`, `MT-duplicate-export`. Reuse the same rule_id for the same class of problem — rule IDs are the unit of precision learning; inventing synonyms breaks calibration.

## Scoring Anchors (0–10)
- **9–10**: exemplary; findings are polish only
- **7–8**: solid; scattered medium findings, no systemic pattern
- **5–6**: systemic weaknesses in ≥1 area of the axis
- **3–4**: axis actively causing incidents/velocity loss
- **0–2**: critical exposure (esp. security/reliability)

## Severity
`critical` (exploitable / data loss / crash in main path) · `high` (likely prod impact) · `medium` (debt with clear cost) · `low` (worth fixing opportunistically) · `info`.

## MANDATORY Output Contract (return ONLY this JSON, no prose, no fences)

```json
{
  "axis": "<axis_name>",
  "score": 6.5,
  "coverage_claimed": ["src/api/**", "src/lib/auth.ts"],
  "findings": [
    {
      "rule_id": "SC-hardcoded-secret",
      "severity": "high",
      "title": "API key committed in config",
      "file": "src/config.ts",
      "line": 42,
      "snippet": "const KEY = 'sk-live-...'",
      "description": "1–3 sentences: what, why it matters, blast radius.",
      "recommendation": "Concrete fix approach a PR agent can execute.",
      "acceptance_criteria": ["Secret moved to env", "Key rotated", "gitleaks passes"],
      "status": "new",
      "related_files": []
    }
  ],
  "top_strengths": ["...max 3..."]
}
```

Contract rules:
1. `status`: `new` for anything not in your brief's `known_open_findings`; for known findings report ONLY `still_present` or `resolved` — do not re-describe them.
2. `coverage_claimed` must list ONLY globs you actually examined deeply. It drives resolution detection and next-run rotation; overclaiming corrupts the ledger.
3. `snippet` ≤ 400 chars, verbatim from the file (it feeds content-addressed fingerprinting).
4. Every `critical`/`high` finding MUST include `acceptance_criteria` — downstream PR agents treat it as definition of done.
5. Respect `suppressed_rules` from your brief: report those patterns only with qualitatively new evidence, and say why in `description`.

## Usage checklist

- [ ] Confirm the axis name and its rule prefix before assigning any `rule_id`.
- [ ] Reuse an existing `rule_id` for the same problem class instead of inventing a synonym.
- [ ] Return only the JSON contract — no prose, no fences.
- [ ] Include `acceptance_criteria` for every `critical` or `high` finding.
- [ ] List `coverage_claimed` as only the globs actually examined deeply.

**Stop condition:** stop and return an error instead of the JSON contract if the caller's brief is missing an `axis` name or a required rule prefix.
