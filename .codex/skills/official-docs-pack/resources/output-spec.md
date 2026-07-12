# Agent Documentation Pack Output Spec

The output folder (written under `.claude/docs/<slug>-<timestamp>/`) is designed for AI agents that need fast source-grounded retrieval.

## Required Files

| Path | Purpose |
| --- | --- |
| `README.md` | Human and agent entrypoint with request, seed URLs, counts, and source policy summary. |
| `AGENT_INDEX.md` | Compact navigation map with page titles, paths, source URLs, and top headings. |
| `manifest.json` | Machine-readable crawl manifest, including accepted seeds, pages, skipped URLs, failures, and settings. |
| `sources.csv` | Flat source ledger: `path,title,url,host,depth,status`. |
| `index/chunks.jsonl` | One JSON object per retrieval chunk, including `path`, `url`, `title`, `heading`, `chunk_index`, and `text`. |
| `docs/*.md` | Full Markdown extraction for each accepted docs page. |

## Markdown Page Format

Each `docs/*.md` file starts with YAML frontmatter:

```yaml
---
title: "Page title"
source_url: "https://official.example.com/docs/page"
host: "official.example.com"
depth: 1
fetched_at: "2026-07-09T12:00:00.000Z"
---
```

Then the full extracted Markdown page body follows.

## Chunking Rules

- Prefer heading-aware chunks.
- Keep chunks roughly 3,000 to 5,000 characters when possible.
- Preserve source URL, page path, page title, and nearest heading in every chunk.
- Do not summarize or paraphrase inside the chunk index; keep source text.

## Agent Search Guidance

Agents should read `README.md` first, use `AGENT_INDEX.md` for navigation, use `index/chunks.jsonl` for search, and open the matching `docs/*.md` page for full context before making claims.
