#!/bin/sh
# Start one TrustLedger backend service. Used by render.yaml (dockerCommand) and works locally too.
#
#   docker/start.sh api | brand-node | paypal-node | worker | seed | all-in-one
#
# It also normalizes values that Render Blueprints can only give us in a bare form:
#   * fromService `hostport` is "name:port" (no scheme)  -> prefix http:// for internal URLs
#   * WEB_PUBLIC_HOST is a bare onrender.com hostname    -> CORS_ORIGINS / PUBLIC_WEB_URL
set -eu

with_scheme() {  # $1 = value; prefix http:// when there is no scheme
  case "$1" in
    "") echo "" ;;
    *://*) echo "$1" ;;
    *) echo "http://$1" ;;
  esac
}

for var in BRAND_NODE_URL PAYPAL_NODE_URL API_URL; do
  eval "val=\${$var:-}"
  if [ -n "$val" ]; then
    export "$var=$(with_scheme "$val")"
  fi
done

if [ -n "${WEB_PUBLIC_HOST:-}" ]; then
  : "${CORS_ORIGINS:=https://$WEB_PUBLIC_HOST}"
  : "${PUBLIC_WEB_URL:=https://$WEB_PUBLIC_HOST}"
  export CORS_ORIGINS PUBLIC_WEB_URL
fi

service="${1:-api}"
case "$service" in
  api)         exec uvicorn backend.api.main:app --host 0.0.0.0 --port "${PORT:-8000}" --proxy-headers ;;
  brand-node)  exec uvicorn backend.brand_node.main:app --host 0.0.0.0 --port "${PORT:-8001}" ;;
  paypal-node) exec uvicorn backend.paypal_node.main:app --host 0.0.0.0 --port "${PORT:-8002}" ;;
  worker)      exec python -m backend.worker.main ;;
  seed)        exec python docker/seed.py ${SEED_ARGS:-} ;;
  all-in-one)  exec bash /app/docker/all_in_one.sh ;;
  *) echo "unknown service: $service" >&2; exit 2 ;;
esac
