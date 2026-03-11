---
layout: default
title: Установка на macOS
permalink: /install/
lead: Пошаговая инструкция для человека с MacBook и Docker Desktop, без
  предположения о техническом опыте.
---

# Установка на macOS

## Что вы получите в конце

После выполнения этой инструкции у вас будет локально запущен Mnemos:

- API на `http://localhost:8000`
- MCP endpoint на `http://localhost:9000/mcp`
- веб-интерфейс на `http://localhost:8000/`

## Перед началом

Убедитесь, что у вас есть:

- MacBook с установленной macOS
- установленный Docker Desktop
- доступ к приложению Terminal
- скачанная папка проекта `mnemos`

Если Docker Desktop ещё не установлен, сначала установите его с
официального сайта Docker.

## Шаг 1. Запустите Docker Desktop

1. Откройте `Applications`.
1. Запустите `Docker`.
1. Дождитесь, пока Docker Desktop покажет, что он готов к работе.

> **Важно**: пока Docker Desktop полностью не запущен, Mnemos не
> стартует.

## Шаг 2. Откройте Terminal

1. Нажмите `Command + Space`.
1. Введите `Terminal`.
1. Нажмите `Enter`.

Откроется окно, куда можно вставлять команды.

## Шаг 3. Перейдите в папку проекта

Если проект уже скачан, перейдите в его папку:

```sh
cd /путь/к/mnemos
```

Если вы не знаете точный путь, можно ввести `cd`, поставить пробел и
перетащить папку `mnemos` в окно Terminal.

Пример:

```sh
cd /Users/yourname/Downloads/mnemos
```

## Шаг 4. Подготовьте файл настроек

Скопируйте пример настроек:

```sh
cp .env.example .env
```

Это создаст рабочий файл `.env`, который Mnemos будет использовать при
запуске.

## Шаг 5. Подготовьте локальное окружение Python

Выполните:

```sh
make venv
```

Что делает эта команда:

- создаёт локальное окружение Python
- устанавливает зависимости проекта

## Шаг 6. Запустите Mnemos

Выполните:

```sh
docker compose up -d --build
```

Что произойдёт:

- Docker соберёт контейнеры проекта
- запустятся PostgreSQL, Qdrant и сам Mnemos
- сервис станет доступен локально на вашем MacBook

Первый запуск обычно дольше следующих.

## Шаг 7. Проверьте, что сервис работает

Откройте в браузере:

- `http://localhost:8000/`
- `http://localhost:8000/health/live`
- `http://localhost:8000/health/ready`

Можно также запустить автоматическую проверку:

```sh
make smoke
```

## Если вам нужны facts и reflections

Для этих функций обычно нужен внешний LLM provider.

Вам понадобится заполнить в `.env` такие переменные:

- `EMBEDDING_BASE_URL`
- `EMBEDDING_API_KEY`
- `EMBEDDING_MODEL`
- `FACT_LLM_BASE_URL`
- `FACT_LLM_API_KEY`
- `FACT_LLM_MODEL`
- `REFLECTION_LLM_BASE_URL`
- `REFLECTION_LLM_API_KEY`
- `REFLECTION_LLM_MODEL`

Если вы хотите использовать локальный mock-режим:

```sh
cp .env.local-mock.example .env
docker compose -f docker-compose.yml \
  -f docker-compose.local-mock.yml \
  up -d --build
```

## Что делать дальше

- [Открыть руководство пользователя](/mnemos/guide/)
- [Посмотреть ответы на частые вопросы](/mnemos/faq/)
- [Открыть README](/mnemos/README_ru.md)
