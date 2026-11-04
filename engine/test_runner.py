
"""
DevOps Unified Continuous Testing Pipeline Runner
Orchestrates test layers, monitors execution, aggregates metrics,
evaluates quality gates, and outputs artifacts.
"""

import os
import sys
import time
import pytest

from datetime import datetime, timezone
from typing import Dict, Any, Callable
from coverage import Coverage

from tests.security.security_scanner import DevSecOpsScanner
from engine.coverage_analyzer import CodeCoverageAnalyzer
from engine.quality_gate import QualityGateEngine
from engine.report_generator import TestReportGenerator


class ContinuousTestingRunner:
    """Unified Orchestrator for all Continuous Testing stages."""

    def __init__(self, log_callback: Callable[[str], None] = None):

        if hasattr(sys.stdout, "reconfigure"):
            try:
                sys.stdout.reconfigure(
                    encoding="utf-8",
                    errors="replace"
                )
            except Exception:
                pass

        self.log_callback = log_callback or self._default_logger

        self.project_dir = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "..")
        )

        self.reports_dir = os.path.join(
            self.project_dir, "reports"
        )

        self.tests_dir = os.path.join(
            self.project_dir, "tests"
        )

        os.makedirs(self.reports_dir, exist_ok=True)

        self.report_gen = TestReportGenerator(
            self.reports_dir
        )

        self.quality_gate = QualityGateEngine()

    def _default_logger(self, msg: str):
        safe_msg = msg.encode(
            "ascii",
            errors="replace"
        ).decode("ascii")

        print(
            f"[{datetime.now().strftime('%H:%M:%S')}] {safe_msg}"
        )

    def log(self, message: str):
        self.log_callback(
            f"[{datetime.now().strftime('%H:%M:%S')}] {message}"
        )

    def run_full_pipeline(self) -> Dict[str, Any]:

        start_time = time.time()

        self.log("==================================================")
        self.log("[START] STARTING DEVOPS CONTINUOUS TESTING PIPELINE")
        self.log("==================================================")

        pipeline_result = {
            "pipeline_id": f"CT-RUN-{int(time.time())}",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "status": "RUNNING",
            "stages": {}
        }

        # --------------------------------------------------
        # STAGE 1: SECURITY AUDIT
        # --------------------------------------------------

        self.log(
            "\n[STAGE 1/5] Running Static Application Security Testing..."
        )

        scanner = DevSecOpsScanner()
        sast_report = scanner.scan_sast()

        self.log(
            f"   -> Files scanned: {sast_report['files_scanned']}"
        )

        self.log(
            f"   -> High/Critical vulnerabilities: "
            f"{sast_report['critical_or_high']}"
        )

        self.log(
            f"   -> SAST: "
            f"{'PASSED' if sast_report['passed'] else 'FAILED'}"
        )

        pipeline_result["stages"]["security_sast"] = sast_report

        # --------------------------------------------------
        # STAGE 2: FUNCTIONAL TESTING
        # --------------------------------------------------

        self.log(
            "\n[STAGE 2/5] Executing PyTest Test Suites..."
        )

        class PytestResultPlugin:

            def __init__(self):
                self.passed = 0
                self.failed = 0
                self.skipped = 0
                self.details = []
                self.execution_errors = 0

            def pytest_runtest_logreport(self, report):

                if report.when == "call":

                    if report.passed:
                        status = "PASSED"
                        self.passed += 1

                    elif report.failed:
                        status = "FAILED"
                        self.failed += 1

                    else:
                        status = "SKIPPED"
                        self.skipped += 1

                    self.details.append({
                        "name": report.nodeid.split("::")[-1],
                        "classname": report.nodeid.split("::")[0],
                        "status": status,
                        "duration": getattr(
                            report, "duration", 0.0
                        ),
                        "error_msg": (
                            str(report.longrepr)
                            if report.failed else None
                        )
                    })

                elif report.when == "setup":

                    if report.failed:
                        self.execution_errors += 1

                    elif report.skipped:
                        self.skipped += 1

                        self.details.append({
                            "name": report.nodeid.split("::")[-1],
                            "classname": report.nodeid.split("::")[0],
                            "status": "SKIPPED",
                            "duration": getattr(
                                report, "duration", 0.0
                            ),
                            "error_msg": str(report.longrepr)
                        })

                elif report.when == "teardown":

                    if report.failed:
                        self.execution_errors += 1

            def pytest_collectreport(self, report):

                if report.failed:
                    self.execution_errors += 1

        plugin = PytestResultPlugin()

        # --------------------------------------------------
        # COVERAGE COLLECTION
        # --------------------------------------------------

        coverage_file = os.path.join(
            self.project_dir,
            ".coverage"
        )

        app_source = os.path.join(
            self.project_dir,
            "app"
        )

        coverage_collector = Coverage(
            data_file=coverage_file,
            source=[app_source],
            omit=["*/__pycache__/*"],
            concurrency=["thread"],
            check_preimported=True
        )

        coverage_collector.erase()
        coverage_collector.start()

        try:

            # Import application only after coverage starts.
            from app.app import create_app

            exit_code = pytest.main(
                [
                    "-q",
                    self.tests_dir,
                    "-k",
                    "not test_system_performance_under_concurrency",
                    "--disable-warnings"
                ],
                plugins=[plugin]
            )

        except Exception as test_error:

            self.log(
                f"   -> [ERROR] PyTest execution error: {test_error}"
            )

            plugin.execution_errors += 1
            exit_code = pytest.ExitCode.INTERNAL_ERROR

        finally:

            coverage_collector.stop()
            coverage_collector.save()

        total_functional_tests = (
            plugin.passed
            + plugin.failed
            + plugin.skipped
        )

        self.log(
            f"   -> Executed {total_functional_tests} tests: "
            f"{plugin.passed} passed, "
            f"{plugin.failed} failed, "
            f"{plugin.skipped} skipped."
        )

        self.log(
            f"   -> PyTest exit code: {int(exit_code)}"
        )

        self.log(
            f"   -> Execution errors: {plugin.execution_errors}"
        )

        pipeline_result["stages"]["functional_tests"] = {
            "total": total_functional_tests,
            "passed": plugin.passed,
            "failed": plugin.failed,
            "skipped": plugin.skipped,
            "execution_errors": plugin.execution_errors,
            "exit_code": int(exit_code)
        }

        # --------------------------------------------------
        # STAGE 3: CODE COVERAGE
        # --------------------------------------------------

        self.log(
            "\n[STAGE 3/5] Performing Code Coverage Analysis..."
        )

        cov_analyzer = CodeCoverageAnalyzer()
        cov_report = cov_analyzer.run_coverage_analysis()

        self.log(
            f"   -> Overall Code Coverage: "
            f"{cov_report['overall_coverage_pct']}%"
        )

        for module in cov_report["modules"]:

            self.log(
                f"      * {module['module']}: "
                f"{module['coverage_pct']}% "
                f"({module['covered_statements']}/"
                f"{module['total_statements']} statements)"
            )

        pipeline_result["stages"]["code_coverage"] = cov_report

        # --------------------------------------------------
        # STAGE 4: PERFORMANCE TESTING
        # --------------------------------------------------

        self.log(
            "\n[STAGE 4/5] Running Performance & Load Testing..."
        )

        # Import performance engine after functional coverage.
        from tests.performance.load_engine import LoadTestEngine

        app_inst = create_app()

        load_engine = LoadTestEngine(
            app=app_inst
        )

        perf_report = load_engine.run_benchmark(
            total_requests=80,
            concurrency=6
        )

        self.log(
            f"   -> Requests: {perf_report['total_requests']} | "
            f"Concurrency: {perf_report['concurrency']} workers"
        )

        self.log(
            f"   -> Mean Latency: "
            f"{perf_report['mean_latency_ms']}ms | "
            f"P95: {perf_report['p95_latency_ms']}ms"
        )

        self.log(
            f"   -> Throughput: "
            f"{perf_report['requests_per_second']} RPS | "
            f"Error Rate: {perf_report['error_rate_pct']}%"
        )

        self.log(
            f"   -> Performance SLA: "
            f"{'PASSED' if perf_report['sla_passed'] else 'FAILED'}"
        )

        pipeline_result["stages"]["performance"] = perf_report

        # --------------------------------------------------
        # STAGE 5: QUALITY GATE
        # --------------------------------------------------

        self.log(
            "\n[STAGE 5/5] Evaluating DevOps Quality Gates..."
        )

        gate_metrics = {
            "total_tests": total_functional_tests,
            "passed_tests": plugin.passed,
            "failed_tests": plugin.failed,
            "skipped_tests": plugin.skipped,
            "execution_errors": plugin.execution_errors,
            "pytest_exit_code": int(exit_code),
            "code_coverage_pct": cov_report["overall_coverage_pct"],
            "security_critical_high": sast_report["critical_or_high"],
            "p95_latency_ms": perf_report["p95_latency_ms"],
            "load_error_rate_pct": perf_report["error_rate_pct"]
        }

        qg_verdict = self.quality_gate.evaluate(
            gate_metrics
        )

        self.log(
            f"   -> Quality Gate: {qg_verdict['verdict']} "
            f"({qg_verdict['passed_checks']}/"
            f"{qg_verdict['checks_count']} checks satisfied)"
        )

        for check in qg_verdict["checks"]:

            self.log(
                f"      [{check['status']}] "
                f"{check['rule']}: "
                f"{check['actual']} "
                f"(Rule: {check['threshold']})"
            )

        total_duration = round(
            time.time() - start_time,
            2
        )

        pipeline_result["duration_seconds"] = total_duration
        pipeline_result["total_tests"] = total_functional_tests
        pipeline_result["quality_gate"] = qg_verdict
        pipeline_result["coverage"] = cov_report
        pipeline_result["performance"] = perf_report
        pipeline_result["security"] = sast_report
        pipeline_result["status"] = qg_verdict["verdict"]

        # --------------------------------------------------
        # SAVE TEST RECORD
        # --------------------------------------------------

        try:

            from app.models import save_test_record

            save_test_record(
                pipeline_id=pipeline_result["pipeline_id"],
                total_tests=total_functional_tests,
                passed_tests=plugin.passed,
                failed_tests=plugin.failed,
                duration_seconds=total_duration,
                code_coverage_pct=cov_report["overall_coverage_pct"],
                p95_latency_ms=perf_report["p95_latency_ms"],
                security_vulnerabilities=sast_report["critical_or_high"],
                verdict=qg_verdict["verdict"]
            )

            self.log(
                "   -> Test execution record saved to SQLite database"
            )

        except Exception as db_error:

            self.log(
                f"   -> [WARN] Database persistence failed: {db_error}"
            )

        # --------------------------------------------------
        # GENERATE REPORTS
        # --------------------------------------------------

        self.log(
            "\n[ARTIFACTS] Generating Test Reports..."
        )

        json_path = self.report_gen.save_json_report(
            pipeline_result
        )

        xml_path = self.report_gen.save_junit_xml(
            plugin.details
        )

        html_path = self.report_gen.save_html_executive_report(
            pipeline_result
        )

        self.log(f"   -> JSON Report: {json_path}")
        self.log(f"   -> JUnit XML: {xml_path}")
        self.log(f"   -> HTML Report: {html_path}")

        self.log("==================================================")

        self.log(
            f"[FINISHED] PIPELINE COMPLETED IN "
            f"{total_duration}s - "
            f"VERDICT: {qg_verdict['verdict']}"
        )

        self.log("==================================================")

        return pipeline_result


if __name__ == "__main__":

    runner = ContinuousTestingRunner()

    result = runner.run_full_pipeline()

    sys.exit(
        0 if result["quality_gate"]["can_deploy"] else 1
    )
