---
name: migration-safety
description: Use when reviewing database migrations, schema changes, or data backfills before merge, deploy, or rollback across Rails, Django, Prisma, Alembic, Knex, Flyway, or Liquibase. Trigger on is this migration safe to deploy, check migration rollback readiness, detect migration framework and lock risk, review schema or data backfill safety. NOT for a lightweight expand backfill contract classification checklist without framework detection; use database-migration-review instead. Requires explicit user approval before creating, editing, applying, reverting, or regenerating any migration or running a migration command.
user-invocable: true
context: fork
agent: Explore
when_to_use: Use before merging, deploying, generating, applying, reverting, or reviewing database migrations or schema/data changes.
argument-hint: "[--changed-only] [--base REF] [--risk-only]"
allowed-tools: "Read Grep Glob Bash(pwd:*) Bash(git status:*) Bash(git rev-parse:*) Bash(git diff:*) Bash(git show:*) Bash(git log:*) Bash(find:*) Bash(rg:*)"
disallowed-tools: "Write Edit Bash(rails db:migrate:*) Bash(rails db:rollback:*) Bash(rake db:migrate:*) Bash(python manage.py migrate:*) Bash(prisma migrate:*) Bash(alembic upgrade:*) Bash(alembic downgrade:*) Bash(knex migrate:*) Bash(flyway migrate:*) Bash(flyway undo:*) Bash(liquibase update:*) Bash(liquibase rollback:*) Bash(psql:*) Bash(mysql:*) Bash(sqlite3:*)"
---

# Migration Safety

## Contents

