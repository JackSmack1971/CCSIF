# Validation Spec

## Package Validation

Run from any directory:

```bash
bash "${CLAUDE_SKILL_DIR}/scripts/validate-skill.sh"
```

Expected success output:

```json
{"status":"pass","checks":[...]}
```

## Static Checks

The validator verifies:

- Skill root name and frontmatter.
- `docpack.ts`, `fetch.ts`, `package.json`, and validation scripts exist.
- Required dependencies are declared: `linkedom`, `turndown`, and `turndown-plugin-gfm`.
- Source-policy and output-spec resources exist.
- The skill description triggers on official docs, documentation packs, folder output, and agent consumption.
- No nested resource chains or hardcoded install paths are present.

## Functional Smoke Tests

Run in a network-capable environment after `bun install`.

### Help text

```bash
bun "${CLAUDE_SKILL_DIR}/scripts/docpack.ts" --help
```

Pass: usage output mentions official docs, `--out-dir`, `--max-pages`, and `--max-depth`.

### Known official docs URL

```bash
bun "${CLAUDE_SKILL_DIR}/scripts/docpack.ts" "https://developer.mozilla.org/en-US/docs/Web/HTTP/Overview" --out-dir /tmp/docs-test --max-pages 3 --json
```

Pass: exits 0, reports `status: ok`, and the JSON `output_dir` field points at a newly created folder under `/tmp/docs-test`.

### Non-docs rejection

```bash
bun "${CLAUDE_SKILL_DIR}/scripts/docpack.ts" "https://stackoverflow.com/questions/11828270/how-do-i-exit-vim" --out-dir /tmp/docs-bad --json
```

Pass: exits non-zero and reports no verified official docs. No folder should be created under `/tmp/docs-bad`.

### Generated folder contents

```bash
python3 - <<'PY'
import pathlib, glob, sys
matches = glob.glob('/tmp/docs-test/*')
assert matches, "no docs folder created"
out = pathlib.Path(matches[0])
required = {'README.md', 'AGENT_INDEX.md', 'manifest.json', 'sources.csv', 'index/chunks.jsonl'}
present = {str(p.relative_to(out)).replace('\\', '/') for p in out.rglob('*') if p.is_file()}
assert required.issubset(present), present
assert any(p.startswith('docs/') and p.endswith('.md') for p in present)
PY
```

Pass: Python exits 0.

## Failure Evidence Template

```text
No official docs pack produced.
Request: <request>
Command: <exact command>
Observed: <short JSON/error excerpt>
Likely cause: <no verified docs|blocked|JS-rendered|dependency missing|HTTP error>
Next safe step: <official docs URL or browser-capable/manual export>
```
