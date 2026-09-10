from free_fleet.packer import pack_items

def test_pack_items():
    records = [
        {"item_id": f"item_{i}", "text": f"Description text for item {i}"}
        for i in range(10)
    ]
    batches = pack_items(records, batch_size=4)
    assert len(batches) == 3
    assert len(batches[0]["items"]) == 4
    assert len(batches[1]["items"]) == 4
    assert len(batches[2]["items"]) == 2
    assert batches[0]["batch_id"].startswith("batch_")
