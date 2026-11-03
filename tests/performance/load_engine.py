"""
Continuous Performance & Load Testing Engine
Simulates concurrent user load against AUT and computes latency percentiles & throughput SLAs.
"""
import time
import math
import threading
import concurrent.futures
from typing import Dict, List, Any
import requests
from app.app import create_app
from app.auth import generate_token

_thread_local = threading.local()

class LoadTestEngine:
    """Multi-threaded concurrent load simulator with statistical percentile analysis."""

    def __init__(self, base_url: str = "http://127.0.0.1:5000", app=None):
        self.base_url = base_url
        self.app = app
        self.token = generate_token(1, "admin", "admin")

    def _get_client(self):
        if self.app is None:
            return None
        if not hasattr(_thread_local, "client"):
            _thread_local.client = self.app.test_client()
        return _thread_local.client

    def _execute_request(self, endpoint: str, method: str = "GET", payload: dict = None) -> Dict[str, Any]:
        url = f"{self.base_url}{endpoint}"
        headers = {"Authorization": f"Bearer {self.token}", "Content-Type": "application/json"}
        t0 = time.perf_counter()
        status_code = 0
        success = False
        error_msg = None
        client = self._get_client()

        try:
            if client:
                if method.upper() == "GET":
                    res = client.get(endpoint, headers=headers)
                elif method.upper() == "POST":
                    res = client.post(endpoint, headers=headers, json=payload or {})
                else:
                    res = client.get(endpoint, headers=headers)
                status_code = res.status_code
                success = (200 <= status_code < 400)
            else:
                if method.upper() == "GET":
                    res = requests.get(url, headers=headers, timeout=5)
                elif method.upper() == "POST":
                    res = requests.post(url, headers=headers, json=payload or {}, timeout=5)
                else:
                    res = requests.get(url, headers=headers, timeout=5)
                status_code = res.status_code
                success = (200 <= status_code < 400)
        except Exception as e:
            error_msg = str(e)
            success = False

        duration_ms = (time.perf_counter() - t0) * 1000.0
        return {
            "status_code": status_code,
            "duration_ms": duration_ms,
            "success": success,
            "error": error_msg
        }

    def run_benchmark(self, total_requests: int = 100, concurrency: int = 10) -> Dict[str, Any]:
        """Run multi-threaded concurrent load test and calculate metrics."""
        endpoints = [
            ("/health", "GET", None),
            ("/api/products", "GET", None),
            ("/api/products/1", "GET", None),
            ("/metrics", "GET", None)
        ]

        tasks = []
        for i in range(total_requests):
            ep = endpoints[i % len(endpoints)]
            tasks.append(ep)

        wall_clock_start = time.perf_counter()
        results = []

        with concurrent.futures.ThreadPoolExecutor(max_workers=concurrency) as executor:
            future_to_req = {
                executor.submit(self._execute_request, ep[0], ep[1], ep[2]): ep
                for ep in tasks
            }
            for future in concurrent.futures.as_completed(future_to_req):
                res = future.result()
                results.append(res)

        wall_clock_total_sec = time.perf_counter() - wall_clock_start
        return self._compute_statistics(results, total_requests, concurrency, wall_clock_total_sec)

    def _compute_statistics(self, results: List[Dict], total_requests: int, concurrency: int, duration_sec: float) -> Dict[str, Any]:
        latencies = sorted([r["duration_ms"] for r in results])
        successes = sum(1 for r in results if r["success"])
        failures = total_requests - successes
        error_rate = round((failures / total_requests) * 100.0, 2) if total_requests > 0 else 0.0

        def percentile(n: float) -> float:
            if not latencies:
                return 0.0
            k = (len(latencies) - 1) * (n / 100.0)
            f = math.floor(k)
            c = math.ceil(k)
            if f == c:
                return round(latencies[int(k)], 2)
            d0 = latencies[int(f)] * (c - k)
            d1 = latencies[int(c)] * (k - f)
            return round(d0 + d1, 2)

        avg_lat = round(sum(latencies) / len(latencies), 2) if latencies else 0.0
        p50 = percentile(50)
        p90 = percentile(90)
        p95 = percentile(95)
        p99 = percentile(99)
        rps = round(total_requests / duration_sec, 2) if duration_sec > 0 else 0.0

        # SLA Gate: p95 latency <= 350ms, error rate <= 2%
        sla_passed = (p95 <= 350.0 and error_rate <= 2.0)

        return {
            "total_requests": total_requests,
            "concurrency": concurrency,
            "successful_requests": successes,
            "failed_requests": failures,
            "error_rate_pct": error_rate,
            "duration_seconds": round(duration_sec, 3),
            "requests_per_second": rps,
            "min_latency_ms": round(latencies[0], 2) if latencies else 0.0,
            "max_latency_ms": round(latencies[-1], 2) if latencies else 0.0,
            "mean_latency_ms": avg_lat,
            "p50_latency_ms": p50,
            "p90_latency_ms": p90,
            "p95_latency_ms": p95,
            "p99_latency_ms": p99,
            "sla_passed": sla_passed,
            "sla_criteria": "p95 <= 350ms, error_rate <= 2%"
        }

if __name__ == "__main__":
    app = create_app()
    engine = LoadTestEngine(app=app)
    print("Running DevOps Continuous Performance Benchmark (100 requests, 10 concurrent users)...")
    stats = engine.run_benchmark(total_requests=100, concurrency=10)
    import json
    print(json.dumps(stats, indent=2))
