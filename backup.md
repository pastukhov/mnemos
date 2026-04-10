---
layout: default
title: Резервное копирование
permalink: /backup/
lang: ru
alternate_url: /en/backup/
lead: Как сохранить данные Mnemos и восстановить их после сбоя,
  переезда или опасного изменения.
---

# Резервное копирование и восстановление

Mnemos хранит основную память в PostgreSQL, а поисковый индекс в
Qdrant. Для надёжной работы полезно делать резервные копии и базы, и
всего локального стека.

## Что сохранять

- PostgreSQL: память, кандидаты, pipeline state
- Qdrant: векторный индекс для поиска
- конфигурацию: `.env`, compose-файлы и локальные настройки

## Рекомендуемый вариант

Для большинства случаев лучше делать полный snapshot стека:

```sh
make stack-backup
```

Команда создаёт архив в `backups/`:

```text
backups/mnemos-stack-YYYYMMDD-HHMMSS.tar.gz
```

Восстановление:

```sh
make stack-restore FILE=backups/mnemos-stack-YYYYMMDD-HHMMSS.tar.gz
```

Этот вариант удобен, когда вы переезжаете на другую машину, тестируете
опасные изменения или хотите быстро вернуть весь локальный стек.

## PostgreSQL backup

Если нужен только дамп базы:

```sh
make backup
```

По умолчанию архив сохраняется как:

```text
backups/mnemos-postgres-YYYYMMDD-HHMMSS.sql.gz
```

Можно указать свой путь:

```sh
./scripts/backup_postgres.sh backups/my-postgres.sql.gz
```

Восстановление:

```sh
make restore FILE=backups/mnemos-postgres-YYYYMMDD-HHMMSS.sql.gz
```

или напрямую:

```sh
./scripts/restore_postgres.sh backups/mnemos-postgres-YYYYMMDD-HHMMSS.sql.gz
```

После restore обычно нужен reindex для Qdrant:

```sh
make reindex
```

Если reindex нужно отложить:

```sh
SKIP_REINDEX=1 ./scripts/restore_postgres.sh backups/mnemos-postgres-YYYYMMDD-HHMMSS.sql.gz
```

## Qdrant backup

Если нужно сохранить только поисковый индекс:

```sh
make qdrant-backup
```

Восстановление:

```sh
make qdrant-restore FILE=backups/mnemos-qdrant-YYYYMMDD-HHMMSS.tar.gz
```

## Backup конфигурации

Чтобы сохранить локальные настройки вместе с данными:

```sh
make config-backup
```

В архив попадают `.env`, compose-файлы и локальные настройки проекта.

## Как проверить восстановление

После restore проверьте:

- `http://localhost:8000/health/live`
- `http://localhost:8000/health/ready`
- поиск через `POST /memory/query`

Если health-check и поиск работают, восстановление прошло успешно.

## Что важно помнить

- `docker compose down -v` удаляет volumes и может стереть данные
- логический restore PostgreSQL не заменяет reindex Qdrant
- полный snapshot удобнее всего использовать перед рискованными
  операциями

- [Открыть FAQ](/mnemos/faq/)
- [Открыть руководство пользователя](/mnemos/guide/)
