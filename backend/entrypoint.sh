#!/bin/sh
set -e

# Roda Alembic migrations se PostgreSQL estiver configurado
if [ -n "$DATABASE_URL" ]; then
  echo "Running Alembic migrations..."
  cd /app/backend && alembic upgrade head
fi

# Sobe uvicorn
exec uvicorn jarvis.api:app --host 0.0.0.0 --port "${JARVIS_PORT:-8000}"
