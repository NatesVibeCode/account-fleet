from bulk_lanes.manifest import ManifestManager
from bulk_lanes.export import export_clean_packet

def test_manifest_lifecycle(tmp_path):
    mgr = ManifestManager(run_dir=tmp_path, total_items=10, max_attempts=5)
    assert mgr.get_remaining_attempts() == 5
    
    # Reserve batch
    assert mgr.reserve_batch("b1", ["i1", "i2"]) is True
    assert mgr.get_remaining_attempts() == 4
    
    # Record success
    mgr.record_batch_success("b1", [{"item_id": "i1"}, {"item_id": "i2"}], {"cost": 0.0, "usage": {"total_tokens": 120}})
    assert mgr.data["batches"]["b1"]["status"] == "verified"
    
    mgr.finalize()
    assert mgr.data["status"] == "completed"

    # Export packet
    export_file = tmp_path / "clean_packet.json"
    packet = export_clean_packet(mgr.data, export_file)
    assert packet["total_verified_records"] == 2
    assert packet["audit"]["total_tokens_consumed"] == 120
    assert export_file.exists()
