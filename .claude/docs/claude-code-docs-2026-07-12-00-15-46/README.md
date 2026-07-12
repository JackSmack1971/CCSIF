# Official Documentation Pack

Generated: 2026-07-12T00:15:46.042Z
Request: https://docs.anthropic.com/en/docs/claude-code/overview

This folder contains only pages accepted by the official-docs source policy. Discovery may inspect search or package metadata, but packaged content is limited to verified documentation pages.

## Contents

- Full pages: 80
- Verified seeds: 4
- Skipped/rejected links recorded: 77
- Fetch/extraction failures recorded: 1

## Verified Seed URLs

- https://docs.anthropic.com/en/docs/claude-code/overview (user-url:known-docs-host+docs-shaped-host+docs-shaped-path, root: /en/docs)
- https://docs.anthropic.com/ (known-target:known-docs-host+docs-shaped-host+docs-homepage, root: /)
- https://modelcontextprotocol.io/docs/getting-started/intro (search-result:known-docs-host+docs-shaped-path, root: /docs)
- https://code.claude.com/docs/en/overview (redirect-target-of-verified-seed, root: /docs)

## How Agents Should Use This Pack

1. Read `AGENT_INDEX.md` for navigation.
2. Search `index/chunks.jsonl` for relevant terms.
3. Open the matching `docs/*.md` file for full context.
4. Cite or reason from `source_url` frontmatter, not from memory.

## Source Policy Summary

Accepted content must be first-party documentation, known official documentation, official generated API docs, official repository docs, or documentation URLs from official package metadata. Unofficial tutorials, Q&A, blogs, mirrors, forums, login-gated pages, and binary assets are excluded.
