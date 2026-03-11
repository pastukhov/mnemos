# Mnemos Backup and Restore Guide

This document describes the backup and restore flows that are actually
implemented in this repository.

Mnemos stores data in three places:

1. PostgreSQL stores memory items, candidates, and pipeline state
1. Qdrant stores vector indexes for search
1. Local configuration files store environment and compose settings

There are two backup strategies in the project:

1. logical backup of PostgreSQL with optional Qdrant reindex later
1. full Docker volume snapshot of PostgreSQL and Qdrant

## 1. Recommended Strategy

Use the full stack snapshot before risky operations such as
`docker compose down -v`, host migration, or destructive experiments.

```sh
make stack-backup
```

The command creates a file in `backups/`:

```text
backups/mnemos-stack-YYYYMMDD-HHMMSS.tar.gz
```

This snapshot includes both Docker volumes used by the running
`postgres` and `qdrant` services.

## 2. PostgreSQL Backup

Create a logical PostgreSQL backup:

```sh
make backup
```

By default it creates:

```text
backups/mnemos-postgres-YYYYMMDD-HHMMSS.sql.gz
```

You can also call the script directly and choose the output path:

```sh
./scripts/backup_postgres.sh backups/my-postgres.sql.gz
```

This backup is compressed and can be restored as `.sql.gz` or `.sql`.

## 3. Qdrant Backup

Create a Qdrant storage backup:

```sh
make qdrant-backup
```

By default it creates:

```text
backups/mnemos-qdrant-YYYYMMDD-HHMMSS.tar.gz
```

You can also call the script directly:

```sh
./scripts/backup_qdrant.sh backups/my-qdrant.tar.gz
```

This backup archives the actual Docker volume mounted at
`/qdrant/storage`.

## 4. Configuration Backup

Create a backup of local configuration files:

```sh
make config-backup
```

The archive includes the files that exist locally from this set:

- `.env`
- `.env.example`
- `.env.local-mock.example`
- `docker-compose.yml`
- `docker-compose.local-mock.yml`
- `config/`

You can also choose the output path directly:

```sh
./scripts/backup_config.sh backups/my-config.tar.gz
```

## 5. Full Backup Bundle

If you want one backup directory with PostgreSQL, Qdrant, and config
archives together, use:

```sh
make full-backup
```

It creates a directory like:

```text
backups/YYYYMMDD-HHMMSS/
  postgres.sql.gz
  qdrant-storage.tar.gz
  config.tar.gz
```

You can also choose the target directory:

```sh
./scripts/backup.sh backups/manual-run
```

## 6. Full Stack Restore

Restore a full Docker volume snapshot:

```sh
make stack-restore FILE=backups/mnemos-stack-YYYYMMDD-HHMMSS.tar.gz
```

Or directly:

```sh
./scripts/restore_stack.sh backups/mnemos-stack-YYYYMMDD-HHMMSS.tar.gz
```

What this restore does:

1. stops `mnemos`, `mnemos-mcp`, `postgres`, and `qdrant`
1. replaces the PostgreSQL and Qdrant Docker volume contents
1. starts the stack again with `docker compose up -d`

This is the most reliable restore path because it does not depend on
recomputing embeddings.

## 7. PostgreSQL Restore

Restore a logical PostgreSQL backup:

```sh
make restore FILE=backups/mnemos-postgres-YYYYMMDD-HHMMSS.sql.gz
```

Or directly:

```sh
./scripts/restore_postgres.sh backups/mnemos-postgres-YYYYMMDD-HHMMSS.sql.gz
```

After restoring the SQL dump, the script automatically runs:

```sh
make reindex
```

This rebuilds Qdrant collections from PostgreSQL records.

If you need to skip reindex temporarily:

```sh
SKIP_REINDEX=1 ./scripts/restore_postgres.sh backups/mnemos-postgres-YYYYMMDD-HHMMSS.sql.gz
```

## 8. Qdrant Restore

Restore a Qdrant backup archive:

```sh
make qdrant-restore FILE=backups/mnemos-qdrant-YYYYMMDD-HHMMSS.tar.gz
```

Or directly:

```sh
./scripts/restore_qdrant.sh backups/mnemos-qdrant-YYYYMMDD-HHMMSS.tar.gz
```

The script stops `qdrant`, replaces the volume contents, and starts the
service again.

## 9. Config Restore

Restore configuration files from a backup archive:

```sh
make config-restore FILE=backups/mnemos-config-YYYYMMDD-HHMMSS.tar.gz
```

Or directly:

```sh
./scripts/restore_config.sh backups/mnemos-config-YYYYMMDD-HHMMSS.tar.gz
```

This extracts files into the repository root.

## 10. Validate Restore

Check service readiness:

```sh
curl http://localhost:8000/health
```

Expected response:

```json
{"status":"ready","checks":{"postgres":"ok","qdrant":"ok"}}
```

Check that search still works:

```sh
curl -X POST "http://localhost:8000/memory/query" \
  -H "Content-Type: application/json" \
  -d '{"query":"test","domain":"self","top_k":3}'
```

If the API returns search results, restore was successful.

## 11. Operational Recommendations

For local or small-team use:

1. run `make stack-backup` before risky maintenance
1. keep backup files outside the machine where possible
1. keep several recent backups instead of only one
1. test a real restore periodically

Especially dangerous command:

```sh
docker compose down -v
```

This removes Docker volumes and can erase PostgreSQL and Qdrant data.

## 12. Automation

You can schedule the full backup bundle with cron:

```cron
0 3 * * * cd /opt/mnemos && ./scripts/backup.sh
```

This creates a dated directory under `backups/` every day at 03:00.
