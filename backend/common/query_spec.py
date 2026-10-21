"""Structured query specs. The LLM writes these (never SQL); nodes validate and run them."""
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

Dimension = Literal[
    "region", "city", "store_id", "sku", "week",
    "distributor_id", "reason_code", "age_band", "gender",
]

MAX_DIMENSIONS = 2
MAX_CELLS = 300  # e.g. 6 stores x 42 weeks; privacy cost per query does not depend on cell count

NODE_RULES: dict[str, dict[str, set[str]]] = {
    # Brand-side data is about businesses (serials, shipments, stores), not people.
    "brand": {
        "metrics": {"shipped_units", "sold_units", "verification_failures"},
        "dims": {"region", "city", "store_id", "sku", "week", "distributor_id", "reason_code"},
    },
    # PayPal-side data is about buyers: differential privacy applies here.
    "paypal": {
        "metrics": {"buyers", "sum_amount"},
        "dims": {"region", "city", "store_id", "sku", "week", "age_band", "gender"},
    },
}


class Filters(BaseModel):
    model_config = ConfigDict(extra="forbid")
    sku: list[str] | None = None
    region: list[str] | None = None
    store_id: list[str] | None = None
    week_from: int | None = Field(default=None, ge=1)
    week_to: int | None = Field(default=None, ge=1)


class QuerySpec(BaseModel):
    model_config = ConfigDict(extra="forbid")
    metric: str
    group_by: list[Dimension] = Field(default_factory=list, max_length=MAX_DIMENSIONS)
    filters: Filters = Field(default_factory=Filters)
    # Deprecated and ignored: the PayPal node charges a fixed rho per metric (see common/privacy.py).
    epsilon: float | None = Field(default=None, exclude=True)


class SpecRefused(Exception):
    def __init__(self, code: str, detail: str):
        super().__init__(f"{code}: {detail}")
        self.code = code
        self.detail = detail


def validate_for_node(spec: QuerySpec, node: str) -> None:
    rules = NODE_RULES[node]
    if spec.metric not in rules["metrics"]:
        raise SpecRefused("METRIC_NOT_ALLOWED", f"{spec.metric!r} is not available on the {node} node")
    bad = [d for d in spec.group_by if d not in rules["dims"]]
    if bad:
        raise SpecRefused("DIMENSION_NOT_ALLOWED", f"{bad} not available on the {node} node")
    if len(set(spec.group_by)) != len(spec.group_by):
        raise SpecRefused("DIMENSION_NOT_ALLOWED", "duplicate dimensions")


def tool_parameters(node: str) -> dict:
    """Plain JSON schema for LLM tool calling (no $refs, which some providers reject)."""
    rules = NODE_RULES[node]
    return {
        "type": "object",
        "properties": {
            "metric": {"type": "string", "enum": sorted(rules["metrics"])},
            "group_by": {
                "type": "array",
                "items": {"type": "string", "enum": sorted(rules["dims"])},
                "maxItems": MAX_DIMENSIONS,
            },
            "filters": {
                "type": "object",
                "properties": {
                    "sku": {"type": "array", "items": {"type": "string"}},
                    "region": {"type": "array", "items": {"type": "string"}},
                    "store_id": {"type": "array", "items": {"type": "string"}},
                    "week_from": {"type": "integer"},
                    "week_to": {"type": "integer"},
                },
            },
        },
        "required": ["metric"],
    }
