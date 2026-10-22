#!/usr/bin/env bash
# Render free plan: one web service runs the whole backend (free has no private services or workers).
#
#   api          0.0.0.0:$PORT   public (browser, PayPal webhooks)   PLATFORM_DATABASE_URL only
#   brand-node   127.0.0.1:8001  localhost only                      BRAND_DATABASE_URL only
#   paypal-node  127.0.0.1:8002  localhost only                      PAYPAL_DATABASE_URL + PAYER_HASH_KEY only
#   worker       -               talks to the three over HTTP         no database URL at all
#
# Each process gets only its own credentials (env -u), so service isolation still holds inside the
# container, and the data nodes aren't reachable from the internet at all. If any process exits, the
# container exits and Render restarts it. Seeds the databases first when they're empty.
set -euo pipefail

PORT="${PORT:-8000}"
DB_VARS=(BRAND_DATABASE_URL PAYPAL_DATABASE_URL PLATFORM_DATABASE_URL)
only() {  # only VAR -- cmd...: run cmd with every database URL except VAR removed
  local keep="$1"; shift 2
  local unset=()
  for v in "${DB_VARS[@]}"; do [ "$v" = "$keep" ] || unset+=(-u "$v"); done
  [ "$keep" = PAYPAL_DATABASE_URL ] || unset+=(-u PAYER_HASH_KEY)  # the payer-hash secret stays in the PayPal-side node
  env "${unset[@]}" "$@"
}

export BRAND_NODE_URL=http://127.0.0.1:8001 PAYPAL_NODE_URL=http://127.0.0.1:8002 API_URL="http://127.0.0.1:$PORT"

if [ "${SEED_ON_START:-auto}" != "never" ]; then
  if [ "${SEED_ON_START:-auto}" = "always" ] || ! python - <<'EOF'
import os, sys, psycopg
try:
    with psycopg.connect(os.environ["PLATFORM_DATABASE_URL"]) as c:
        sys.exit(0 if c.execute("SELECT to_regclass('public.stores')").fetchone()[0] else 1)
except Exception as e:
    print(f"seed check: {e}", file=sys.stderr); sys.exit(1)
EOF
  then
    echo "all-in-one: seeding databases"
    python docker/seed.py ${SEED_ARGS:-}
  fi
fi

pids=()
only BRAND_DATABASE_URL -- uvicorn backend.brand_node.main:app --host 127.0.0.1 --port 8001 & pids+=($!)
only PAYPAL_DATABASE_URL -- uvicorn backend.paypal_node.main:app --host 127.0.0.1 --port 8002 & pids+=($!)
only PLATFORM_DATABASE_URL -- uvicorn backend.api.main:app --host 0.0.0.0 --port "$PORT" --proxy-headers & pids+=($!)
only NONE -- python -m backend.worker.main & pids+=($!)

trap 'kill "${pids[@]}" 2>/dev/null' TERM INT
wait -n "${pids[@]}"
code=$?
echo "all-in-one: a process exited ($code); stopping the rest" >&2
kill "${pids[@]}" 2>/dev/null || true
exit "$code"
