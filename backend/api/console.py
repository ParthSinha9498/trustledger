"""Brand question console: question -> editable query specs -> guarded results -> optional explanation.

    POST /console/plan    {question}                 -> {specs: [{node, spec}], rationale}
    POST /console/run     {specs: [{node, spec}], explain} -> {results, budget, explanation}
    GET  /console/budget                             -> PayPal node budget (passthrough)

Privacy rules kept here:
  * The planner LLM sees only the brand's question and the query-spec schema. Never data.
  * The explainer LLM sees only the guarded results the nodes returned (aggregates, DP output,
    refusal codes). Never the question text, raw rows or buyer identifiers (nodes never return them).
  * Every spec is validated (QuerySpec + validate_for_node) before it is shown or run.
"""
import json
import re
from typing import Literal

import httpx
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field, ValidationError

from backend import config
from backend.common import http
from backend.common.query_spec import NODE_RULES, QuerySpec, SpecRefused, tool_parameters, validate_for_node

router = APIRouter(prefix="/console", tags=["console"])

Node = Literal["brand", "paypal"]
MAX_SPECS_PER_RUN = 8
MAX_ROWS_TO_EXPLAIN = 40

# ---------------------------------------------------------------- models


class PlanRequest(BaseModel):
    question: str = Field(min_length=1, max_length=2000)


class NodeSpec(BaseModel):
    node: Node
    spec: dict


class RunRequest(BaseModel):
    specs: list[NodeSpec] = Field(max_length=MAX_SPECS_PER_RUN)
    explain: bool = False


def check_spec(node: str, raw: dict) -> QuerySpec:
    """Parse and validate one spec for a node. Raises SpecRefused with a node-style code."""
    try:
        spec = QuerySpec.model_validate(raw)
    except ValidationError as e:
        msgs = "; ".join(f"{'.'.join(map(str, err['loc'])) or 'spec'}: {err['msg']}" for err in e.errors())
        raise SpecRefused("INVALID_SPEC", msgs) from None
    validate_for_node(spec, node)
    return spec


def _dump(spec: QuerySpec) -> dict:
    return spec.model_dump(exclude_none=True)


# ---------------------------------------------------------------- planners

PLAN_SYSTEM = """You turn a brand analyst's question into structured aggregate queries.
You never write SQL and never see data. Use the tools to propose 1 to 3 queries:
- propose_brand_query: exact counts about the brand's businesses (shipments, sales, verification failures),
  dimensions include store_id, distributor_id, region, sku, week, reason_code.
- propose_paypal_query: differentially private buyer aggregates (buyers, sum_amount), dimensions include
  store_id, region, sku, week, age_band, gender. Each PayPal query spends privacy budget, so prefer few,
  coarse queries (one or two group_by dimensions) and only when buyer data is needed.
Catalog (use these exact codes in filters): skus NMB-P8-128 (Nimbus P8 128GB), NMB-P8-256 (Nimbus P8 256GB),
NMB-A5-64 (Nimbus A5 64GB); regions West, Central, East; stores store_a to store_f ("Store C" is store_c).
Weeks are numbered from 1 at the start of the year. The current week is {current_week}, so "the last 8 weeks"
means week_from {current_week} - 7 to week_to {current_week}.
In the message content, explain your plan in one or two plain sentences."""

PLAN_TOOLS = [
    {"type": "function", "function": {
        "name": f"propose_{node}_query",
        "description": f"Propose one query for the {node} node.",
        "parameters": tool_parameters(node)}}
    for node in ("brand", "paypal")
]

EXPLAIN_SYSTEM = """You explain aggregate query results to a brand analyst in plain language (at most 6 sentences).
Brand-node results are exact business counts. PayPal-node results are differentially private: values are noisy
(each row has ci95, a 95% interval half-width), small cells are suppressed, and differences smaller than the
combined interval are not evidence. Mention refusals and what they mean. Never speculate about individual
buyers and never call a product counterfeit."""


def _deterministic_rationale(specs: list[dict]) -> str:
    parts = []
    for s in specs:
        dims = " and ".join(s["spec"].get("group_by") or []) or "overall"
        parts.append(f"{s['node']} node: {s['spec']['metric']} by {dims}")
    return "; ".join(parts)


