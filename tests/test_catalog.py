import pytest
from bulk_lanes.catalog import RouteCatalog, RouteCircuitBreaker

def test_catalog_ladder_rotation(tmp_path):
    cfg = tmp_path / "routes.json"
    cat = RouteCatalog(config_path=cfg)
    cat.data = {
        "revision": 1,
        "routes": [
            {"id": "r1", "enabled": True, "zero_price_verified": True},
            {"id": "r2", "enabled": True, "zero_price_verified": True},
            {"id": "r3", "enabled": True, "zero_price_verified": True},
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
            {"id": "r_free", "enabled": True, "zero_price_verified": True}
        ]
    }
    cat.save()

    # Reporting non-zero cost must trip circuit breaker
    with pytest.raises(RouteCircuitBreaker):
        cat.record_cost("r_free", reported_cost=0.005)
    
    # Check that route was disabled in catalog
    assert cat.data["routes"][0]["enabled"] is False
    assert "Circuit breaker tripped" in cat.data["routes"][0]["disabled_reason"]

def test_is_free_in_schema():
    from bulk_lanes.catalog import is_free_in_schema
    assert is_free_in_schema({"id": "meta/llama:free"}) is True
    assert is_free_in_schema({"id": "m1", "name": "Model 1 (Free tier)"}) is True
    assert is_free_in_schema({"id": "m2", "pricing": {"prompt": "0", "completion": "0"}}) is True
    assert is_free_in_schema({"id": "m3", "cost": {"input": 0, "output": 0}}) is True
    assert is_free_in_schema({"id": "m4", "pricing": {"prompt": "0.001", "completion": "0.002"}}) is False
