#!/usr/bin/env bash
# Levanta el Postgres de desarrollo y espera a que acepte conexiones.
#
# Usa podman o docker directamente, sin compose: así `make dev` funciona en
# una máquina recién clonada sin instalar nada más que el motor de contenedores.
set -euo pipefail

cd "$(dirname "$0")/.."

if [ -f .env ]; then
  set -a
  # shellcheck disable=SC1091
  . ./.env
  set +a
fi

POSTGRES_DB="${POSTGRES_DB:-gatabase}"
POSTGRES_USER="${POSTGRES_USER:-gatabase}"
POSTGRES_PASSWORD="${POSTGRES_PASSWORD:-gatabase}"
POSTGRES_PORT="${POSTGRES_PORT:-5433}"
IMAGEN="${POSTGRES_IMAGE:-docker.io/library/postgres:17}"
CONTENEDOR="${POSTGRES_CONTAINER:-gatabase-db}"
VOLUMEN="${POSTGRES_VOLUME:-gatabase-db-data}"

MOTOR="${CONTAINER_ENGINE:-}"
if [ -z "$MOTOR" ]; then
  for candidato in podman docker; do
    if command -v "$candidato" >/dev/null 2>&1; then
      MOTOR="$candidato"
      break
    fi
  done
fi
if [ -z "$MOTOR" ]; then
  echo "No se encontró podman ni docker. Instala uno, o apunta las variables POSTGRES_* de .env a un Postgres propio." >&2
  exit 1
fi

estado() { "$MOTOR" inspect -f '{{.State.Status}}' "$CONTENEDOR" 2>/dev/null || true; }

case "$(estado)" in
  running) ;;
  "")
    "$MOTOR" run -d \
      --name "$CONTENEDOR" \
      -e POSTGRES_DB="$POSTGRES_DB" \
      -e POSTGRES_USER="$POSTGRES_USER" \
      -e POSTGRES_PASSWORD="$POSTGRES_PASSWORD" \
      -p "127.0.0.1:${POSTGRES_PORT}:5432" \
      -v "${VOLUMEN}:/var/lib/postgresql/data" \
      "$IMAGEN" >/dev/null
    ;;
  *)
    "$MOTOR" start "$CONTENEDOR" >/dev/null
    ;;
esac

# La comprobación va por TCP y ejecuta una consulta de verdad: durante la
# inicialización la imagen levanta un Postgres temporal que solo escucha en el
# socket unix, y `pg_isready` a secas lo daría por listo antes de tiempo.
for _ in $(seq 1 60); do
  if "$MOTOR" exec -e PGPASSWORD="$POSTGRES_PASSWORD" "$CONTENEDOR" \
      psql -h 127.0.0.1 -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c 'select 1' >/dev/null 2>&1; then
    exit 0
  fi
  sleep 1
done

echo "Postgres no respondió en 60 segundos. Revisa: $MOTOR logs $CONTENEDOR" >&2
exit 1
