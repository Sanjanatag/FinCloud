"""
FinCloud Load Testing Script

Demonstrates sub-200ms API latency under controlled load.
Designed for low traffic to stay within free-tier limits (≤5K requests/month).

Usage:
    python load_test.py --base-url http://localhost:8000 --requests 100
    python load_test.py --base-url http://<ALB-DNS> --requests 50
"""

import argparse
import json
import statistics
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from typing import Optional

import httpx


@dataclass
class RequestResult:
    endpoint: str
    method: str
    status_code: int
    latency_ms: float
    success: bool
    error: Optional[str] = None


@dataclass
class LoadTestReport:
    results: list[RequestResult] = field(default_factory=list)

    @property
    def total_requests(self) -> int:
        return len(self.results)

    @property
    def successful_requests(self) -> int:
        return sum(1 for r in self.results if r.success)

    @property
    def failed_requests(self) -> int:
        return self.total_requests - self.successful_requests

    @property
    def latencies(self) -> list[float]:
        return [r.latency_ms for r in self.results if r.success]

    def summary(self) -> dict:
        lats = self.latencies
        if not lats:
            return {"error": "No successful requests"}

        return {
            "total_requests": self.total_requests,
            "successful": self.successful_requests,
            "failed": self.failed_requests,
            "success_rate": f"{(self.successful_requests / self.total_requests) * 100:.1f}%",
            "latency_ms": {
                "min": round(min(lats), 2),
                "max": round(max(lats), 2),
                "mean": round(statistics.mean(lats), 2),
                "median": round(statistics.median(lats), 2),
                "p95": round(sorted(lats)[int(len(lats) * 0.95)], 2) if len(lats) >= 20 else "N/A (need ≥20 samples)",
                "p99": round(sorted(lats)[int(len(lats) * 0.99)], 2) if len(lats) >= 100 else "N/A (need ≥100 samples)",
                "stdev": round(statistics.stdev(lats), 2) if len(lats) > 1 else 0,
            },
            "sla_200ms_met": f"{sum(1 for l in lats if l < 200) / len(lats) * 100:.1f}%",
        }

    def print_report(self):
        s = self.summary()
        print("\n" + "=" * 60)
        print("  FinCloud Load Test Report")
        print("=" * 60)
        print(f"  Total Requests:     {s.get('total_requests', 0)}")
        print(f"  Successful:         {s.get('successful', 0)}")
        print(f"  Failed:             {s.get('failed', 0)}")
        print(f"  Success Rate:       {s.get('success_rate', 'N/A')}")
        print()
        lat = s.get("latency_ms", {})
        print("  Latency (ms):")
        print(f"    Min:              {lat.get('min', 'N/A')}")
        print(f"    Max:              {lat.get('max', 'N/A')}")
        print(f"    Mean:             {lat.get('mean', 'N/A')}")
        print(f"    Median:           {lat.get('median', 'N/A')}")
        print(f"    P95:              {lat.get('p95', 'N/A')}")
        print(f"    P99:              {lat.get('p99', 'N/A')}")
        print(f"    Std Dev:          {lat.get('stdev', 'N/A')}")
        print()
        print(f"  SLA (< 200ms):      {s.get('sla_200ms_met', 'N/A')}")
        print("=" * 60)

        per_endpoint = {}
        for r in self.results:
            key = f"{r.method} {r.endpoint}"
            if key not in per_endpoint:
                per_endpoint[key] = []
            if r.success:
                per_endpoint[key].append(r.latency_ms)

        if per_endpoint:
            print("\n  Per-Endpoint Breakdown:")
            print("  " + "-" * 56)
            for endpoint, lats in sorted(per_endpoint.items()):
                if lats:
                    print(f"  {endpoint}")
                    print(f"    Requests: {len(lats)} | Mean: {statistics.mean(lats):.1f}ms | Median: {statistics.median(lats):.1f}ms")
            print()


