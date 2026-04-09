# Keenetic API MVP

Минимальный FastAPI-сервис для тестирования Keenetic API:

- рабочая async-аутентификация через `GET /auth` -> `POST /auth`
- рабочий `POST /interfaces` c нормализованным списком интерфейсов и их названий
- рабочий `POST /show-interfaces`
- рабочий `POST /raw-rci-post`
- рабочий `POST /rename-interface` через подтверждённый `POST /rci/`
- рабочий `POST /delete-interface` через подтверждённый `POST /rci/`
- рабочий `POST /create-interface` через подтверждённый `POST /rci/`

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

Этот endpoint логинится в Keenetic, делает `GET /rci/show/interface` и возвращает только WireGuard-интерфейсы:

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
  "kind": "wireguard",
  "total": 2,
  "named_total": 2,
  "unnamed_total": 0,
  "interfaces": [
    {
      "interface_id": "Wireguard0",
      "name": "test",
      "display_name": "test",
      "has_name": true,
      "kind": "wireguard"
    },
    {
      "interface_id": "Wireguard1",
      "name": "TestAWG",
      "display_name": "TestAWG",
      "has_name": true,
      "kind": "wireguard"
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

Этот endpoint теперь использует подтверждённый из DevTools вызов:

- `POST /rci/`
- payload с `interface.description`
- затем `system.configuration.save`

По умолчанию он отправляет минимальный payload такого вида:

```json
[
  {
    "interface": {
      "description": "test1",
      "name": "Wireguard0"
    }
  },
  {
    "system": {
      "configuration": {
        "save": {}
      }
    }
  }
]
```

При желании можно передать свои `path` и `payload` вручную, тогда endpoint просто прокинет их в `raw_rci_post(...)`.

```bash
curl -X POST https://testawg.twzrds.ru/rename-interface \
  -H "Content-Type: application/json" \
  -d '{
    "base_url": "http://192.168.1.1",
    "login": "admin",
    "password": "admin_password",
    "interface_id": "Wireguard0",
    "new_name": "test1"
  }'
```

Пример красивого ответа:

```json
{
  "ok": true,
  "action": "rename_interface",
  "interface_id": "Wireguard0",
  "new_name": "test1",
  "saved": true,
  "message": "Interface Wireguard0 renamed to test1.",
  "router_messages": [
    "\"Wireguard0\": description saved.",
    "saving (http/rci)."
  ]
}
```

## Delete interface

Этот endpoint использует подтверждённый вызов удаления:

- `POST /rci/`
- payload с `{"interface": {"name": "...", "no": true}}`
- затем `system.configuration.save`

```bash
curl -X POST https://testawg.twzrds.ru/delete-interface \
  -H "Content-Type: application/json" \
  -d '{
    "base_url": "http://192.168.1.1",
    "login": "admin",
    "password": "admin_password",
    "interface_id": "Wireguard2"
  }'
```

Пример ответа:

```json
{
  "ok": true,
  "action": "delete_interface",
  "interface_id": "Wireguard2",
  "deleted": true,
  "saved": true,
  "message": "Interface Wireguard2 deleted.",
  "router_messages": [
    "interface \"Wireguard2\" removed.",
    "saving (http/rci)."
  ]
}
```

## Create interface

Этот endpoint использует подтверждённый import-вызов:

- `POST /rci/`
- payload с `interface.wireguard.import`
- принимает base64 содержимое `.conf`

```bash
curl -X POST https://testawg.twzrds.ru/create-interface \
  -H "Content-Type: application/json" \
  -d '{
    "base_url": "http://192.168.1.1",
    "login": "admin",
    "password": "admin_password",
    "config_base64": "W0ludGVyZmFjZV0KLi4u",
    "filename": "Test_Zamena.conf",
    "name": ""
  }'
```

Пример ответа:

```json
{
  "ok": true,
  "action": "create_interface",
  "filename": "Test_Zamena.conf",
  "interface_id": "Wireguard2",
  "intersects": "",
  "message": "Interface Wireguard2 created from Test_Zamena.conf.",
  "router_messages": [
    "\"Wireguard2\": imported settings."
  ]
}
```

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
    "new_name": "test1"
  }'
```

Если захотите вручную воспроизвести тот же вызов через `raw-rci-post`, это будет так:

```bash
curl -X POST https://testawg.twzrds.ru/raw-rci-post \
  -H "Content-Type: application/json" \
  -d '{
    "base_url": "http://192.168.1.1",
    "login": "admin",
    "password": "admin_password",
    "path": "/rci/",
    "payload": [
      {
        "interface": {
          "description": "test1",
          "name": "Wireguard0"
        }
      },
      {
        "system": {
          "configuration": {
            "save": {}
          }
        }
      }
    ]
  }'
```