STORE_RE = re.compile(r"\bstore[ _]([a-f])\b", re.I)
SKU_RE = re.compile(r"\b(NMB-[A-Z0-9]+-\d+)\b", re.I)
WEEK_RE = re.compile(r"\bweeks? (\d{1,2})(?:\s*(?:-|to|through)\s*(\d{1,2}))?", re.I)
LAST_WEEKS_RE = re.compile(r"\b(?:last|past|previous)\s+(\d{1,2})\s+weeks\b", re.I)
# Product names as people say them ("the P8 128GB", "the A5"). A bare "P8" means both P8 sizes.
MODEL_RE = re.compile(r"\b(P8|A5)(?:\s*(128|256|64)\s*GB)?\b", re.I)
MODEL_SKUS = {("p8", "128"): ["NMB-P8-128"], ("p8", "256"): ["NMB-P8-256"], ("p8", ""): ["NMB-P8-128", "NMB-P8-256"],
              ("a5", "64"): ["NMB-A5-64"], ("a5", ""): ["NMB-A5-64"]}
TREND_WORDS = {"weekly", "trend", "trends", "change", "changed", "changes", "grow", "grew", "growth"}


def _filters_from(question: str) -> dict:
    f: dict = {}
    stores = sorted({f"store_{m.lower()}" for m in STORE_RE.findall(question)})
    if stores:
        f["store_id"] = stores
    skus = {m.upper() for m in SKU_RE.findall(question)}
    for model, size in MODEL_RE.findall(question):
        skus.update(MODEL_SKUS.get((model.lower(), size), []))
    if skus:
        f["sku"] = sorted(skus)
    m = WEEK_RE.search(question)
    last = LAST_WEEKS_RE.search(question)
    if m:
        lo = int(m.group(1))
        hi = int(m.group(2)) if m.group(2) else lo
        f["week_from"], f["week_to"] = min(lo, hi), max(lo, hi)
    elif last:
        now = config.current_week()
        f["week_from"], f["week_to"] = max(1, now - int(last.group(1)) + 1), now
    return f


def _dims_from(words: set[str], filters: dict) -> list[str]:
    """Group-by dimensions a business question names (at most 2); stores if it names none."""
    dims = []
    if words & {"region", "regions", "regional"}:
        dims.append("region")
    if words & TREND_WORDS:
        dims.append("week")
    if words & {"store", "stores"} and "store_id" not in filters and len(dims) < 2:
        dims.append("store_id")
    if len(filters.get("sku", [])) > 1 and len(dims) < 2:
        dims.append("sku")  # comparing products: split by product
    return dims or ["store_id"]


def mock_plan(question: str) -> tuple[list[dict], str]:
    """Deterministic keyword planner for LLM_MODE=mock. Not an LLM; same question, same plan."""
    q = question.lower()
    words = set(re.findall(r"[a-z]+", q))
    filters = _filters_from(question)
    specs: list[dict] = []
    reasons: list[str] = []

    demo = [d for d in ("age_band", "gender") if (d == "age_band" and words & {"age", "ages", "old", "young"})
            or (d == "gender" and words & {"gender", "female", "male", "women", "men"})]
    if demo:
        if len(demo) < 2 and len(filters.get("sku", [])) > 1:
            demo.append("sku")  # "the P8 vs the A5": split each band by product
        specs.append({"node": "paypal", "spec": {"metric": "buyers", "group_by": demo, "filters": filters}})
        reasons.append("buyer demographics are only on the PayPal side, so this is a differentially private count")
    if words & {"spend", "spent", "revenue", "amount", "sales", "money"} and not demo:
        dims = _dims_from(words, filters)
        specs.append({"node": "paypal", "spec": {"metric": "sum_amount", "group_by": dims, "filters": filters}})
        reasons.append("spend comes from PayPal-side transactions (noisy, budgeted); each cell also gives buyers "
                       "and spend per buyer")
    elif words & {"buyer", "buyers", "customer", "customers", "shoppers"} and not demo:
        dims = _dims_from(words, filters)
        specs.append({"node": "paypal", "spec": {"metric": "buyers", "group_by": dims, "filters": filters}})
        reasons.append(f"buyers by {' and '.join(dims)} is a PayPal-side count (differentially private, budgeted)")
    if words & {"distributor", "distributors", "diversion", "diverted", "channel", "supplier"}:
        specs.append({"node": "brand", "spec": {"metric": "sold_units", "group_by": ["store_id", "distributor_id"],
                                                "filters": filters}})
        reasons.append("sold units by store and distributor show whose stock sells where (exact brand data)")
    elif words & {"sell", "sells", "selling", "sold"} and not specs:
        dims = _dims_from(words, filters)
        specs.append({"node": "brand", "spec": {"metric": "sold_units", "group_by": dims, "filters": filters}})
        reasons.append(f"verified units sold by {' and '.join(dims)} come from the brand's own records "
                       "(exact, no privacy budget)")
    if words & {"shipped", "shipments", "shipment", "inventory", "stock"}:
        specs.append({"node": "brand", "spec": {"metric": "shipped_units", "group_by": ["store_id"], "filters": filters}})
        reasons.append("shipments per store come from the brand's own records")
    failures = words & {"fail", "failed", "failures", "fake", "counterfeit", "clone", "clones"}
    if failures or (not specs and words & {"where", "region", "store", "stores"}):
        dim = "region" if "region" in words else "store_id"
        specs.append({"node": "brand", "spec": {"metric": "verification_failures", "group_by": [dim, "reason_code"],
                                                "filters": filters}})
        reasons.append(f"verification failures by {dim} and reason show where checks fail (exact brand data)")
    if not specs:
        specs.append({"node": "brand", "spec": {"metric": "verification_failures", "group_by": ["store_id"],
                                                "filters": filters}})
        reasons.append("no specific topic recognised, so start with where verification failures happen")
    rationale = "Keyword planner (LLM_MODE=mock): " + "; ".join(reasons) + "."
    return specs, rationale


