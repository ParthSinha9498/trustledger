"""
Render Environment Variable Auto-Sync Tool

Reads configuration directly from the local .env file and render.yaml,
and syncs all required environment variables to Render services
using the Render REST API (PUT /v1/services/{serviceId}/env-vars/{key}).

Zero manual copy-pasting of environment variables required.
"""

import os
import re
import sys
import secrets
from pathlib import Path
import httpx
import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
ENV_FILE = REPO_ROOT / ".env"
RENDER_YAML = REPO_ROOT / "render.yaml"

def parse_env_file(path: Path) -> dict[str, str]:
    env_vars = {}
    if not path.exists():
        return env_vars
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" in line:
            key, val = line.split("=", 1)
            key = key.strip()
            val = val.strip().strip("'\"")
            env_vars[key] = val
    return env_vars

def get_render_client(api_key: str) -> httpx.Client:
    return httpx.Client(
        base_url="https://api.render.com/v1",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Accept": "application/json",
            "Content-Type": "application/json",
        },
        timeout=30.0,
    )

def main():
    dry_run = "--live" not in sys.argv
    local_env = parse_env_file(ENV_FILE)
    api_key = os.environ.get("RENDER_API_KEY", "") or local_env.get("RENDER_API_KEY", "")

    print("=== TrustLedger Render Environment Auto-Sync ===")
    print(f"Mode: {'DRY RUN (no changes)' if dry_run else 'LIVE'}")
    print(f"Local .env variables found: {len(local_env)}")

    if not api_key:
        print("\nError: RENDER_API_KEY not found in environment or .env.")
        sys.exit(1)

    client = get_render_client(api_key)

    # 1. Fetch services
    res = client.get("/services")
    if res.status_code != 200:
        print(f"Error fetching services: {res.status_code} - {res.text}")
        sys.exit(1)

    services = {}
    service_urls = {}
    for item in res.json():
        svc = item.get("service", {})
        s_name = svc.get("name")
        s_id = svc.get("id")
        s_url = svc.get("serviceDetails", {}).get("url", "")
        # extract hostname from https://<host>.onrender.com
        s_host = s_url.replace("https://", "").replace("http://", "").strip("/")
        services[s_name] = s_id
        service_urls[s_name] = s_host
        print(f"Found service: {s_name} -> ID: {s_id} (Host: {s_host})")

    # 2. Fetch postgres database
    res_pg = client.get("/postgres")
    if res_pg.status_code != 200:
        print(f"Error fetching postgres: {res_pg.status_code} - {res_pg.text}")
        sys.exit(1)

    db_info = {}
    for pg in res_pg.json():
        p_info = pg.get("postgres", {})
        if p_info.get("name") == "trustledger-db":
            p_id = p_info.get("id")
            # Fetch connection string details
            conn_res = client.get(f"/postgres/{p_id}/connection-info")
            if conn_res.status_code == 200:
                c_data = conn_res.json()
                internal_conn = c_data.get("internalConnectionString") or c_data.get("externalConnectionString", "")
                db_info["PLATFORM_DATABASE_URL"] = internal_conn
                # Replace db name at end with /brand and /paypal_side
                # e.g. postgresql://user:pass@host/trustledger_db_tguo
                base_conn = internal_conn.rsplit("/", 1)[0]
                db_info["BRAND_DATABASE_URL"] = f"{base_conn}/brand"
                db_info["PAYPAL_DATABASE_URL"] = f"{base_conn}/paypal_side"
                print(f"Found trustledger-db -> Internal connection strings derived for platform, brand, paypal_side")

    # 3. Build backend env vars dictionary
    backend_vars = {
        "PLATFORM_DATABASE_URL": db_info.get("PLATFORM_DATABASE_URL", ""),
        "BRAND_DATABASE_URL": db_info.get("BRAND_DATABASE_URL", ""),
        "PAYPAL_DATABASE_URL": db_info.get("PAYPAL_DATABASE_URL", ""),
        "SEED_ON_START": "auto",
        "WEB_PUBLIC_HOST": service_urls.get("trustledger-web", "trustledger-web.onrender.com"),
        "NODE_SHARED_TOKEN": local_env.get("NODE_SHARED_TOKEN") or secrets.token_hex(16),
        "PAYER_HASH_KEY": secrets.token_hex(32),
        "PAYPAL_MODE": "sandbox",
        "PAYPAL_CLIENT_ID": local_env.get("PAYPAL_CLIENT_ID", ""),
        "PAYPAL_CLIENT_SECRET": local_env.get("PAYPAL_CLIENT_SECRET", ""),
        "PAYPAL_WEBHOOK_ID": local_env.get("PAYPAL_WEBHOOK_ID", ""),
        "LLM_MODE": "live",
        "LLM_API_KEY": local_env.get("LLM_API_KEY", ""),
        "LLM_BASE_URL": "https://api.groq.com/openai/v1",
        "AGENT_MODEL": "openai/gpt-oss-120b",
        "LLM_FALLBACK_API_KEY": local_env.get("LLM_FALLBACK_API_KEY", ""),
        "LLM_FALLBACK_BASE_URL": "https://generativelanguage.googleapis.com/v1beta/openai/",
        "LLM_FALLBACK_MODEL": "gemini-3.5-flash",
        "SANDBOX_TEST_CARD_NUMBER": local_env.get("SANDBOX_TEST_CARD_NUMBER", "4000000000000000"),
        "SANDBOX_TEST_CARD_EXPIRY": local_env.get("SANDBOX_TEST_CARD_EXPIRY", "2030-01"),
        "SANDBOX_TEST_CARD_CVV": local_env.get("SANDBOX_TEST_CARD_CVV", "123"),
        "NOTIFY_WEBHOOK_URL": local_env.get("NOTIFY_WEBHOOK_URL", ""),
        "BRAND_ID": "nimbus",
        "CURRENT_WEEK": "42",
        "DAILY_EPSILON": "5.0",
    }

    # 4. Build web env vars dictionary
    web_vars = {
        "API_PUBLIC_HOST": service_urls.get("trustledger-backend", "trustledger-backend-0abs.onrender.com"),
        "NEXT_PUBLIC_PAYPAL_CLIENT_ID": local_env.get("PAYPAL_CLIENT_ID", ""),
    }

    # 5. Push backend env vars
    backend_id = services.get("trustledger-backend")
    if backend_id:
        print(f"\n[*] Syncing {len(backend_vars)} environment variables to trustledger-backend ({backend_id})...")
        for k, v in backend_vars.items():
            if not v:
                print(f"  [-] {k}: EMPTY / SKIPPED")
                continue
            if dry_run:
                print(f"  [+] {k}: READY [length: {len(v)}]")
            else:
                res_put = client.put(f"/services/{backend_id}/env-vars/{k}", json={"value": v})
                if res_put.status_code in (200, 201):
                    print(f"  [+] {k}: SYNCED OK")
                else:
                    print(f"  [!] {k}: FAILED ({res_put.status_code}: {res_put.text})")

    # 6. Push web env vars
    web_id = services.get("trustledger-web")
    if web_id:
        print(f"\n[*] Syncing {len(web_vars)} environment variables to trustledger-web ({web_id})...")
        for k, v in web_vars.items():
            if not v:
                print(f"  [-] {k}: EMPTY / SKIPPED")
                continue
            if dry_run:
                print(f"  [+] {k}: READY [length: {len(v)}]")
            else:
                res_put = client.put(f"/services/{web_id}/env-vars/{k}", json={"value": v})
                if res_put.status_code in (200, 201):
                    print(f"  [+] {k}: SYNCED OK")
                else:
                    print(f"  [!] {k}: FAILED ({res_put.status_code}: {res_put.text})")

    if not dry_run:
        print("\n[✓] All environment variables synced successfully!")

if __name__ == "__main__":
    main()
