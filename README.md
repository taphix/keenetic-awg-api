# Keenetic API MVP

Минимальный FastAPI-сервис для управления WireGuard/AWG-интерфейсами Keenetic по API.

Что умеет:
- async-аутентификация через `GET /auth` -> `POST /auth`
- `POST /interfaces` - список только WireGuard-интерфейсов
- `POST /show-interfaces` - сырой ответ `GET /rci/show/interface`
- `POST /raw-rci-post` - сырой `POST` в `/rci/...`
- `POST /create-interface` - импорт `.conf`
- `POST /rename-interface` - смена имени интерфейса
- `POST /delete-interface` - удаление интерфейса

Используется только:
- FastAPI
- httpx
- pydantic

## Файлы

- `main.py` - FastAPI endpoints
- `keenetic_client.py` - async клиент Keenetic
- `schemas.py` - pydantic модели
- `compose.yaml` - `api` + `caddy`

## Локальный запуск

```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 8000
```

## Docker Compose

```bash
docker compose up -d --build
docker compose down
```

Стек поднимает:
- `api` на `8000`
- `caddy` на `80/443`
- домен `https://testawg.twzrds.ru`

Для TLS нужно:
- DNS `A`-запись `testawg.twzrds.ru` на IP сервера
- открытые `80` и `443`

## Проверка

```bash
curl https://testawg.twzrds.ru/health
```

## Список WG интерфейсов

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

## Сырой show interfaces

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
    "path": "/rci/",
    "payload": []
  }'
```

## Переименовать интерфейс

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

Пример ответа:

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

## Удалить интерфейс

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

## Создать интерфейс из `.conf`

Сначала кодируем локальный файл в base64:

```bash
CONFIG_BASE64=$(base64 < Test_Zamena.conf | tr -d '\n')
```

Потом вызываем API:

```bash
curl -X POST https://testawg.twzrds.ru/create-interface \
  -H "Content-Type: application/json" \
  -d "{
    \"base_url\": \"http://192.168.1.1\",
    \"login\": \"admin\",
    \"password\": \"admin_password\",
    \"config_base64\": \"$CONFIG_BASE64\",
    \"filename\": \"Test_Zamena.conf\",
    \"name\": \"\"
  }"
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

## Примечания

- `raw-rci-post` оставлен для отладки и экспериментов с Keenetic RCI
- все запросы к Keenetic идут через `httpx.AsyncClient`
- сервис не использует БД, Docker Compose orchestration, кроме `api + caddy`, и не хранит состояние