class LiveConsoleLLM:
    """OpenAI-compatible planner and explainer. `llm` needs next_turn(); explain uses a plain completion."""

    def __init__(self, llm=None) -> None:
        if llm is None:
            from backend.common.llm import get_llm

            llm = get_llm()
        self.llm = llm

    def plan(self, question: str) -> tuple[list[dict], str]:
        # One-click sample questions use verified stored query plans; never call a model
        samples = [
            "Where did the P8 128GB sell, by region, in the last 8 weeks?",
            "Which age bands buy the P8 128GB vs the A5?",
            "How did weekly buyers change at Store C over the last 12 weeks?",
            "What is the spend per buyer by region?",
        ]
        if any(question.strip().lower() == s.lower() for s in samples):
            return mock_plan(question)

        system = PLAN_SYSTEM.replace("{current_week}", str(config.current_week()))
        messages = [{"role": "system", "content": system}, {"role": "user", "content": question}]
        turn = self.llm.next_turn(messages, PLAN_TOOLS)
        specs = []
        for call in turn.tool_calls:
            node = {"propose_brand_query": "brand", "propose_paypal_query": "paypal"}.get(call.name)
            specs.append({"node": node, "spec": call.arguments, "_tool": call.name})
        return specs, (turn.content or "").strip()

    def explain(self, guarded: list[dict]) -> str:
        messages = [{"role": "system", "content": EXPLAIN_SYSTEM},
                    {"role": "user", "content": json.dumps(guarded, default=str)}]
        if hasattr(self.llm, "complete"):
            return self.llm.complete(messages)
        resp = self.llm.client.chat.completions.create(model=self.llm.model, messages=messages)
        return (resp.choices[0].message.content or "").strip()


class MockConsoleLLM:
    def plan(self, question: str) -> tuple[list[dict], str]:
        return mock_plan(question)

    def explain(self, guarded: list[dict]) -> str:
        return mock_explain(guarded)


def get_console_llm():
    if config.env("LLM_MODE", "live") == "mock":
        return MockConsoleLLM()
    from backend.common.llm import get_llm

    return LiveConsoleLLM(get_llm())


# ---------------------------------------------------------------- plan


@router.post("/plan")
def plan(req: PlanRequest):
    proposed, rationale = get_console_llm().plan(req.question)
    specs, dropped = [], []
    seen = set()
    for p in proposed:
        node = p.get("node")
        if node not in NODE_RULES:
            dropped.append(f"{p.get('_tool', 'unknown tool')}: unknown node")
            continue
        try:
            spec = _dump(check_spec(node, p.get("spec") or {}))
        except SpecRefused as e:
            dropped.append(f"{node} query ({e.code}: {e.detail})")
            continue
        key = json.dumps([node, spec], sort_keys=True)
        if key in seen:
            continue
        seen.add(key)
        specs.append({"node": node, "spec": spec})
    if not rationale:
        rationale = "Proposed queries: " + _deterministic_rationale(specs) if specs else "No queries proposed."
    if dropped:
        rationale += f" Dropped {len(dropped)} invalid proposal(s): " + "; ".join(dropped) + "."
    return {"specs": specs, "rationale": rationale}


# ---------------------------------------------------------------- run


def _node_url(node: str) -> str:
    return config.brand_node_url() if node == "brand" else config.paypal_node_url()


def _detail(r: httpx.Response):
    try:
        body = r.json()
    except ValueError:
        return {"refused": f"HTTP_{r.status_code}", "detail": r.text[:300]}
    return body.get("detail", body) if isinstance(body, dict) else body


