"""Case alerts: POST a small JSON event to NOTIFY_WEBHOOK_URL (a Zapier catch hook or a Slack webhook).

Never blocks or fails the request that triggered it. Contains no buyer data: only case facts.
"""
import logging
import threading

import httpx

from backend import config

log = logging.getLogger(__name__)


def _post(url: str, payload: dict) -> None:
    try:
        httpx.post(url, json=payload, timeout=10).raise_for_status()
    except Exception as e:  # alerts are best effort
        log.warning("case alert failed: %s", e)


def case_event(event: str, case: dict, summary: str | None = None) -> None:
    url = config.env("NOTIFY_WEBHOOK_URL")
    if not url:
        return
    dashboard = config.env("PUBLIC_WEB_URL", "http://localhost:3000")
    payload = {
        "event": event,                         # case_opened | case_completed | case_failed
        "case_id": case["case_id"],
        "store_id": case.get("store_id"),
        "sku": case.get("sku"),
        "reason_code": case.get("reason_code"),
        "summary": (summary or "")[:1500],
        "url": f"{dashboard}/cockpit/cases/{case['case_id']}",
        # Plain-text fallback, used directly by Slack incoming webhooks.
        "text": _text(event, case, summary, dashboard),
    }
    threading.Thread(target=_post, args=(url, payload), daemon=True).start()


def _text(event: str, case: dict, summary: str | None, dashboard: str) -> str:
    link = f"{dashboard}/cockpit/cases/{case['case_id']}"
    if event == "case_opened":
        return (f":rotating_light: Verification failed at {case.get('store_id')} for {case.get('sku')} "
                f"({case.get('reason_code')}). No payment was created. Investigation opened: {link}")
    if event == "case_deferred":
        return f":hourglass: Investigation {case['case_id']} deferred: waiting for AI capacity.\n{(summary or '')[:600]}\n{link}"
    status = "completed" if event == "case_completed" else "failed"
    return f":mag: Investigation {case['case_id']} {status}.\n{(summary or '')[:600]}\n{link}"
