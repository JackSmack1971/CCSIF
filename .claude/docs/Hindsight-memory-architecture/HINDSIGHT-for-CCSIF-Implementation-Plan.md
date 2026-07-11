# Implementing the HINDSIGHT Memory Architecture in CCSIF
### A durable, portable, project-level memory layer for `JackSmack1971/CCSIF`

---

## 0. Grounding notes (read this first)

Before the plan, three honesty checks, because this document is only useful if it's built on real capabilities rather than borrowed confidence:

1. **HINDSIGHT is a design spec, not a shipping product.** Everything in the ten uploaded source documents (Four Pillars, World/Experience/Observation/Opinion networks, TEMPR, CARA, Retain/Recall/Reflect) reads as a coherent architectural *specification*. I have no independent evidence it exists as a named, shipping system anywhere. That's fine — the request is to *implement the spec*, not to install an existing product. Everywhere below, I map spec concepts to real, verifiable infrastructure (mostly Graphiti/Zep, plus documented Claude Code hooks/subagents/skills). Where the spec calls for something no off-the-shelf tool provides (the Opinion Network's confidence math, CARA's personality conditioning), I say so explicitly and design it as new CCSIF-native code rather than pretending a library does it for you.

2. **The uploaded `Claude_Code_Memory_Architecture_Map.md` is not something I'm treating as ground truth.** It describes an alleged March 2026 leak of Claude Code's `cli.js.map`, internal modules like `src/memdir/`, `autoDream.ts`, and a "KAIROS" subagent. I have no way to verify a source leak occurred, and the module names don't correspond to anything in Anthropic's official docs. I've deliberately **not** built this plan on that document's claims. Instead, everything about actual Claude Code behavior below (hooks, subagents, skills, MCP, `.claude/` layout) is grounded in the current official docs (`code.claude.com/docs`) and in the real CCSIF repository structure, which I fetched directly.

3. **Tooling note on the requested `/official-docs-pack` run.** I ran it against both `code.claude.com/docs` and the Graphiti/Zep docs as instructed. Bun installed fine and the script executed without error, but in both runs its link-discovery logic seeded off unrelated "known docs host" links it found in page chrome (`git-scm.com/downloads/win`, `docs.github.com`) instead of the actual target documentation, so the resulting ZIPs don't contain useful CCSIF/Graphiti reference material. I'm flagging that rather than handing you a ZIP that looks complete but isn't. Everything technical below is instead sourced from direct fetches of the CCSIF repo, the Graphiti/Zep repo and docs, and current Claude Code hooks documentation, cited inline.

With that out of the way — here's the plan.

---

## 1. What CCSIF actually has today

Fetched directly from `github.com/JackSmack1971/CCSIF`:

| Piece | What it is | Relevant because |
|---|---|---|
| `CLAUDE.md` | Repo constitution / operating rules, loaded every session | This is where HINDSIGHT's *design principles* get declared as standing instructions |
| `.claude/settings.json` | Permissions, hook registration, shell allow/deny lists | Where the Graphiti MCP server gets registered, and where hooks get wired |
| `.claude/agents/` | `implementation-agent`, `pr-reviewer`, `upstream-auditor` | Existing subagents that Recall/Reflect need to feed, plus the pattern to clone for new memory subagents |
| `.claude/commands/` | `/create-pr`, `/review-pr`, `/audit-upstream` | Pattern for new slash commands (`/memory-status`, `/reflect`) |
| `.claude/workflows/*.js` | Deterministic JS orchestration scaffolds | Where Retain/Recall/Reflect get sequenced as a workflow, same pattern as `issue-to-pr.js` |
| `.claude/hooks/*.sh` + `hooks/lib/trace-writer.js` | `session-start.sh`, `pre-tool-use.sh`, `post-tool-use.sh`, `stop.sh`, writing JSONL to `.claude/traces/` | **This is already 80% of a Retain pipeline's raw input.** CCSIF is already capturing exactly the kind of session telemetry HINDSIGHT's Retain operation is supposed to ingest — it just isn't being turned into structured memory yet. |
| `.claude/skills/` | `repo-audit`, `self-improve`, `dependency-audit`, `fsv-verify` | Where new skills (`hindsight-retain`, `hindsight-recall`, `hindsight-observe`, `hindsight-reinforce`) get added, following the existing `SKILL.md` convention |
| `.claude/rules/` | Path-scoped behavior rules, e.g. `security.md` | Where the four-network epistemic-clarity rules and the CARA-style persona profile get declared |

