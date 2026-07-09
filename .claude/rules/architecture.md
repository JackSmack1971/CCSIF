---
name: architecture
description: Architecture boundaries and dependency direction.
globs:
  - "src/**/*.ts"
  - "src/**/*.tsx"
  - "app/**/*.ts"
  - "app/**/*.tsx"
---

# Architecture Rules

- Preserve existing module boundaries.
- Do not introduce cross-layer imports without documenting the dependency direction.
- Keep domain logic independent from transport, UI, and persistence details.
- Add integration tests when changing cross-boundary behavior.
