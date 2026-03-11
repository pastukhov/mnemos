---
layout: default
title: Установка
permalink: /install/
lead: Пошаговая инструкция — работает на любой платформе с Docker
---

# Установка

## Что вы получите в конце

После выполнения этой инструкции у вас будет локально запущен Mnemos:

- API на `http://localhost:8000`
- MCP endpoint на `http://localhost:9000/mcp`
- веб-интерфейс на `http://localhost:8000/`

## Перед началом

- компьютер с Linux или Windows
- Docker Desktop или Docker Engine с Compose
- доступ к Terminal, PowerShell или другому shell
- скачанная папка проекта `mnemos`

Если Docker ещё не установлен:

- для Windows и macOS удобно Docker Desktop
- для Linux подойдёт Docker Engine + Docker Compose

## Шаг 1. Запустите Docker

Если вы используете Docker Desktop, просто запустите его и дождитесь,
пока он станет готов к работе.

> **Важно**: пока Docker не запущен, Mnemos не
> стартует.

Эта инструкция работает для любой платформы, где доступен Docker
Compose.

## Шаг 2. Откройте командную строку

Подойдёт:

- `Terminal` или любой shell
- `Terminal` или shell на Linux
- `PowerShell` или `Windows Terminal` на Windows

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

Для пользовательской установки этот шаг **не нужен**.

`make venv` нужен разработчику для локального запуска CLI, тестов и
работы с кодом вне Docker.

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

## Если вы хотите подключить агента

После запуска можно использовать MCP endpoint:

```text
http://localhost:9000/mcp
```

Или установить skill из репозитория:

```sh
npx skills add https://github.com/pastukhov/mnemos --skill mnemos-memory
```