- [Purpose](#purpose)
- [Protected-area rules](#protected-area-rules)
- [Inputs](#inputs)
- [Procedure](#procedure)
- [Checklist](#checklist)
- [Output format](#output-format)
- [Stop conditions](#stop-conditions)

## Purpose

Review database migration safety before code review, merge, or deployment. Identify migration frameworks, schema/data change risks, application compatibility issues, rollout sequencing requirements, and rollback readiness.

Database migrations are a **protected area**. Unless the user gives explicit approval for the exact action, do **not** create, edit, regenerate, apply, roll back, squash, reorder, or otherwise modify migration files or database state. Default to read-only review and recommendations.

## Protected-area rules

- Treat all database migration files, schema dumps, migration metadata, and migration commands as protected.
- Require explicit approval before applying any change that affects database schema, database data, migration history, generated schema files, or migration files.
- Do not run migration commands against local, staging, production, or ephemeral databases without explicit approval.
- Do not make “safe-looking” migration edits opportunistically. Report the proposed patch and wait for approval.
- If approval is granted, restate the approved scope, target environment, command, and rollback plan before proceeding.
- If approval is ambiguous, stop and ask for clarification.

## Inputs

Parse optional arguments as:

- `--changed-only`: inspect only files changed in the working tree or current branch.
- `--base REF`: compare migrations and application code against the specified base ref.
- `--risk-only`: produce only the risk rating, blockers, and rollback checklist.

Reject unknown flags. If no base is supplied, infer the comparison base from repository context and label the inference.

## Procedure

### 1. Establish repository and diff context

1. Confirm the repository root with `git rev-parse --show-toplevel`.
2. Check working tree state with `git status --short`.
3. Identify changed migration, schema, model, persistence, and deployment files using `git diff --name-only`, `git diff --cached --name-only`, and, when relevant, `git diff --name-only BASE...HEAD`.
4. Inspect project documentation and operational playbooks for migration policies, deploy ordering, online DDL requirements, maintenance windows, and rollback procedures.

### 2. Detect migration directories and frameworks

Search for migration evidence using file names, directories, manifests, lockfiles, and framework configuration. Common patterns include:

- **Rails / Active Record**: `db/migrate/**`, `db/schema.rb`, `db/structure.sql`, `config/database.yml`, `Gemfile`, `ActiveRecord::Migration`.
- **Django**: `*/migrations/*.py`, `manage.py`, `settings.py`, `INSTALLED_APPS`, `django.db.migrations`.
- **Prisma**: `prisma/migrations/**`, `prisma/schema.prisma`, `package.json` scripts containing `prisma migrate`.
- **Alembic / SQLAlchemy**: `alembic.ini`, `alembic/env.py`, `versions/*.py`, `op.create_table`, `op.alter_column`.
- **Knex**: `knexfile.*`, `migrations/*.js`, `migrations/*.ts`, `exports.up`, `exports.down`.
- **Flyway**: `db/migration/V*.sql`, `flyway.conf`, `flyway.toml`, `repeatable` migrations named `R__*.sql`.
- **Liquibase**: `changelog.xml`, `changelog.yaml`, `changelog.json`, `db.changelog-*`, `changeset`, `rollback` blocks.
- **Raw SQL / custom**: `migrations/*.sql`, `sql/migrations/**`, `schema/*.sql`, custom migration runners, shell scripts invoking SQL clients.

Record each detected framework, its migration directory, migration ordering convention, current schema artifact, and command surface. If multiple frameworks exist, determine whether they target different databases or represent legacy/current systems.

### 3. Review migration content

For each relevant migration, inspect both the forward and reverse paths where the framework supports them.

Check for:

- **Reversibility**: explicit `down`/rollback logic, Liquibase rollback blocks, Django reversible operations, Rails `change` operations that are actually reversible, and raw SQL rollback scripts.
- **Lock risk**: table rewrites, long transactions, `ALTER TABLE`, `DROP COLUMN`, column type changes, constraint validation, foreign key creation, `NOT NULL` additions, default changes, large table updates, and DDL that blocks writes.
- **Data backfills**: row count assumptions, batching, idempotency, resumability, transaction boundaries, retry behavior, throttling, observability, and separation from schema changes.
- **Index creation**: concurrent/online index options, uniqueness validation strategy, lock behavior, naming, partial indexes, covering indexes, and duplicate index risk.
- **Destructive operations**: `DROP TABLE`, `DROP COLUMN`, `DELETE`, `TRUNCATE`, irreversible type conversions, enum value removal, constraint tightening, sequence resets, data format rewrites, and column renames that break older code.
- **Deploy sequencing**: ordering between schema changes, application deployment, background jobs, feature flags, reads/writes, backfills, and cleanup migrations.
- **Operational guardrails**: timeouts, lock timeout settings, statement timeouts, migration transaction mode, retries, monitoring, and alert thresholds.

Mark a migration as high risk when it combines schema mutation, large data movement, and application behavior changes in a single deploy step.

### 4. Check application/schema backward compatibility

Compare migration changes with application code that reads or writes the affected schema.

Verify:

- New nullable columns or tables can be deployed before code writes to them.
- New non-null, unique, or foreign-key constraints do not reject data written by the currently deployed application version.
- Renamed columns, removed columns, changed enum values, and type changes are compatible with both old and new application versions during rolling deploys.
- Reads tolerate missing new columns until migrations complete, especially in multi-instance deployments.
- Writes are dual-written or feature-flagged when both old and new schemas must coexist.
- ORM schema artifacts, generated clients, model validations, serializers, API contracts, GraphQL schemas, fixtures, factories, and tests are consistent with the migration.
- Background jobs, queues, ETL, analytics, reports, admin scripts, and cron tasks are compatible with the intermediate schema state.

Flag any migration that requires all app instances to switch atomically unless the deployment environment actually guarantees atomic cutover.

### 5. Recommend expand/contract rollout patterns

When a change is risky or not backward compatible, recommend an expand/contract sequence. Typical patterns:

- **Additive expand**: add nullable column/table/index first; deploy code that can read old and new schema.
- **Dual write**: write to both old and new locations behind a feature flag; monitor parity.
- **Backfill**: run a separate, batched, idempotent backfill outside the critical deploy path.
- **Read switch**: gradually switch reads to the new schema after backfill validation.
- **Constraint validation**: add constraints as non-valid/not enforced when supported, clean data, then validate/enforce later.
- **Contract cleanup**: remove old columns/tables/code only after all deployed versions and jobs no longer depend on them.
- **Online index strategy**: create indexes concurrently or with the database vendor's online DDL feature where supported.

Prefer multiple small, reversible migrations over one large migration when it reduces lock time, rollback ambiguity, or mixed-version incompatibility.

### 6. Produce risk rating

Assign one overall rating and individual ratings for major findings:

- `low`: additive, reversible, small scope, backward compatible, no meaningful lock or data-loss risk.
- `medium`: manageable operational risk, limited backfill or lock exposure, clear mitigation required, rollback is possible with care.
- `high`: destructive, irreversible, large-table lock/backfill risk, mixed-version incompatibility, weak rollback path, or sequencing uncertainty.
- `critical`: likely data loss, production outage, migration cannot be safely rolled back, or deployment requires unverified manual coordination.

For each non-low risk, include evidence, impact, likelihood, affected files, and recommended mitigation.

### 7. Produce rollback checklist

Always include a rollback checklist. Cover:

- Exact migration version(s), changeset IDs, or SQL files involved.
- Whether rollback is automatic, manual, lossy, or unsupported.
- Commands that would be used for rollback, clearly marked as **do not run without approval**.
- Data backup or snapshot requirements before deployment.
- Restore point, point-in-time recovery, or dump verification requirements.
- How to stop or pause backfills and background jobs.
- How to disable feature flags or revert application code safely.
- Validation queries or application checks to confirm rollback success.
- Owner, approval, and communication requirements for production rollback.

## Checklist

- [ ] Establish repository and diff context.
- [ ] Detect migration directories and frameworks in use.
- [ ] Review migration content for reversibility, lock risk, backfills, indexes, and destructive operations.
- [ ] Check application/schema backward compatibility across rolling deploy states.
- [ ] Recommend expand/contract rollout patterns for risky or incompatible changes.
- [ ] Produce an overall and per-finding risk rating.
- [ ] Produce a rollback checklist.
- [ ] Produce the report using the Output format sections, or stop per Stop conditions.

## Output format

Return Markdown with these sections:

1. `Detected migration systems`
2. `Protected-area status`
3. `Compatibility assessment`
4. `Risk rating`
5. `Findings`
6. `Recommended rollout plan`
7. `Rollback checklist`
8. `Approval required before changes`

Use `blocked`, `high`, `medium`, `low`, or `informational` labels for findings. Include file and line evidence when possible. If no migrations are detected, say so and list the paths and patterns checked.

## Stop conditions

Stop and report instead of proceeding when:

- The user asks to apply, run, edit, regenerate, revert, or squash migrations without explicit approval.
- The target database or environment is unclear for a requested migration action.
- The rollback path is unknown for a destructive migration.
- Required migration files or schema artifacts are generated but missing from the diff.
- Multiple migration frameworks appear to manage the same database and ownership is unclear.
