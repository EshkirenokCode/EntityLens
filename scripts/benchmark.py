"""Bounded warm HTTP measurements; no claim about batch matching throughput."""

import httpx, time, json, statistics, platform, os
from pathlib import Path

url = os.environ.get("CONCORD_URL", "http://127.0.0.1:8765")
out = {}
with httpx.Client(base_url=url, timeout=60) as c:
    for path in [
        "/api/status",
        "/api/pairs?limit=40",
        "/api/entities",
        "/api/evaluation",
    ]:
        c.get(path).raise_for_status()
        samples = []
        for _ in range(5):
            start = time.perf_counter()
            c.get(path).raise_for_status()
            samples.append((time.perf_counter() - start) * 1000)
        out[path] = dict(
            repeats=5,
            p50_ms=statistics.median(samples),
            p95_ms=max(samples),
            samples_ms=samples,
        )
report = dict(
    environment=platform.platform(),
    cpu_cores=os.cpu_count(),
    concurrency=1,
    cache="warm; one unmeasured request per endpoint",
    measurements=out,
    limitations="p95 is maximum of five runs; HTTP latency only; RAM and batch throughput not measured",
)
Path("reports/http-benchmark.json").write_text(json.dumps(report, indent=2))
print(json.dumps(report, indent=2))
