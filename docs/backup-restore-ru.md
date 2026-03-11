# Резервное копирование и восстановление Mnemos

Этот документ описывает минимальный безопасный контур для сохранения и
восстановления данных Mnemos.

## Что именно нужно сохранять

Главный источник данных в Mnemos — PostgreSQL. Именно там лежат:

- записи памяти
- кандидаты на review
- связи между записями
- служебные метрики пайплайнов

Qdrant хранит поисковые векторы. Поэтому есть два режима резервного
копирования:

- логический backup PostgreSQL
- полный snapshot stack-данных PostgreSQL и Qdrant volumes

Для обычной надёжной эксплуатации лучше использовать полный snapshot.

## Рекомендуемый вариант: полный backup stack

Создать полный backup PostgreSQL + Qdrant:

```sh
make stack-backup
```

Будет создан файл в `backups/` вида:

```text
backups/mnemos-stack-YYYYMMDD-HHMMSS.tar.gz
```

Восстановить полный backup:

```sh
make stack-restore FILE=backups/mnemos-stack-YYYYMMDD-HHMMSS.tar.gz
```

Что делает этот вариант:

1. Останавливает сервисы.
1. Возвращает содержимое volumes PostgreSQL и Qdrant.
1. Поднимает сервисы обратно.

Плюс этого режима в том, что он не зависит от внешнего embedding API.

## Альтернативный вариант: логический backup PostgreSQL

Создать логический backup:

```sh
make backup
```

По умолчанию backup создаётся в папке `backups/` с именем вида:

```text
backups/mnemos-postgres-YYYYMMDD-HHMMSS.sql.gz
```

Можно указать свой путь:

```sh
./scripts/backup_postgres.sh backups/my-backup.sql.gz
```

## Восстановить логический backup

Восстановление принимает `.sql.gz` или `.sql`:

```sh
make restore FILE=backups/mnemos-postgres-YYYYMMDD-HHMMSS.sql.gz
```

Или напрямую:

```sh
./scripts/restore_postgres.sh backups/mnemos-postgres-YYYYMMDD-HHMMSS.sql.gz
```

Если нужно восстановить только PostgreSQL без немедленного reindex:

```sh
SKIP_REINDEX=1 ./scripts/restore_postgres.sh backups/mnemos-postgres-YYYYMMDD-HHMMSS.sql.gz
```

Что делает restore:

1. Загружает SQL-дамп обратно в PostgreSQL.
1. После этого запускает reindex Qdrant.
1. Восстанавливает поисковую доступность данных.

## Переиндексация отдельно

Если PostgreSQL на месте, а Qdrant потерял данные или был очищен:

```sh
make reindex
```

Команда пересоздаёт коллекции Qdrant и заново индексирует accepted
memory из PostgreSQL.

## Когда данные реально теряются

Особенно опасна команда:

```sh
docker compose down -v
```

Она удаляет volume, а значит и данные PostgreSQL.

Перед такими действиями стоит обязательно сделать backup:

```sh
make backup
```

## Рекомендуемый порядок

Если нужна максимальная надёжность:

1. `make stack-backup`
1. только потом risky actions вроде `docker compose down -v`

Если нужен перенос только базы в SQL-виде:

1. `make backup`
1. хранить `.sql.gz` отдельно от машины

После восстановления:

1. для полного снапшота: `make stack-restore FILE=...`
1. для логического restore: `make restore FILE=...`

## Ограничения

- полный snapshot привязан к локальным Docker volumes этого проекта
- логический restore PostgreSQL требует reindex для Qdrant
- если внешний embedding provider недоступен, логический restore базы
  завершится, но reindex может не собраться до устранения проблемы