The architectural gap is precise: CCSIF has session-scoped, ephemeral, unstructured trace telemetry (JSONL) and no persistent, structured, queryable memory bank. HINDSIGHT is exactly a spec for that missing layer. Nothing needs to be bolted on awkwardly — the four hook points and the skills/agents/rules directories are already the right shape for it.

---

## 2. Substrate choice: why Graphiti, and what it does *not* give you for free

I looked for existing MCP-connected memory systems that could serve as the technical backbone, rather than hand-building a graph database and hybrid retriever from scratch. **Graphiti** (`getzep/graphiti`, Apache-2.0, 27.8k stars, the open-source engine behind Zep's "Zep: A Temporal Knowledge Graph Architecture for Agent Memory" paper) is an unusually close real-world match to HINDSIGHT's *Recall/TEMPR* description:

| HINDSIGHT spec requirement | Graphiti's actual, documented behavior |
|---|---|
| Four-way parallel retrieval: semantic, BM25 keyword, graph spreading-activation, temporal | Graphiti's documented retrieval combines "semantic embeddings, keyword (BM25), and graph traversal" natively, reranked by graph distance |
| Reciprocal Rank Fusion + neural reranker | Graphiti ships a pluggable cross-encoder reranker (OpenAI, Gemini, or custom) over its hybrid search results |
| Timestamp intervals per fact, point-in-time queries | Graphiti's bi-temporal model tracks `t_valid`/`t_invalid` per edge explicitly — this is a direct match, not an analogy |
| Entity resolution + rich graph links (entity/temporal/semantic/causal) | Graphiti performs entity resolution and stores triplets (entity → relationship → entity) with temporal validity windows, and supports custom Pydantic-defined ontologies for edge/node types |
| Provenance / traceability of every fact | Every Graphiti entity and edge traces back to the raw "episode" that produced it — full lineage, which is exactly HINDSIGHT's auditability requirement |
| Async, incremental updates without full recomputation | Graphiti is explicitly built for this — no batch reprocessing |
| Ships as an MCP server for Claude/Cursor/etc. | Confirmed — `mcp_server/` in the Graphiti repo, deployable via Docker |

This means **TEMPR's Retain and Recall halves are close to solved by adopting Graphiti**, rather than needing to be built from scratch. What Graphiti does **not** give you, and what genuinely has to be built as new CCSIF-native logic:

- **The four-network epistemic partition itself.** Graphiti has no built-in concept of "this fact is Objective World, this one is Subjective Opinion." You get to define that structure using Graphiti's `group_id` namespacing and custom ontology types (real, documented Graphiti features) — this is design work, not a missing feature, but it's not automatic.
- **Confidence scores and belief reinforcement math** (the Opinion Network's core mechanic). Nothing in Graphiti tracks "conviction strength" or updates it based on corroborating/contradicting evidence. This has to be hand-written.
- **CARA's personality-conditioned reasoning** (skepticism/literalism/empathy dials that shape how retrieved facts become opinions and responses). This is pure CCSIF-side logic — a persona profile plus a subagent that applies it.
- **The Observation Network's "neutral synthesis excluding the agent's behavioral profile"** — Graphiti will happily summarize an entity's facts, but keeping that summarization *provably uninfluenced* by the persona profile is a process discipline you have to enforce (separate skill, separate model call, no persona injected into that particular prompt).

**Storage backend recommendation for "durable and portable, project-level":** FalkorDB over Neo4j for this use case. Graphiti supports both as documented drivers. FalkorDB has an embedded "Lite" mode (`graphiti-core[falkordblite]`, Python 3.12+) that stores the entire graph as a single file — this is the closest fit to "the memory travels with the git clone" without requiring a standing server process. For a team that wants shared memory across multiple developers' machines, use FalkorDB via `docker-compose` with a named volume instead (Graphiti's repo ships a ready `docker-compose.yml` with a `--profile falkordb` flag) — that trades single-file portability for multi-developer durability. Document both options in the repo and let the team pick; don't force it.

---

## 3. The mapping table

| HINDSIGHT concept | CCSIF / Graphiti implementation |
|---|---|
| **World Network** | Graphiti nodes/edges with `group_id = "ccsif:world"`, custom Pydantic type `WorldFact`. Populated from repo state, PR/issue content, upstream-audit findings — anything about the external environment that isn't the agent's own action. |
| **Experience Network** | `group_id = "ccsif:experience"`, custom type `ExperienceFact`, written in first person ("I implemented issue #142 as PR #89"). Sourced directly from `.claude/traces/*.jsonl` — this is the network CCSIF is already 80% capturing. |
| **Observation Network** | Not a Graphiti-native concept — implemented as a scheduled/triggered synthesis job (new skill `hindsight-observe`) that queries Graphiti for all World+Experience facts mentioning an entity (a file, a dependency, a contributor, a subsystem) and writes back a `ObservationProfile` node, generated with **no persona/opinion input**. |
| **Opinion Network** | `group_id = "ccsif:opinion"`, custom edge type `OpinionBelief(text, confidence: float, formed_at: datetime)`. Written only by the Reflect subagent, never directly by Retain. |
| **Retain (TEMPR)** | Extended `post-tool-use.sh` / `stop.sh` hooks + new skill `hindsight-retain`, calling Graphiti MCP's `add_episode` tool. |
| **Recall (TEMPR)** | New skill `hindsight-recall`, invoked via a `UserPromptSubmit` hook, calling Graphiti's hybrid search tools with an explicit token budget. |
| **Reflect (CARA)** | New subagent `reflect-agent.md`, parallel to the existing `implementation-agent`/`pr-reviewer` agents, conditioned by a versioned persona-profile file. |
| **TEMPR (the component)** | The Graphiti MCP server itself — this is a legitimate, direct match, not an analogy. |
| **CARA (the component)** | Does not exist as a product. Implemented as the combination of `reflect-agent.md` + `.claude/rules/persona-profile.md` + the `hindsight-reinforce` skill's confidence-update function. |

---

## 4. Build plan, component by component

### 4.1 Storage + MCP wiring

Add a project-scoped MCP registration (portable — checked into the repo, not user-local):

```jsonc
// .claude/settings.json (excerpt — add to existing mcpServers block)
{
  "mcpServers": {
    "graphiti-memory": {
      "command": "docker",
      "args": ["compose", "-f", ".claude/memory/docker-compose.graphiti.yml", "run", "--rm", "mcp-server"],
      "env": {
        "GRAPHITI_GROUP_PREFIX": "ccsif",
        "GRAPHITI_TELEMETRY_ENABLED": "false"
      }
    }
  }
}
```

For the "single developer, fully portable" path, skip Docker entirely and run Graphiti's MCP server against embedded FalkorDB Lite from a `uv run` command instead — no daemon, no volume, one file at `.claude/memory/graph.db` (git-ignored by default, like `.claude/traces/`).

Either way, **the LLM/embedding credentials for Graphiti's own extraction pipeline are a separate concern from your Claude Code subscription** — Graphiti needs its own configured LLM client (Anthropic and Gemini are both documented as supported, alongside OpenAI) plus an embedding model (Voyage or OpenAI) for the entity/edge extraction it runs on every episode. Budget for this: extraction is an LLM call per ingested episode, so batch traces rather than streaming every tool call individually.

### 4.2 Ontology — the part that actually implements "four networks"

Graphiti's *prescribed ontology* feature (custom Pydantic node/edge types) is the real mechanism. Define once, in a small versioned module:

```python
# .claude/memory/hindsight_ontology.py
from pydantic import BaseModel, Field
from datetime import datetime

class WorldFact(BaseModel):
    """Objective, perspective-independent fact about the external environment."""
    statement: str

class ExperienceFact(BaseModel):
    """First-person record of the agent's own past action or recommendation."""
    statement: str  # e.g. "I merged PR #89 after pr-reviewer approval"

class ObservationProfile(BaseModel):
    """Preference-neutral synthesized summary of one entity. Never persona-conditioned."""
    entity_name: str
    summary: str
    source_fact_count: int

class OpinionBelief(BaseModel):
    """Subjective judgment, written only by the Reflect subagent."""
    statement: str
    confidence: float = Field(ge=0.0, le=1.0)
    formed_at: datetime
```

`group_id` namespacing does the network-level partitioning (`ccsif:<repo>:world`, `:experience`, `:observation`, `:opinion`), so a Recall query can ask Graphiti for "just objective facts" or "just opinions" without any custom filtering code — this is a native Graphiti capability, not something bolted on.

### 4.3 Retain pipeline

Extend the existing trace-writing hooks rather than replacing them:

```
PostToolUse / Stop hook (existing, unchanged)
        │
        ▼
.claude/traces/YYYY-MM-DD.jsonl  (existing, unchanged — source of truth)
        │
        ▼
hindsight-retain skill (new)
  1. reads new lines since .claude/memory/retain-cursor.json
  2. classifies each narrative fact → World / Experience / Opinion-candidate
  3. calls Graphiti MCP `add_episode`, tagged with source = trace file + line range
  4. queues touched entities for Observation resync
```

Provenance is free here: Graphiti's episode-to-fact lineage plus CCSIF's own trace file/line reference means every stored memory is auditable back to an exact session and tool call — directly satisfying HINDSIGHT's traceability principle without extra bookkeeping.

**Durability guarantee, and why it matters more than the database file itself:** because Retain is a deterministic function of `.claude/traces/*.jsonl`, the graph is a *derived index*, not the source of truth — exactly the posture CCSIF's own README already takes toward `.claude/traces/` ("generated telemetry, not source"). If the graph file is lost, corrupted, or a teammate's machine doesn't have it, it is fully rebuildable by replaying the trace corpus through Retain. That's a stronger durability story than trying to git-commit a binary graph database file.

### 4.4 Recall pipeline

```yaml
# .claude/settings.json hooks excerpt
hooks:
  UserPromptSubmit:
    - hooks:
        - type: command
          command: bash .claude/hooks/hindsight-recall.sh
          timeout: 30
```

`hindsight-recall.sh` calls the `hindsight-recall` skill, which passes a token budget straight to Graphiti's `search_nodes`/`search_facts` MCP tools. Because Graphiti already performs hybrid semantic+BM25+graph-traversal search with cross-encoder reranking internally, there's no separate RRF-fusion layer to hand-build — that part of TEMPR's four-way pipeline is genuinely inherited, not reimplemented. `UserPromptSubmit`'s stdout is documented to be injected as visible context to Claude, which is exactly the mechanism needed to make Recall's output usable without the model having to remember to ask for it.

### 4.5 Reflect layer — the part with no existing tool to lean on

This is where the real engineering is, because nothing upstream provides it:

```markdown
<!-- .claude/rules/persona-profile.md -->
# CARA-style behavioral profile (versioned, portable, applies repo-wide)
skepticism: 0.7      # how much corroboration an Opinion needs before high confidence
literalism: 0.8       # weight given to exact wording vs inferred intent
empathy: 0.4
bias_strength: 0.5    # how much existing opinions resist being overturned by one new fact
```

```markdown
<!-- .claude/agents/reflect-agent.md — new subagent, same pattern as implementation-agent -->
Role: takes Recall's retrieved World/Experience/Observation facts + persona-profile.md,
produces the response, AND produces zero-or-more OpinionBelief candidates with a proposed
confidence score. Never writes directly to the graph — hands candidates to hindsight-reinforce.
```

Confidence reinforcement itself should be a small, deterministic function — not another LLM call, so it's auditable and doesn't drift:

```python
# .claude/memory/hindsight_reinforce.py
def update_confidence(prior_confidence: float, new_evidence_supports: bool,
                       learning_rate: float = 0.2) -> float:
    """Exponential-moving-average style update, bounded to [0,1]."""
    target = 1.0 if new_evidence_supports else 0.0
    return prior_confidence + learning_rate * (target - prior_confidence)
```

This is deliberately simple rather than a full Bayesian model — HINDSIGHT's spec calls for confidence to move up on reinforcement and down on contradiction, and this satisfies that without inventing false precision.

### 4.6 Observation Network — enforcing "neutral synthesis"

The spec's requirement that Observation summaries be generated "without any influence from the agent's behavioral profile" is a process discipline, not a technology: `hindsight-observe` must run as its own skill invocation with a prompt that never includes `persona-profile.md`, triggered asynchronously (e.g. from the `Stop` hook, or a periodic `PreCompact` hook) rather than inline during Reflect — this keeps the "no opinion leakage into observations" boundary structurally enforced rather than just documented.

### 4.7 Rules enforcement

```markdown
<!-- .claude/rules/hindsight-memory.md -->
- Before any non-trivial answer, call hindsight-recall with an explicit token budget.
- Never write to group_id ending in `:opinion` without a confidence score attached.
- hindsight-observe must never receive persona-profile.md in its prompt context.
- Every Retain-written fact must carry a source trace file + line range.
```

---

## 5. Phased rollout

| Phase | Deliverable | Acceptance check |
|---|---|---|
| 0 | Docker/FalkorDB-Lite decision made, Graphiti MCP server registered in `.claude/settings.json` | `claude mcp list` shows `graphiti-memory` connected |
| 1 | Ontology module + `group_id` scheme committed | Manual `add_episode` call lands in the correct namespace |
| 2 | `hindsight-retain` wired to `PostToolUse`/`Stop` | New trace lines produce new World/Experience facts within one session |
| 3 | `hindsight-recall` wired to `UserPromptSubmit` | A prompt referencing a past session surfaces the relevant fact as injected context |
| 4 | `reflect-agent` + `persona-profile.md` + `hindsight-reinforce` | Opinion confidence measurably moves after corroborating vs. contradicting evidence |
| 5 | `hindsight-observe` async job | Querying "tell me about `<entity>`" returns the synthesized profile, not raw fact dumps |
| 6 | Hardening: secret redaction in Retain (reuse existing `trace-writer.js` redaction), cost/concurrency tuning (`SEMAPHORE_LIMIT`), rebuild-from-traces drill | A full graph wipe + replay of `.claude/traces/` reproduces the same World/Experience facts |

---

## 6. Open risks worth checking before you commit to this

- **Ingestion cost.** Graphiti's extraction pipeline is an LLM call per episode. A busy CCSIF repo generating dense `PostToolUse` traces could get expensive fast if you retain every tool call individually rather than batching. Batch, and use a cheap model for extraction.
- **Hook surface keeps expanding.** Current Claude Code docs list roughly two dozen hook events (`SessionStart`, `UserPromptSubmit`, `PreToolUse`, `PostToolUse`, `Stop`, `SubagentStart/Stop`, `PreCompact`, and others), and the exact set has been growing release over release — re-check `code.claude.com/docs/en/hooks` against your installed version before finalizing which hook names this plan uses, rather than trusting this document a year from now.
- **`UserPromptSubmit`'s 30-second default timeout** is tight for a live Graphiti hybrid-search round trip if the server is cold or the graph is large — plan for a warm connection or raise the timeout explicitly in the hook config.
- **FalkorDB Lite requires Python 3.12+** — confirm your CI/dev environment before committing to the single-file "fully portable" path over the Docker path.

---

## 7. What I'd build first if you only do one thing

Phase 2 (Retain) alone, wired to the existing trace hooks, turns CCSIF's already-collected JSONL telemetry into a queryable, structured, auditable fact store — genuinely durable and portable — even before Reflect/Opinion/Observation exist. Everything else in this plan is additive on top of that foundation.