class LoadTester:
    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip("/")
        self.token: Optional[str] = None
        self.user_id: Optional[str] = None
        self.receiver_id: Optional[str] = None
        self.report = LoadTestReport()

    def _request(self, method: str, path: str, **kwargs) -> RequestResult:
        url = f"{self.base_url}{path}"
        headers = kwargs.pop("headers", {})
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"

        start = time.perf_counter()
        try:
            with httpx.Client(timeout=10.0) as client:
                response = client.request(method, url, headers=headers, **kwargs)
            latency = (time.perf_counter() - start) * 1000

            result = RequestResult(
                endpoint=path,
                method=method,
                status_code=response.status_code,
                latency_ms=latency,
                success=response.status_code < 400,
            )
        except Exception as e:
            latency = (time.perf_counter() - start) * 1000
            result = RequestResult(
                endpoint=path,
                method=method,
                status_code=0,
                latency_ms=latency,
                success=False,
                error=str(e),
            )

        self.report.results.append(result)
        return result

    def setup_test_users(self):
        """Create test users for the load test."""
        ts = int(time.time())
        r1 = self._request("POST", "/api/v1/users/register", json={
            "email": f"loadtest-sender-{ts}@test.com",
            "password": "loadtest123456",
            "full_name": "Load Test Sender",
        })
        if not r1.success:
            print(f"  Warning: sender registration returned {r1.status_code}")

        r2 = self._request("POST", "/api/v1/users/register", json={
            "email": f"loadtest-receiver-{ts}@test.com",
            "password": "loadtest123456",
            "full_name": "Load Test Receiver",
        })

        login = self._request("POST", "/api/v1/users/login", json={
            "email": f"loadtest-sender-{ts}@test.com",
            "password": "loadtest123456",
        })

        if login.success:
            with httpx.Client(timeout=10.0) as client:
                resp = client.post(
                    f"{self.base_url}/api/v1/users/login",
                    json={"email": f"loadtest-sender-{ts}@test.com", "password": "loadtest123456"},
                )
                data = resp.json()
                self.token = data.get("access_token")
                self.user_id = data.get("user_id")

            with httpx.Client(timeout=10.0) as client:
                resp = client.post(
                    f"{self.base_url}/api/v1/users/login",
                    json={"email": f"loadtest-receiver-{ts}@test.com", "password": "loadtest123456"},
                )
                data = resp.json()
                self.receiver_id = data.get("user_id")

    def run_health_checks(self, count: int = 20):
        """Rapid health checks to warm up and measure baseline latency."""
        print(f"\n  Running {count} health check requests...")
        for _ in range(count):
            self._request("GET", "/api/v1/users/health")
            self._request("GET", "/api/v1/transactions/health")

    def run_user_operations(self, count: int = 10):
        """Test user profile retrieval."""
        print(f"  Running {count} user profile requests...")
        for _ in range(count):
            self._request("GET", "/api/v1/users/me")

    def run_transaction_operations(self, count: int = 10):
        """Test transaction operations."""
        if not self.receiver_id:
            print("  Skipping transactions (no receiver set up)")
            return

        print(f"  Running {count} transaction requests...")
        for i in range(count):
            self._request("POST", "/api/v1/transactions/transfer", json={
                "receiver_id": self.receiver_id,
                "amount": round(1.00 + (i * 0.50), 2),
                "description": f"Load test transfer #{i + 1}",
            })

        for _ in range(count // 2):
            self._request("GET", "/api/v1/transactions/history")
            self._request("GET", "/api/v1/transactions/wallet")

    def run_concurrent_load(self, total_requests: int = 50, concurrency: int = 5):
        """Run concurrent requests to test under load."""
        print(f"  Running {total_requests} concurrent requests (concurrency={concurrency})...")
        endpoints = [
            ("GET", "/api/v1/users/health"),
            ("GET", "/api/v1/transactions/health"),
            ("GET", "/api/v1/users/me"),
            ("GET", "/api/v1/transactions/wallet"),
        ]

        def make_request(idx):
            method, path = endpoints[idx % len(endpoints)]
            return self._request(method, path)

        with ThreadPoolExecutor(max_workers=concurrency) as executor:
            futures = [executor.submit(make_request, i) for i in range(total_requests)]
            for f in as_completed(futures):
                f.result()


def main():
    parser = argparse.ArgumentParser(description="FinCloud Load Test")
    parser.add_argument("--base-url", default="http://localhost:8000", help="Base URL of the API")
    parser.add_argument("--requests", type=int, default=100, help="Total number of requests")
    parser.add_argument("--concurrency", type=int, default=5, help="Concurrent request threads")
    parser.add_argument("--skip-setup", action="store_true", help="Skip user setup")
    args = parser.parse_args()

    print("=" * 60)
    print("  FinCloud Load Test")
    print(f"  Target: {args.base_url}")
    print(f"  Requests: {args.requests}")
    print("=" * 60)

    tester = LoadTester(args.base_url)

    if not args.skip_setup:
        print("\n  Setting up test users...")
        tester.setup_test_users()

    health_count = max(args.requests // 5, 10)
    tester.run_health_checks(count=health_count)

    user_count = max(args.requests // 10, 5)
    tester.run_user_operations(count=user_count)

    txn_count = max(args.requests // 10, 5)
    tester.run_transaction_operations(count=txn_count)

    concurrent_count = args.requests - (health_count * 2 + user_count + txn_count * 2)
    if concurrent_count > 0:
        tester.run_concurrent_load(total_requests=concurrent_count, concurrency=args.concurrency)

    tester.report.print_report()

    latencies = tester.report.latencies
    if latencies:
        mean_latency = statistics.mean(latencies)
        if mean_latency < 200:
            print(f"  PASS: Mean latency {mean_latency:.1f}ms < 200ms SLA target")
            return 0
        else:
            print(f"  WARN: Mean latency {mean_latency:.1f}ms >= 200ms SLA target")
            return 1
    return 1


if __name__ == "__main__":
    sys.exit(main())
