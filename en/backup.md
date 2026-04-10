---
layout: default
title: Backup
permalink: /en/backup/
lang: en
alternate_url: /backup/
lead: How to keep Mnemos data safe and restore it after a failure,
  migration, or risky change.
---

# Backup and restore

Mnemos stores the main memory in PostgreSQL and the search index in
Qdrant. For reliable use, it helps to back up both the database and the
full local stack.

## What to back up

- PostgreSQL: memory items, candidates, and pipeline state
- Qdrant: the vector index used for search
- configuration: `.env`, compose files, and local settings

## Recommended strategy

For most cases, use a full stack snapshot:

```sh
make stack-backup
```

The command creates an archive in `backups/`:

```text
backups/mnemos-stack-YYYYMMDD-HHMMSS.tar.gz
```

Restore it with:

```sh
make stack-restore FILE=backups/mnemos-stack-YYYYMMDD-HHMMSS.tar.gz
```

This is the easiest option when you move to another machine, test a
risky change, or want a fast way to bring the whole local stack back.

## PostgreSQL backup

If you only need the database dump:

```sh
make backup
```

By default it creates:

```text
backups/mnemos-postgres-YYYYMMDD-HHMMSS.sql.gz
```

You can also choose the output path directly:

```sh
./scripts/backup_postgres.sh backups/my-postgres.sql.gz
```

Restore it with:

```sh
make restore FILE=backups/mnemos-postgres-YYYYMMDD-HHMMSS.sql.gz
```

or directly:

```sh
./scripts/restore_postgres.sh backups/mnemos-postgres-YYYYMMDD-HHMMSS.sql.gz
```

After a PostgreSQL restore, run a Qdrant reindex:

```sh
make reindex
```

To skip reindex for now:

```sh
SKIP_REINDEX=1 ./scripts/restore_postgres.sh backups/mnemos-postgres-YYYYMMDD-HHMMSS.sql.gz
```

## Qdrant backup

If you only need the search index:

```sh
make qdrant-backup
```

Restore it with:

```sh
make qdrant-restore FILE=backups/mnemos-qdrant-YYYYMMDD-HHMMSS.tar.gz
```

## Configuration backup

To preserve local settings together with the data:

```sh
make config-backup
```

The archive includes `.env`, compose files, and local project settings.

## How to verify recovery

After restore, check:

- `http://localhost:8000/health/live`
- `http://localhost:8000/health/ready`
- search via `POST /memory/query`

If health checks and search work, the restore was successful.

## Things to remember

- `docker compose down -v` removes volumes and can erase data
- a logical PostgreSQL restore does not replace Qdrant reindexing
- a full snapshot is the safest option before risky maintenance

- [Open the FAQ](/mnemos/en/faq/)
- [Open the user guide](/mnemos/en/guide/)
