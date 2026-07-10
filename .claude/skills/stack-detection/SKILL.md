---
name: stack-detection
description: Use when classifying the desktop client stack before an architectural or client-layer change. Trigger on classify the desktop stack, detect tauri versus docs-first scaffold, check if the client is buildable, pick a follow-on client review skill. NOT for a generic non-Tauri repository stack detection; use plain repository inspection instead. Requires classifying the project as docs-first-scaffold, tauri-desktop-app, or mixed-or-partial before further review.
disable-model-invocation: false
user-invocable: true
when_to_use: Use to classify the desktop client stack before architectural or client-layer changes, not for a generic non-Tauri repository stack detection.
argument-hint: "(no arguments; inspects the current repository's client stack)"
allowed-tools: Read, Grep, Glob
---

# Stack Detection

## Checklist

- [ ] Inspect `package.json` or other frontend build manifests.
- [ ] Inspect `src-tauri/Cargo.toml` and Rust entrypoints.
- [ ] Inspect `src-tauri/tauri.conf.json`.
- [ ] Inspect `docs/` and `.planning/`.
- [ ] Inspect the actual source tree under `src/` and `src-tauri/src/`.
- [ ] Verify the classification against at least two independent evidence files before reporting; re-classify if evidence conflicts.

**Stop condition:** stop and report `mixed-or-partial` with the specific conflicting evidence instead of guessing when the manifest and source-tree signals disagree.

Inspect:

- `package.json` or other frontend build manifests
- `src-tauri/Cargo.toml` and Rust entrypoints
- `src-tauri/tauri.conf.json`
- `docs/` and `.planning/`
- the actual source tree under `src/` and `src-tauri/src/`

Classify:

- `docs-first-scaffold`: architecture is described in docs but not yet enforced by runnable app code
- `tauri-desktop-app`: backend/runtime wiring is present and the app is buildable
- `mixed-or-partial`: the project has some runtime wiring but still carries important scaffold gaps

Output:

- Chosen classification
- Evidence files
- Missing build or runtime manifests
- Follow-on skill suggestions:
  - `privacy-boundary-review`
  - `provider-routing-review`
  - `storage-recovery-review`
  - `release-evidence-review`

