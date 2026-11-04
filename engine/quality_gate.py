
"""DevOps Quality Gate Engine.

Validates test, coverage, security and performance metrics.
Missing or invalid metrics fail the quality gate.
"""


class QualityGateEngine:
    """Enforces automated CI/CD quality gate rules."""

    DEFAULT_THRESHOLDS = {
        "min_test_pass_rate": 100.0,
        "min_code_coverage_pct": 75.0,
        "max_critical_vulnerabilities": 0,
        "max_p95_latency_ms": 350.0,
        "max_error_rate_pct": 1.0,
    }

    def __init__(self, thresholds=None):
        self.thresholds = {
            **self.DEFAULT_THRESHOLDS,
            **(thresholds or {}),
        }

    def evaluate(self, metrics):
        checks = []

        def add_check(rule, threshold, actual, passed):
            checks.append({
                "rule": rule,
                "threshold": threshold,
                "actual": actual,
                "status": "PASSED" if passed else "FAILED",
            })

        def valid_number(value):
            return (
                isinstance(value, (int, float))
                and not isinstance(value, bool)
            )

        total = metrics.get("total_tests")
        passed = metrics.get("passed_tests")
        failed = metrics.get("failed_tests")
        skipped = metrics.get("skipped_tests")
        exit_code = metrics.get("pytest_exit_code")
        execution_errors = metrics.get("execution_errors")

        counts_valid = all(
            isinstance(v, int) and not isinstance(v, bool) and v >= 0
            for v in (total, passed, failed, skipped)
        )

        if counts_valid:
            counts_valid = (
                total > 0
                and passed + failed + skipped == total
            )

        pass_rate = (
            passed / total * 100
            if counts_valid and total > 0
            else None
        )

        add_check(
            "Test pass rate",
            f">= {self.thresholds['min_test_pass_rate']}%",
            pass_rate if pass_rate is not None else "INVALID/MISSING",
            counts_valid
            and pass_rate >= self.thresholds["min_test_pass_rate"]
            and failed == 0
            and skipped == 0
            and exit_code == 0
            and execution_errors == 0,
        )

        coverage = metrics.get("code_coverage_pct")
        coverage_valid = (
            valid_number(coverage) and 0 <= coverage <= 100
        )
        add_check(
            "Code coverage",
            f">= {self.thresholds['min_code_coverage_pct']}%",
            coverage if coverage_valid else "INVALID/MISSING",
            coverage_valid
            and coverage >= self.thresholds["min_code_coverage_pct"],
        )

        security = metrics.get("security_critical_high")
        security_valid = (
            isinstance(security, int)
            and not isinstance(security, bool)
            and security >= 0
        )
        add_check(
            "High/Critical vulnerabilities",
            f"<= {self.thresholds['max_critical_vulnerabilities']}",
            security if security_valid else "INVALID/MISSING",
            security_valid
            and security <= self.thresholds["max_critical_vulnerabilities"],
        )

        latency = metrics.get("p95_latency_ms")
        latency_valid = valid_number(latency) and latency >= 0
        add_check(
            "P95 latency",
            f"<= {self.thresholds['max_p95_latency_ms']} ms",
            latency if latency_valid else "INVALID/MISSING",
            latency_valid
            and latency <= self.thresholds["max_p95_latency_ms"],
        )

        error_rate = metrics.get("load_error_rate_pct")
        error_valid = (
            valid_number(error_rate) and 0 <= error_rate <= 100
        )
        add_check(
            "Load error rate",
            f"<= {self.thresholds['max_error_rate_pct']}%",
            error_rate if error_valid else "INVALID/MISSING",
            error_valid
            and error_rate <= self.thresholds["max_error_rate_pct"],
        )

        passed_checks = sum(
            check["status"] == "PASSED" for check in checks
        )
        verdict = (
            "PASSED"
            if passed_checks == len(checks)
            else "FAILED"
        )

        
        return {
    "verdict": verdict,
    "can_deploy": verdict == "PASSED",
    "passed_checks": passed_checks,
    "checks_count": len(checks),
    "checks": checks,
    "recommendation": (
        "All quality gate policies passed. Build is eligible for deployment."
        if verdict == "PASSED"
        else "Quality gate failed. Review failed checks before deployment."
    ),
}

