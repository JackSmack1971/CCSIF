# HINDSIGHT docs analysis for CCSIF

This is a repo-grounded read of the HINDSIGHT docs under
`.claude/docs/Hindsight-memory-architecture/` against the current CCSIF
implementation.

## What the docs require

1. Epistemic clarity through four distinct networks.
2. Temporal awareness through timestamped facts and point-in-time retrieval.
3. Entity-aware reasoning through graph links and multi-hop discovery.
4. Preference consistency through CARA-style behavioral parameters.
5. A three-step lifecycle: Retain, Recall, Reflect.
6. Opinion confidence reinforcement over time.
7. Observation synthesis that stays neutral and persona-free.

## Doc-by-doc review

| Doc | Main claim | Repo alignment |
|---|---|---|
| `The Four Pillars of HINDSIGHT Memory Architecture.txt` | Defines the four core design principles. | Mostly aligned at the scaffold level; the repo now has separate world/experience/observation/opinion paths, but only the first two are grounded in actual graph semantics. |
| `The World Network_ HINDSIGHT’s Foundation of Objective Reality.txt` | World facts are objective evidence about the environment. | Partially aligned; `hindsight.py` writes `world` records, but the live backend is optional and not yet verified end to end. |
| `The Experience Network_ HINDSIGHT's Biographical Memory Core.txt` | Experience facts are first-person biographical records. | Partially aligned; `experience` records exist and are written in first person. |
| `The Observation Network_ Objective Synthesis in HINDSIGHT Memory Architecture.txt` | Observations are neutral, entity-focused summaries refreshed asynchronously. | Mostly aligned; the runtime now refreshes observations from the live Graphiti path when available and still falls back to local synthesis when it is not. |
| `The Opinion Network_ Architecting AI Subjectivity.txt` | Opinions carry confidence and evolve with evidence. | Mostly aligned; opinion records now carry explicit evidence scores and separate support/contradiction counts. |
| `The HINDSIGHT Architecture_ Entity-Aware Reasoning and Memory Graphs.txt` | Retrieval should work by entity resolution and multi-hop graph traversal. | Partially aligned; Graphiti search is wired, but the bespoke graph reasoning described in the doc is not fully built. |
| `HINDSIGHT Memory Architecture_ The Recall Operation and TEMPR Pipeline.txt` | Recall is token-budgeted, hybrid, and reranked. | Partially aligned; recall exists and uses Graphiti when present, but the repo does not yet prove the full live retrieval path. |
| `The Cognitive Mechanics of HINDSIGHT Memory Architecture.txt` | Retain, recall, reflect form a cognitive loop. | Mostly aligned at the workflow level; the hooks and skills exist, but the loop is still shallow compared to the spec. |
| `Epistemic Clarity in the HINDSIGHT Memory Architecture.txt` | The system must keep evidence, synthesis, and opinion separate. | Mostly aligned structurally; the repo separates these paths, though enforcement still relies on convention and simple runtime checks. |
| `HINDSIGHT-for-CCSIF-Implementation-Plan.md` | Maps the spec onto CCSIF and Graphiti. | This is the strongest repo-grounded doc and matches the current implementation direction; it is still a plan, not a completed verification artifact. |

## What CCSIF already has

- `HINDSIGHT` hook and skill scaffolding in `.claude/`.
- A memory runtime in `.claude/memory/hindsight.py`.
- A Graphiti-aware MCP wrapper in `.claude/memory/hindsight_mcp.py`.
- Recall and observe hooks in `.claude/hooks/`.
- Hindsight rules, skills, and a reflect agent scaffold.
- A trace corpus already written by existing hooks.

## What is implemented vs the docs

| Requirement | Current state | Notes |
|---|---|---|
| Four logical networks | Partially implemented | The runtime distinguishes `world`, `experience`, `observation`, and `opinion` records with separate `group_id`s. |
| Temporal awareness | Partially implemented | Trace records carry timestamps, but the repo still uses simple local ranking when Graphiti is unavailable. |
| Entity-aware reasoning | Partially implemented | The code builds entity hints and uses Graphiti search when available, but there is no full custom spreading-activation layer. |
| Preference consistency | Partially implemented | `persona-profile.md` and `reflect-agent.md` exist, but the opinion logic remains lightweight. |
| Retain | Implemented at scaffold level | Hooks call `hindsight.py retain`, which can write local records and optionally add Graphiti episodes. |
| Recall | Implemented at scaffold level | `hindsight-recall.sh` and `hindsight.py recall` exist. |
| Reflect | Implemented at scaffold level | `reflect-agent.md` and `hindsight.py reflect` exist. |
| Opinion reinforcement | Implemented minimally | `reinforce()` is deterministic and bounded, but not a richer belief model. |
| Neutral observation synthesis | Implemented minimally | `observe()` summarizes world/experience facts without persona input. |

## Notes by theme

- The docs are internally consistent. They all describe the same architecture
  from different angles.
- The repo already reflects the intended decomposition, but most of the hard
  semantics are still aspirational.
- The implementation plan is accurate about what Graphiti can cover and what
  must remain CCSIF-native.
- The live backend work is the right next step if the goal is to move from
  documentation alignment to runtime proof.

## Live Graphiti backend status

The repo now supports a live Graphiti path by setting `HINDSIGHT_BACKEND=graphiti`
and providing Neo4j, LLM, and Voyage values via `.claude/memory/.env`.
`python .claude/memory/hindsight.py graphiti-check` performs the runtime probe.

Required environment surface:

- `NEO4J_URI`
- `NEO4J_USER`
- `NEO4J_PASSWORD`
- `NEO4J_DATABASE`
- `HINDSIGHT_LLM_API_KEY` or `OPENAI_API_KEY`
- `HINDSIGHT_LLM_MODEL`
- `HINDSIGHT_LLM_SMALL_MODEL`
- `HINDSIGHT_LLM_BASE_URL`
- `HINDSIGHT_LLM_TEMPERATURE`
- `VOYAGE_API_KEY`
- `VOYAGE_EMBEDDING_MODEL`
- `VOYAGE_EMBEDDING_DIM`

## Gaps that remain

- The docs describe richer Graphiti-backed retrieval than the current repo
  delivers when Graphiti is unavailable, so the local fallback remains a
  deliberate ceiling.
- The Observation Network now refreshes from the live Graphiti client when the
  backend is configured, while keeping the local projection as a fallback.
- The Opinion Network now carries explicit evidence scores and, as of this
  pass, persists and reinforces belief across calls (see below) rather than
  resetting to a fresh estimate every time — but it is still a deterministic
  exponential-moving-average update, not a probabilistic belief graph.
- There is now a dedicated `graphiti-check` runtime command that proves the live
  Graphiti backend is reachable from this workspace when the environment is
  configured.

## CARA persona conditioning and opinion reinforcement (this pass)

Previously `persona-profile.md` was inert prose — nothing in `hindsight.py`
read it, and `build_opinion_record` recomputed each opinion from a fresh
Bayesian-style prior of `0.5` on every `reflect` call, so confidence never
actually accumulated across turns despite the Opinion Network's spec calling
for evolving belief. This is now wired end to end:

- `load_persona()` parses `.claude/rules/persona-profile.md`'s
  `skepticism` / `literalism` / `empathy` / `bias_strength` values (falling
  back to `0.5` defaults if the file is absent or a key is missing).
- `find_latest_opinion(query)` looks up the most recent persisted opinion for
  a normalized entity/query string in `state/opinions.jsonl`.
- `build_opinion_record` now reinforces that prior via the existing
  deterministic `reinforce()` function instead of recomputing from scratch:
  `skepticism` dampens how much one evidence batch can move belief,
  `bias_strength` controls the effective learning rate (higher bias =
  slower revision). With no matching evidence the prior confidence holds
  steady rather than drifting.
- `_render_reflect` reports the before/after confidence in its output
  (`Confidence reinforced: 0.60 -> 0.68`) so the reinforcement is directly
  observable, not just internal state.
- Observation and Opinion records now carry a `source_refs` list that chains
  back to the underlying World/Experience trace pointers (or to the prior
  derived record's own `source_refs`), instead of the previous
  `source_trace="derived"` dead end — closing part of the "Preference
  consistency" and traceability gap noted above.
- Regression coverage: `.claude/memory/tests/test_hindsight.py` now asserts
  persona parsing/defaults, cross-call reinforcement (confidence moves up on
  repeated supporting evidence rather than resetting), steady-state behavior
  when no matching evidence exists, and provenance chaining from an
  Observation into a derived Opinion.

What is still not built: a richer probabilistic belief model (this remains a
bounded EMA by design, per the original implementation plan).

`literalism` and `empathy` now have distinct, deliberately separate homes:

- `literalism` gates `find_latest_opinion(query, persona)`'s entity match in
  `hindsight.py`. A score of `1.0` requires the normalized query to exactly
  match a prior opinion's entity string (the historical behavior); lower
  values accept a looser token-overlap match, so a low-literalism persona
  reuses/reinforces a prior opinion for a paraphrased query while a
  high-literalism persona treats it as a fresh, unrelated opinion. This is a
  mechanical, testable effect on `opinions.jsonl` state
  (`.claude/memory/tests/test_hindsight.py`).
- `empathy` deliberately has no hook anywhere in `hindsight.py`'s confidence
  pipeline. The spec gives no basis for a numeric confidence effect, so
  forcing one in would be invented behavior. Instead it is wired as a
  response-composition instruction in `.claude/agents/reflect-agent.md`:
  it shapes only how the reflect agent phrases the opinion text it presents
  (acknowledging stakes vs. stating things bluntly), never the confidence
  score computed by `hindsight.py`.

Note on `skepticism`: the source doc's own example describes skepticism
shaping opinion *valence* — "a highly skeptical agent reviewing the exact
same objective facts would form a completely opposite, critical opinion"
(`The Opinion Network_ Architecting AI Subjectivity.txt`) — not the *speed*
of belief revision. The current implementation maps `skepticism` to
`scaled_score = evidence_score * (1.5 - skepticism)` in
`build_opinion_record()`, i.e. skepticism dampens how far one evidence batch
can move confidence (inertia), while `bias_strength` sets the effective
learning rate. That's a defensible, mechanically cleaner interpretation, but
it is a divergence from the spec's own example, not a direct implementation
of it — a future reader should not assume this mapping is literal.

## Bottom line

The docs and the repo now agree on the shape of the system, and the live
Graphiti backend now has a dedicated connectivity check in this workspace.
The durable part is in place, and the Opinion Network's "confidence evolves
with evidence" requirement is now real (persisted, persona-conditioned
reinforcement) rather than aspirational. All four CARA parameters now have a
defined home: `skepticism` and `bias_strength` shape confidence math in
`build_opinion_record()`, `literalism` gates entity matching in
`find_latest_opinion()`, and `empathy` shapes response tone in
`reflect-agent.md` only. The remaining work is to keep a real Neo4j plus
Graphiti plus Voyage environment healthy end to end.
