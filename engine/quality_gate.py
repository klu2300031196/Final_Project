"""
DevOps Quality Gate Engine
Enforces CI/CD quality gate rules and determines whether software build is deployable.
"""
from typing import Dict, List, Any

class QualityGateEngine:
    """Enforces strict, automated DevOps quality gates for continuous delivery."""

    DEFAULT_THRESHOLDS = {
        "min_test_pass_rate": 100.0,       # 100% of all tests must pass
        "min_code_coverage_pct": 75.0,     # At least 75% code coverage
        "max_critical_vulnerabilities": 0,  # Zero critical/high security issues
        "max_p95_latency_ms": 350.0,        # Latency p95 SLA limit
        "max_error_rate_pct": 1.0           # Max 1% error rate under load
    }

    def __init__(self, custom_thresholds: Dict[str, float] = None):
        self.thresholds = dict(self.DEFAULT_THRESHOLDS)
        if custom_thresholds:
            self.thresholds.update(custom_thresholds)

    def evaluate(self, test_metrics: Dict[str, Any]) -> Dict[str, Any]:
        """
        Evaluate comprehensive test metrics against quality gates.
        
        Args:
            test_metrics: Dictionary containing:
                - total_tests, passed_tests, failed_tests
                - code_coverage_pct
                - security_critical_high
                - p95_latency_ms
                - load_error_rate_pct
        """
        checks = []
        violations = []

        total_tests = test_metrics.get("total_tests", 0)
        passed_tests = test_metrics.get("passed_tests", 0)
        failed_tests = test_metrics.get("failed_tests", 0)
        pass_rate = round((passed_tests / total_tests * 100.0), 2) if total_tests > 0 else 0.0

        # Rule 1: Test Suite Pass Rate
        target_pass_rate = self.thresholds["min_test_pass_rate"]
        passed_rule1 = (failed_tests == 0 and pass_rate >= target_pass_rate)
        checks.append({
            "rule": "Automated Test Suite Pass Rate",
            "threshold": f">= {target_pass_rate}% (0 failures)",
            "actual": f"{pass_rate}% ({failed_tests} failed)",
            "status": "PASSED" if passed_rule1 else "FAILED"
        })
        if not passed_rule1:
            violations.append(f"Test suite had {failed_tests} failures; 100% pass rate is strictly required.")

        # Rule 2: Code Coverage Threshold
        coverage_pct = test_metrics.get("code_coverage_pct", 0.0)
        target_cov = self.thresholds["min_code_coverage_pct"]
        passed_rule2 = (coverage_pct >= target_cov)
        checks.append({
            "rule": "Application Source Code Coverage",
            "threshold": f">= {target_cov}%",
            "actual": f"{coverage_pct}%",
            "status": "PASSED" if passed_rule2 else "FAILED"
        })
        if not passed_rule2:
            violations.append(f"Code coverage ({coverage_pct}%) is below required threshold ({target_cov}%).")

        # Rule 3: Security & SAST Vulnerability Gate
        sec_high = test_metrics.get("security_critical_high", 0)
        target_sec = self.thresholds["max_critical_vulnerabilities"]
        passed_rule3 = (sec_high <= target_sec)
        checks.append({
            "rule": "Security SAST/DAST Critical Vulnerabilities",
            "threshold": f"<= {target_sec}",
            "actual": f"{sec_high} vulnerabilities",
            "status": "PASSED" if passed_rule3 else "FAILED"
        })
        if not passed_rule3:
            violations.append(f"Security audit detected {sec_high} high/critical vulnerabilities.")

        # Rule 4: Performance Latency SLA (P95)
        p95_lat = test_metrics.get("p95_latency_ms", 0.0)
        target_p95 = self.thresholds["max_p95_latency_ms"]
        passed_rule4 = (p95_lat <= target_p95)
        checks.append({
            "rule": "API P95 Response Latency SLA",
            "threshold": f"<= {target_p95}ms",
            "actual": f"{p95_lat}ms",
            "status": "PASSED" if passed_rule4 else "FAILED"
        })
        if not passed_rule4:
            violations.append(f"API P95 response time ({p95_lat}ms) exceeded SLA limit ({target_p95}ms).")

        # Rule 5: Concurrency Error Rate
        err_rate = test_metrics.get("load_error_rate_pct", 0.0)
        target_err = self.thresholds["max_error_rate_pct"]
        passed_rule5 = (err_rate <= target_err)
        checks.append({
            "rule": "Concurrent Load Error Rate",
            "threshold": f"<= {target_err}%",
            "actual": f"{err_rate}%",
            "status": "PASSED" if passed_rule5 else "FAILED"
        })
        if not passed_rule5:
            violations.append(f"Concurrent load error rate ({err_rate}%) exceeded threshold ({target_err}%).")

        overall_verdict = "PASSED" if len(violations) == 0 else "FAILED"

        return {
            "verdict": overall_verdict,
            "can_deploy": (overall_verdict == "PASSED"),
            "checks_count": len(checks),
            "passed_checks": sum(1 for c in checks if c["status"] == "PASSED"),
            "failed_checks": len(violations),
            "checks": checks,
            "violations": violations,
            "recommendation": "Software satisfies all DevOps Continuous Testing standards. Build approved for deployment."
                              if overall_verdict == "PASSED" else
                              "Build rejected by DevOps Quality Gate. Address violations before releasing to production."
        }
