# ---- builder ----
FROM python:3.12-slim AS builder

WORKDIR /build

COPY . /build/backend

RUN pip install --no-cache-dir /build/backend

# ---- runtime ----
FROM python:3.12-slim

WORKDIR /app

# Copia pacotes instalados e scripts do builder
COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copia Alembic config e migrations (necessario em runtime)
COPY alembic.ini /app/backend/alembic.ini
COPY alembic/ /app/backend/alembic/

# Copia entrypoint
COPY entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

EXPOSE 8000

ENTRYPOINT ["/app/entrypoint.sh"]
