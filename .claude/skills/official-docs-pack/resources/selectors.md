# Selector Reference

`docpack.ts` uses the same content-extraction strategy as `fetch.ts`: choose a high-signal docs container, remove navigation/chrome, convert HTML to GFM Markdown, and preserve links as absolute URLs.

## Built-In Selector Families

| Site family | Include selector | Exclude selector |
| --- | --- | --- |
| Anthropic / Claude docs | `#content-container,main,article` | `nav,header,footer,.sidebar` |
| OpenAI platform docs | `main,article,[role=main]` | `nav,header,footer,.sidebar` |
| MDN | `article` | `nav,header,footer` |
| Python docs | `div.body` | `nav,header,footer,.sphinxsidebar` |
| Rust docs | `main` | `nav,header,footer` |
| Go docs | `main` | `nav,header,footer` |
| Read the Docs | `div.document,.rst-content,main` | `nav,.wy-nav-side,header,footer` |
| MkDocs / Material | `main article,article.md-content__inner,main` | `nav,header,footer,.md-sidebar` |
| Generic docs fallback | `article,main,[role=main]` | `script,style,noscript,template,svg,nav,header,footer` |

## Diagnostics

Use `--debug` to print selector decisions and rejected URL evidence:

```bash
bun "${CLAUDE_SKILL_DIR}/scripts/docpack.ts" "$ARGUMENTS" --debug --max-pages 5 --json
```

## Manual Single-Page Diagnosis

`fetch.ts` remains available for page-level troubleshooting:

```bash
bun "${CLAUDE_SKILL_DIR}/scripts/fetch.ts" "<official-docs-url>" --debug
```

Do not use `fetch.ts` as the final workflow when a ZIP pack is requested.
