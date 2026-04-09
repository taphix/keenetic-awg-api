# Keenetic API MVP

Минимальный FastAPI-сервис для тестирования Keenetic API:

- рабочая async-аутентификация через `GET /auth` -> `POST /auth`
- рабочий `POST /interfaces` c нормализованным списком интерфейсов и их названий
- рабочий `POST /show-interfaces`
- рабочий `POST /raw-rci-post`
- `POST /rename-interface` пока оставлен как честная заглушка до подтверждения точного RCI write payload

## Файлы

- `main.py` - FastAPI endpoints
- `keenetic_client.py` - async клиент Keenetic
- `schemas.py` - pydantic модели запросов

## Установка

```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 8000
```

## Docker

```bash
docker build -t keenetic-api-mvp .
docker run -d \
  --name keenetic-api-mvp \
  -p 8000:8000 \
  keenetic-api-mvp
```

## Docker Compose

```bash
docker compose up -d --build
```

Если на сервере нет Compose plugin, используйте legacy-команду:

```bash
docker-compose up -d --build
```

Остановить:

```bash
docker compose down
```

Или:

```bash
docker-compose down
```

Контейнер внутри поднимает:

```bash
- API-контейнер FastAPI на 8000
- Caddy-контейнер на 80/443
- домен: https://testawg.twzrds.ru
```

Важно для TLS:

```bash
- DNS A-запись testawg.twzrds.ru должна указывать на ваш сервер
- порты 80 и 443 должны быть доступны снаружи
- Caddy хранит сертификаты в docker volume `caddy_data`
```

Compose поднимает два контейнера:

```bash
- `api` с FastAPI
- `caddy` с reverse proxy и TLS
```

## Проверка

```bash
curl https://testawg.twzrds.ru/health
```

## Список интерфейсов и названий

Этот endpoint логинится в Keenetic, делает `GET /rci/show/interface` и возвращает удобный список:

```bash
curl -X POST https://testawg.twzrds.ru/interfaces \
  -H "Content-Type: application/json" \
  -d '{
    "base_url": "http://192.168.1.1",
    "login": "admin",
    "password": "admin_password"
  }'
```

Пример ответа:

```json
{
  "interfaces": [
    {
      "interface_id": "Wireguard0",
      "name": "test"
    }
  ]
}
```

## Raw show interfaces

```bash
curl -X POST https://testawg.twzrds.ru/show-interfaces \
  -H "Content-Type: application/json" \
  -d '{
    "base_url": "http://192.168.1.1",
    "login": "admin",
    "password": "admin_password"
  }'
```

## Raw RCI POST

```bash
curl -X POST https://testawg.twzrds.ru/raw-rci-post \
  -H "Content-Type: application/json" \
  -d '{
    "base_url": "http://192.168.1.1",
    "login": "admin",
    "password": "admin_password",
    "path": "/rci/some/path",
    "payload": {
      "example": "value"
    }
  }'
```

## Rename interface

Сейчас endpoint нужен как thin wrapper для rename. Он не выдумывает Keenetic write endpoint.

Если точные `path` и `payload` ещё неизвестны, он вернёт `501 Not Implemented`.

Если точные `path` и `payload` уже известны, их можно передать прямо в этот endpoint, и он вызовет `raw_rci_post(...)`.

```bash
curl -X POST https://testawg.twzrds.ru/rename-interface \
  -H "Content-Type: application/json" \
  -d '{
    "base_url": "http://192.168.1.1",
    "login": "admin",
    "password": "admin_password",
    "interface_id": "Wireguard0",
    "new_name": "test1",
    "path": "/rci/CONFIRMED/RENAME/PATH",
    "payload": {
      "interface_id": "Wireguard0",
      "new_name": "test1"
    }
  }'
```

После того как вы снимете точный write path/payload из DevTools, достаточно заменить реализацию `rename_interface()` в `keenetic_client.py` на вызов `raw_rci_post(...)`.

## Как переименовать `test` в `test1`

Шаг 1. Получить список интерфейсов и убедиться, что нужный интерфейс найден:

```bash
curl -X POST https://testawg.twzrds.ru/interfaces \
  -H "Content-Type: application/json" \
  -d '{
    "base_url": "http://192.168.1.1",
    "login": "admin",
    "password": "admin_password"
  }'
```

Шаг 2. Найти, например:

```json
{
  "interface_id": "Wireguard0",
  "name": "test"
}
```

Шаг 3. Когда точный Keenetic rename `path/payload` будет известен, вызвать:

```bash
curl -X POST https://testawg.twzrds.ru/rename-interface \
  -H "Content-Type: application/json" \
  -d '{
    "base_url": "http://192.168.1.1",
    "login": "admin",
    "password": "admin_password",
    "interface_id": "Wireguard0",
    "new_name": "test1",
    "path": "/rci/CONFIRMED/RENAME/PATH",
    "payload": {
      "id": "Wireguard0",
      "new_name": "test1"
    }
  }'
```

Когда будет известен точный `path/payload`, можно будет сделать `rename_interface()` реальным thin wrapper без изменения остальной архитектуры.
