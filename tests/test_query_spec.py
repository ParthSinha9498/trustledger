import pytest
from pydantic import ValidationError

from backend.common.query_spec import QuerySpec, SpecRefused, validate_for_node


def test_rejects_demographics_on_brand_node():
    with pytest.raises(SpecRefused) as e:
        validate_for_node(QuerySpec(metric="sold_units", group_by=["age_band"]), "brand")
    assert e.value.code == "DIMENSION_NOT_ALLOWED"


def test_rejects_distributor_on_paypal_node():
    with pytest.raises(SpecRefused):
        validate_for_node(QuerySpec(metric="buyers", group_by=["distributor_id"]), "paypal")


def test_rejects_wrong_metric():
    with pytest.raises(SpecRefused) as e:
        validate_for_node(QuerySpec(metric="buyers"), "brand")
    assert e.value.code == "METRIC_NOT_ALLOWED"


def test_max_two_dimensions_and_no_extra_fields():
    with pytest.raises(ValidationError):
        QuerySpec(metric="buyers", group_by=["region", "sku", "week"])
    with pytest.raises(ValidationError):
        QuerySpec(metric="buyers", sql="SELECT *")
