from bulk_lanes.sessions import SessionPool, WorkerSession

def test_session_lifecycle():
    pool = SessionPool(num_sessions=3, routes=["r1", "r2"])
    sessions = pool.get_all_sessions()
    assert len(sessions) == 3
    s0 = sessions[0]
    assert s0.status == "active"
    s0.record_batch_success(items_count=5, tokens=200, cost=0.0)
    assert s0.items_completed == 5
    assert s0.tokens_used == 200
    s0.finish()
    assert s0.status == "completed"
