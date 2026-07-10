---
name: database-migration-review
description: Use when asked to review a database migration, schema change, or ORM migration for safety before merge or deployment. Trigger on review migration, database schema change, ORM migration change, assess SQL migration before deployment. NOT for a framework-detecting protected-area gate that blocks running migration commands outright; use migration-safety instead. Requires classifying each migration operation as expand, backfill, contract, destructive, or index-only before recommending deployment sequencing.
---

# Database Migration Review

## Operating mode: audit first

Treat database migrations as protected areas. Default to review, risk identification, and recommendations rather than editing migration files.

- Do not mutate migration files, generated schema snapshots, production data scripts, or ORM-generated migration artifacts unless the user explicitly approves that exact mutation.
- If a fix is needed, first describe the risk, the proposed change, and any operational assumptions.
- Prefer comments, review notes, checklists, or separate follow-up patches over direct edits to applied or shared migrations.
- Preserve existing migration history unless the user confirms the migration is unapplied and safe to rewrite.

## Review workflow

1. Identify the database engine, migration framework, ORM, deployment topology, and whether the migration has already run anywhere.
2. Inspect the migration files, ORM models/schema files, generated clients/snapshots, and application code paths that read or write affected tables.
3. Classify each operation as expand, backfill, contract, destructive, data-only, index-only, or constraint-only.
4. Evaluate compatibility across old app + old schema, old app + new schema, new app + old schema, and new app + new schema.
5. Call out risks with severity, evidence, likely failure mode, and a safer alternative.
6. Recommend validation commands, staging checks, explain plans, and deployment sequencing.

## Checklist

### 1. Ordering and reversibility

- Verify migrations are ordered deterministically and dependencies appear before consumers.
- Check whether rollback/down migrations truly restore data shape, constraints, indexes, triggers, and defaults.
- Flag irreversible operations such as dropping columns/tables, destructive type casts, data rewrites, truncation, or lossy transforms.
- Ensure generated migration names/timestamps match framework expectations and do not conflict with existing migrations.
- Distinguish “technically reversible” from “operationally safe to roll back after app traffic has written new data.”

### 2. Backward and forward compatibility

- Confirm the migration supports rolling deploys, blue/green deploys, canaries, and delayed workers where old and new application versions may run concurrently.
- For renames, prefer expand-and-contract: add new object, dual-write or backfill, switch reads, then remove old object later.
- Verify old code tolerates added columns, defaults, constraints, enum values, indexes, triggers, and table changes.
- Verify new code tolerates the previous schema until migration completion when deploy order is not strictly guaranteed.
- Check background jobs, queues, read replicas, reporting jobs, API consumers, and cached/generated ORM clients.

### 3. Backfills, locking, long-running operations, and online safety

- Identify table size, write volume, replication lag sensitivity, and maintenance-window assumptions.
- Flag table rewrites, full-table scans, blocking DDL, exclusive locks, large transactions, and unbounded updates/deletes.
- Prefer batched, idempotent, resumable backfills with progress tracking, rate limits, and safe retry behavior.
- Separate schema expansion from data backfill from constraint enforcement when the database or framework may lock heavily.
- Recommend online migration features where available, such as concurrent index creation, non-blocking validation, or shadow-copy strategies.
- Check that backfills are safe under concurrent writes and do not overwrite newer application data.

### 4. Index creation and query-plan impact

- Verify new indexes match the actual query predicates, join keys, sort order, selectivity, and uniqueness requirements.
- Check whether indexes are created concurrently or online when required for high-traffic tables.
- Flag redundant, overlapping, unused, or write-amplifying indexes.
- For dropped or changed indexes, inspect affected query paths and recommend before/after `EXPLAIN` or `EXPLAIN ANALYZE` evidence.
- Consider partial, covering, composite, expression, and foreign-key-supporting indexes when appropriate for the database engine.
- Check index build failure handling and whether failed concurrent indexes leave invalid artifacts that require cleanup.

### 5. Nullability, defaults, constraints, and referential integrity

- For new non-null columns, verify a safe sequence: add nullable or with safe default, backfill, validate, then enforce `NOT NULL` if needed.
- Check default values for table rewrite behavior, semantic correctness, and compatibility with old application versions.
- Verify check constraints, unique constraints, foreign keys, cascades, triggers, and enum changes match application invariants.
- Prefer validating constraints after backfill when supported, and flag immediate validation on large existing tables.
- Check foreign-key actions for accidental cascade deletes, orphan creation, deferred validation assumptions, and required supporting indexes.

### 6. Rollback plans and backup assumptions

- Ask what backup, point-in-time recovery, snapshot, or logical export exists before destructive or high-risk migrations.
- Verify rollback instructions cover both schema and application version rollback, including data written during the rollout.
- Flag rollback plans that rely on unavailable backups, restoring entire production databases for small mistakes, or manually reconstructing lost data.
- Recommend dry-run restores, migration rehearsal, row-count checks, checksums, and post-deploy verification for high-risk changes.
- Document when the safer rollback is forward-fix rather than down-migration.

### 7. ORM model and schema drift

- Compare migrations with ORM models, schema definitions, generated clients, type definitions, fixtures, factories, and seed data.
- Check that renamed fields, relations, enums, defaults, nullability, and constraints agree between database and ORM metadata.
- Verify generated artifacts are updated and compatible with CI, local development, and deployed services.
- Flag drift between raw SQL migrations and ORM-managed schema snapshots.
- Check that application validations do not contradict database constraints, and database constraints do not break existing app assumptions.

## Output format

Provide review findings in priority order:

- **Severity**: blocker, high, medium, low, or note.
- **Area**: ordering, compatibility, online safety, indexing, constraints, rollback, or ORM drift.
- **Evidence**: cite the migration/model/query path inspected.
- **Risk**: describe the failure mode and affected deployment scenario.
- **Recommendation**: give the safest next step, including whether explicit approval is required before mutation.

End with an explicit approval gate when changes to migrations are requested or implied: “Migration files are protected; I will not modify them unless you explicitly approve the proposed mutation.”
