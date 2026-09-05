"""Fail-closed real-data acceptance, in addition to legacy demo/CORS gates."""

import json
import sys
import time
import urllib.request
from pathlib import Path


def request(base, path, data=None):
    body = None if data is None else json.dumps(data).encode()
    req = urllib.request.Request(base + path, data=body, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=180) as response:
        return json.load(response)


def validate(diagnosis, tasks, outbound, returning):
    expected = {"supermarket", "hospital", "pharmacy", "city_hall", "station", "social"}
    items = diagnosis.get("item_results", [])
    assert diagnosis.get("data_source") == "routing_provider", "mock diagnosis prohibited"
    assert {item["category"] for item in items} == expected and len(items) == 6
    assert all(item["status"] != "unknown" for item in items), "real route unavailable"
    assert len(tasks) == 6
    assert {task["destination_id"] for task in tasks} == {item["destination_id"] for item in items}
    for task in tasks:
        assert task["data_source"] == "routing_provider"
        assert task["outbound_departure"] == outbound and task["return_departure"] == returning
        assert "10時ごろ" not in task["voice_script_ja"]


def main():
    api_url = sys.argv[1].rstrip("/")
    source = json.loads(Path("data/hakusan/otp-sources.json").read_text())["scenario"]
    outbound = source["service_date"] + "T" + source["outbound_time"]
    returning = source["service_date"] + "T" + source["return_time"]
    for attempt in range(3):
        try:
            fixture = request(api_url, "/fixtures/hakusan")
            assert fixture["data_profile"] == "hakusan" and not fixture["mock_transport_results"]
            diagnosis = request(api_url, "/diagnosis/run", {
                **fixture, "outbound_departure": outbound, "return_departure": returning,
            })
            tasks = request(api_url, "/rehearsals/generate", diagnosis)["tasks"]
            validate(diagnosis, tasks, outbound, returning)
            print("hakusan_real_smoke=PASS destinations=6 dated_rehearsals=6")
            return
        except Exception:
            if attempt == 2:
                raise
            time.sleep(5)


if __name__ == "__main__":
    main()
