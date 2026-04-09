FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN apt-get update \
    && apt-get install -y --no-install-recommends caddy \
    && rm -rf /var/lib/apt/lists/* \
    && pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 80 443

CMD ["sh", "-c", "uvicorn main:app --host 127.0.0.1 --port 8000 & exec caddy run --config /app/Caddyfile --adapter caddyfile"]
