# KPI Defaults by Component Type

Use these when the user has not supplied custom metrics.
Report each KPI as a ratio or percentage where applicable.

---

## CLAUDE.md

| KPI | Definition | Baseline Target |
|-----|-----------|----------------|
| Rule adherence rate | % of tasks where Claude followed all CLAUDE.md constraints without override | ≥ 95% |
| Override attempts | Count of CLAUDE.md rule violations per 10-task window | ≤ 1 |
| Unnecessary escalation rate | % of tasks where Claude asked for clarification when it had sufficient context | ≤ 10% |

---

## skill:\<name\>

| KPI | Definition | Baseline Target |
|-----|-----------|----------------|
| Trigger reliability | % of tasks where skill correctly activated when the request matched its purpose | ≥ 90% |
| Undertrigger rate | % of in-scope tasks where skill failed to fire | ≤ 10% |
| Overtrigger rate | % of out-of-scope tasks where skill fired unnecessarily | ≤ 5% |
| Output quality | % of outputs passing the skill's own verification checklist | ≥ 90% |
| Token efficiency | Average tokens loaded per activation (instructions + references) | ≤ 5,000 |

---

## hook:\<name\>

| KPI | Definition | Baseline Target |
|-----|-----------|----------------|
| Block precision | % of blocked operations that were genuinely dangerous or policy-violating | ≥ 95% |
| False positive rate | % of legitimate operations incorrectly blocked | ≤ 5% |
| Coverage rate | % of targeted operation types actually intercepted by the hook | ≥ 98% |
| Execution latency p95 | 95th-percentile time added to tool calls by hook | ≤ 500 ms |

---

## mcp:\<tool\>

| KPI | Definition | Baseline Target |
|-----|-----------|----------------|
| Tool call success rate | % of calls returning valid, non-error results | ≥ 95% |
| Schema adherence rate | % of calls using correct parameter structure | ≥ 99% |
| Latency p95 | 95th-percentile response time from tool | ≤ 2,000 ms |
| Unauthorized call rate | Count of calls to undeclared or disallowed endpoints per 10-task window | 0 |

---

## Scoring Rubric

```
Score = recurrence_count × kpi_delta_magnitude × reversibility_factor
```

| Variable | Description |
|---|---|
| `recurrence_count` | Raw count of occurrences in the analysis window |
| `kpi_delta_magnitude` | Estimated percentage-point improvement (e.g., `15` for +15 pp) |
| `reversibility_factor` | `1.0` full git revert; `0.7` partial manual rollback; `0.3` hard to reverse |

**Carry forward if:** `Score ≥ 5` OR failure is classified `critical` (data loss, security bypass, Constitution violation, unauthorized external call).

**Rank proposals** by Score descending. When scores are tied, prefer the higher-reversibility proposal.

---

## Estimating KPI Delta

When exact measurement is not available from traces, estimate conservatively:

- **Activation miss (undertrigger):** `delta = (miss_count / window_size) × 100`
- **Activation false positive (overtrigger):** `delta = (fp_count / window_size) × 100`
- **Output quality failure:** `delta = (failure_count / window_size) × 100`
- **Tool failure:** count occurrences; estimate delta relative to target success rate

Always state the estimation method in `KPI Impact`. Example:
```
Trigger reliability: estimated +27 pp
(4 activation_miss events / 15-task window = 26.7%; rounded to 27 pp)
```
