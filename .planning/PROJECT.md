# CCSIF HINDSIGHT Planning Project

## Project Summary

CCSIF is a repository-local Claude Code control plane with a durable memory
subsystem under `.claude/memory/`. This planning set focuses on the HINDSIGHT
memory architecture described by the repo's docs and implemented by the local
runtime.

## Planning Scope

- Turn the HINDSIGHT docs and current roadmap into a concrete implementation
  plan.
- Keep the local memory runtime as the source of truth for current behavior.
- Preserve the separation between World, Experience, Observation, and Opinion
  memory paths.
- Keep Graphiti as an optional backend until the repo proves a full live setup
  path.

## Source Documents Ingested

- `C:\workspaces\CCSIF\ROADMAP.md`
- `C:\workspaces\CCSIF\CLAUDE.md`
- `C:\workspaces\CCSIF\.claude\docs\Hindsight-memory-architecture\*.txt`
- `C:\workspaces\CCSIF\.claude\docs\Hindsight-memory-architecture\*.md`

## Planning Principles

- Favor the current runtime over aspirational architecture when the docs and
  code diverge.
- Keep every phase testable and tied to a clear exit criterion.
- Preserve the local-first path so the system remains usable without Graphiti.
- Make provenance and replayability explicit requirements, not implied ones.

## Non-Goals

- Rewriting the HINDSIGHT docs into a product spec.
- Forcing Graphiti to be mandatory for all users.
- Expanding the planning set beyond the HINDSIGHT memory architecture in this
  ingest pass.

