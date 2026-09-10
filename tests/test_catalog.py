import pytest
from bulk_lanes.catalog import PriceState, RouteCatalog, RouteCircuitBreaker, classify_price_state

def test_catalog_ladder_rotation(tmp_path):
    cfg = tmp_path / "routes.json"
    cat = RouteCatalog(config_path=cfg)
    cat.data = {
        "revision": 1,
        "routes": [
            {"id": "r1", "enabled": True, "price_state": "price_observed_zero"},
            {"id": "r2", "enabled": True, "price_state": "price_observed_zero"},
            {"id": "r3", "enabled": True, "price_state": "price_observed_zero"},
        ]
    }
    cat.save()

    l1 = cat.get_ladder(task_seed="seed_a", free_only=True)
    assert len(l1) == 3
    assert set(l1) == {"r1", "r2", "r3"}

def test_circuit_breaker_on_nonzero_cost(tmp_path):
    cfg = tmp_path / "routes.json"
    cat = RouteCatalog(config_path=cfg)
    cat.data = {
        "revision": 1,
        "routes": [
            {"id": "r_free", "enabled": True, "price_state": "price_observed_zero"}
        ]
    }
    cat.save()

    # Reporting non-zero cost must trip circuit breaker
    with pytest.raises(RouteCircuitBreaker):
        cat.record_cost("r_free", reported_cost=0.005)
    
    # Check that route was disabled in catalog
    assert cat.data["routes"][0]["enabled"] is False
    assert "Circuit breaker tripped" in cat.data["routes"][0]["disabled_reason"]

def test_price_state_requires_observed_pricing():
    assert classify_price_state({"id": "meta/llama:free"}) is PriceState.CANDIDATE
    assert classify_price_state({"id": "m1", "name": "Model 1 (Free tier)"}) is PriceState.CANDIDATE
    assert classify_price_state({"id": "m2", "pricing": {"prompt": "0", "completion": "0"}}) is PriceState.PRICE_OBSERVED_ZERO
    assert classify_price_state({"id": "m3", "cost": {"input": 0, "output": 0}}) is PriceState.PRICE_OBSERVED_ZERO
    assert classify_price_state({"id": "m4", "pricing": {"prompt": "0.001", "completion": "0.002"}}) is PriceState.UNKNOWN


def test_candidate_route_is_not_in_free_ladder(tmp_path):
    cat = RouteCatalog(config_path=tmp_path / "routes.json")
    cat.data = {"revision": 2, "routes": [{"id": "looks-free", "enabled": True, "price_state": "candidate"}]}
    assert cat.get_ladder(free_only=True) == []


def test_packaged_routes_are_disabled_hints_until_refreshed(tmp_path):
    catalog = RouteCatalog(db_path=tmp_path / "state.db")
    assert catalog.get_routes(free_only=True) == []
    assert catalog.get_routes(free_only=False, include_disabled=True)
