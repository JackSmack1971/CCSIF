# Official Documentation Pack

Generated: 2026-07-12T00:35:13.395Z
Request: https://neo4j.com/docs/

This folder contains only pages accepted by the official-docs source policy. Discovery may inspect search or package metadata, but packaged content is limited to verified documentation pages.

## Contents

- Full pages: 39
- Verified seeds: 6
- Skipped/rejected links recorded: 163
- Fetch/extraction failures recorded: 1

## Verified Seed URLs

- https://neo4j.com/docs/ (user-url:known-docs-host+docs-shaped-path, root: /docs)
- https://www.neo4j.com/docs/reference/docs-archive/ (search-result:known-docs-host+docs-shaped-path, root: /docs)
- https://neo4j.com/docs/reference/ (search-result:known-docs-host+docs-shaped-path, root: /docs)
- https://neo4j.com/docs/operations-manual/current/ (search-result:known-docs-host+docs-shaped-path, root: /docs)
- https://neo4j.com/docs/getting-started/ (search-result:known-docs-host+docs-shaped-path, root: /docs)
- https://docs.spring.io/spring-data/neo4j/docs/5.0.0.RELEASE/reference/html/ (search-result:docs-shaped-host+docs-shaped-path, root: /spring-data/neo4j/docs)

## How Agents Should Use This Pack

1. Read `AGENT_INDEX.md` for navigation.
2. Search `index/chunks.jsonl` for relevant terms.
3. Open the matching `docs/*.md` file for full context.
4. Cite or reason from `source_url` frontmatter, not from memory.

## Source Policy Summary

Accepted content must be first-party documentation, known official documentation, official generated API docs, official repository docs, or documentation URLs from official package metadata. Unofficial tutorials, Q&A, blogs, mirrors, forums, login-gated pages, and binary assets are excluded.