def run_one(node: str, raw: dict) -> dict:
    try:
        spec = check_spec(node, raw)
    except SpecRefused as e:
        return {"node": node, "spec": raw, "refused": {"refused": e.code, "detail": e.detail}}
    body = {"brand_id": config.brand_id(), "spec": _dump(spec), "purpose": "console"}
    out: dict = {"node": node, "spec": _dump(spec)}
    try:
        with http.client(_node_url(node)) as c:
            r = c.post("/v1/query", json=body)
    except httpx.HTTPError as e:
        return out | {"refused": {"refused": "NODE_UNAVAILABLE", "detail": str(e)[:300]}}
    if r.status_code in (403, 422):
        return out | {"refused": _detail(r)}
    if r.status_code >= 400:
        return out | {"refused": {"refused": f"HTTP_{r.status_code}", "detail": str(_detail(r))[:300]}}
    data = r.json()
    out["rows"] = data.get("rows", [])
    for k in ("suppressed_cells", "noise", "exact", "cached"):
        if k in data:
            out[k] = data[k]
    return out


def _paypal_budget() -> dict | None:
    try:
        with http.client(config.paypal_node_url()) as c:
            r = c.get("/v1/budget", params={"brand_id": config.brand_id()})
    except httpx.HTTPError:
        return None
    return r.json() if r.status_code == 200 else None


def guarded_view(results: list[dict]) -> list[dict]:
    """The only thing the explainer ever sees: node outputs, trimmed. No question text, nothing else."""
    view = []
    for r in results:
        item = {"node": r["node"], "metric": r["spec"].get("metric"), "group_by": r["spec"].get("group_by", []),
                "filters": r["spec"].get("filters", {})}
        if "refused" in r:
            ref = r["refused"]
            item["refused"] = ref.get("refused") if isinstance(ref, dict) else str(ref)
        else:
            item["rows"] = r.get("rows", [])[:MAX_ROWS_TO_EXPLAIN]
            item["rows_total"] = len(r.get("rows", []))
            for k in ("suppressed_cells", "exact"):
                if k in r:
                    item[k] = r[k]
            if "noise" in r:
                item["noise"] = {k: r["noise"].get(k) for k in ("mechanism", "sigma", "display_floor", "eps_equivalent")
                                 if k in r["noise"]}
        view.append(item)
    return view


def _label(row: dict, dims: list[str]) -> str:
    return ", ".join(f"{d}={row.get(d)}" for d in dims) or "total"


def mock_explain(guarded: list[dict]) -> str:
    """Templated explanation for LLM_MODE=mock, built from the guarded view only."""
    lines = []
    for g in guarded:
        dims = g.get("group_by") or []
        what = f"{g['metric']} by {', '.join(dims) or 'total'}"
        if "refused" in g:
            lines.append(f"The {g['node']} node refused {what} ({g['refused']}).")
            continue
        rows = g.get("rows") or []
        if g["node"] == "brand":
            if rows:
                top = max(rows, key=lambda r: r.get("value", 0))
                lines.append(f"Brand data (exact): {what} has {g.get('rows_total', len(rows))} groups; "
                             f"the largest is {_label(top, dims)} with {top.get('value')}.")
            else:
                lines.append(f"Brand data (exact): {what} returned no matching records.")
        else:
            sup = g.get("suppressed_cells", 0)
            if rows:
                top = max(rows, key=lambda r: r.get("value", 0))
                ci = top.get("ci95")
                ci_txt = f" (±{ci} at 95%)" if ci is not None else ""
                lines.append(f"PayPal-side data (differentially private): {what} released {len(rows)} cells, "
                             f"{sup} suppressed as too small; the largest is {_label(top, dims)} at about "
                             f"{top.get('value')}{ci_txt}. Differences smaller than the intervals are not evidence.")
            else:
                lines.append(f"PayPal-side data (differentially private): every cell of {what} was below the "
                             f"display floor ({sup} suppressed), so nothing can be read from it.")
    return " ".join(lines) or "No results to explain."


@router.post("/run")
def run(req: RunRequest):
    results = [run_one(s.node, s.spec) for s in req.specs]
    explanation = None
    if req.explain:
        explanation = get_console_llm().explain(guarded_view(results))
    return {"results": results, "budget": _paypal_budget(), "explanation": explanation}


# ---------------------------------------------------------------- budget


@router.get("/budget")
def budget():
    try:
        with http.client(config.paypal_node_url()) as c:
            r = c.get("/v1/budget", params={"brand_id": config.brand_id()})
    except httpx.HTTPError as e:
        raise HTTPException(502, f"PayPal node unavailable: {e}")
    if r.status_code != 200:
        raise HTTPException(502, {"node_status": r.status_code, "detail": _detail(r)})
    return r.json()
