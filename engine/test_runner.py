"""
DevOps Unified Continuous Testing Pipeline Runner
Orchestrates test layers, monitors execution, aggregates metrics,
evaluates quality gates, and outputs artifacts.
"""
import os
import sys
import time
import pytest
from datetime import datetime
from typing import Dict, Any, Callable

from app.app import create_app
from tests.performance.load_engine import LoadTestEngine
from tests.security.security_scanner import DevSecOpsScanner
from engine.coverage_analyzer import CodeCoverageAnalyzer
from engine.quality_gate import QualityGateEngine
from engine.report_generator import TestReportGenerator

class ContinuousTestingRunner:
    """Unified Orchestrator for all Continuous Testing stages."""

    def __init__(self, log_callback: Callable[[str], None] = None):
        if hasattr(sys.stdout, "reconfigure"):
            try:
                sys.stdout.reconfigure(encoding="utf-8", errors="replace")
            except Exception:
                pass
        self.log_callback = log_callback or self._default_logger
        self.reports_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "reports"))
        self.tests_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "tests"))
        self.report_gen = TestReportGenerator(self.reports_dir)
        self.quality_gate = QualityGateEngine()

    def _default_logger(self, msg: str):
        safe_msg = msg.encode("ascii", errors="replace").decode("ascii")
        print(f"[{datetime.now().strftime('%H:%M:%S')}] {safe_msg}")

    def log(self, message: str):
        self.log_callback(f"[{datetime.now().strftime('%H:%M:%S')}] {message}")

    def run_full_pipeline(self) -> Dict[str, Any]:
        """Execute the complete multi-layer DevOps testing pipeline."""
        start_time = time.time()
        self.log("==================================================================")
        self.log("[START] STARTING DEVOPS CONTINUOUS TESTING PIPELINE")
        self.log("==================================================================")

        pipeline_result = {
            "pipeline_id": f"CT-RUN-{int(time.time())}",
            "timestamp": datetime.utcnow().isoformat(),
            "status": "RUNNING",
            "stages": {}
        }

        # ---------------- STAGE 1: SAST SECURITY AUDIT ---------------- #
        self.log("\n[STAGE 1/5] [SECURITY] Running Static Application Security Testing (SAST)...")
        scanner = DevSecOpsScanner()
        sast_report = scanner.scan_sast()
        self.log(f"   -> Files scanned: {sast_report['files_scanned']}")
        self.log(f"   -> High/Critical vulnerabilities: {sast_report['critical_or_high']}")
        self.log(f"   -> Security SAST: {'PASSED' if sast_report['passed'] else 'FAILED'}")
        pipeline_result["stages"]["security_sast"] = sast_report

        # ---------------- STAGE 2: UNIT & INTEGRATION TESTING ---------------- #
        self.log("\n[STAGE 2/5] [TESTS] Executing Automated PyTest Test Suites (Unit, Integration, E2E)...")
        
        # Collect pytest execution results programmatically
        class PytestResultPlugin:
            def __init__(self):
                self.passed = 0
                self.failed = 0
                self.skipped = 0
                self.details = []

            def pytest_runtest_logreport(self, report):
                if report.when == "call":
                    status = "PASSED" if report.passed else ("FAILED" if report.failed else "SKIPPED")
                    if report.passed:
                        self.passed += 1
                    elif report.failed:
                        self.failed += 1
                    else:
                        self.skipped += 1
                    
                    self.details.append({
                        "name": report.nodeid.split("::")[-1],
                        "classname": report.nodeid.split("::")[0],
                        "status": status,
                        "duration": getattr(report, "duration", 0.0),
                        "error_msg": str(report.longrepr) if report.failed else None
                    })

        plugin = PytestResultPlugin()
        exit_code = pytest.main([
            "-q", self.tests_dir,
            "-k", "not test_system_performance_under_concurrency", # Run perf separately for granular telemetry
            "--disable-warnings"
        ], plugins=[plugin])

        total_functional_tests = plugin.passed + plugin.failed + plugin.skipped
        self.log(f"   -> Executed {total_functional_tests} tests: {plugin.passed} passed, {plugin.failed} failed.")
        pipeline_result["stages"]["functional_tests"] = {
            "total": total_functional_tests,
            "passed": plugin.passed,
            "failed": plugin.failed,
            "exit_code": int(exit_code)
        }

        # ---------------- STAGE 3: CODE COVERAGE ANALYSIS ---------------- #
        self.log("\n[STAGE 3/5] [COVERAGE] Performing AST Code Coverage Analysis on AUT Modules...")
        cov_analyzer = CodeCoverageAnalyzer()
        cov_report = cov_analyzer.run_coverage_analysis()
        self.log(f"   -> Overall Code Coverage: {cov_report['overall_coverage_pct']}%")
        for m in cov_report["modules"]:
            self.log(f"      * {m['module']}: {m['coverage_pct']}% ({m['covered_statements']}/{m['total_statements']} stmts)")
        pipeline_result["stages"]["code_coverage"] = cov_report

        # ---------------- STAGE 4: PERFORMANCE & LOAD TESTING ---------------- #
        self.log("\n[STAGE 4/5] [PERF] Simulating Concurrent Workload (Performance & Latency SLAs)...")
        app_inst = create_app()
        load_engine = LoadTestEngine(app=app_inst)
        perf_report = load_engine.run_benchmark(total_requests=80, concurrency=6)
        self.log(f"   -> Requests: {perf_report['total_requests']} | Concurrency: {perf_report['concurrency']} workers")
        self.log(f"   -> Mean Latency: {perf_report['mean_latency_ms']}ms | P95: {perf_report['p95_latency_ms']}ms")
        self.log(f"   -> Throughput: {perf_report['requests_per_second']} RPS | Error Rate: {perf_report['error_rate_pct']}%")
        self.log(f"   -> Performance SLA: {'PASSED' if perf_report['sla_passed'] else 'FAILED'}")
        pipeline_result["stages"]["performance"] = perf_report

        # ---------------- STAGE 5: QUALITY GATE EVALUATION ---------------- #
        self.log("\n[STAGE 5/5] [GATE] DevOps Quality Gate Evaluation...")
        
        gate_metrics = {
            "total_tests": total_functional_tests,
            "passed_tests": plugin.passed,
            "failed_tests": plugin.failed,
            "code_coverage_pct": cov_report["overall_coverage_pct"],
            "security_critical_high": sast_report["critical_or_high"],
            "p95_latency_ms": perf_report["p95_latency_ms"],
            "load_error_rate_pct": perf_report["error_rate_pct"]
        }

        qg_verdict = self.quality_gate.evaluate(gate_metrics)
        self.log(f"   -> Quality Gate Status: {qg_verdict['verdict']} ({qg_verdict['passed_checks']}/{qg_verdict['checks_count']} checks satisfied)")
        for c in qg_verdict["checks"]:
            self.log(f"      [{c['status']}] {c['rule']}: {c['actual']} (Rule: {c['threshold']})")

        total_duration = round(time.time() - start_time, 2)
        pipeline_result["duration_seconds"] = total_duration
        pipeline_result["total_tests"] = total_functional_tests
        pipeline_result["quality_gate"] = qg_verdict
        pipeline_result["coverage"] = cov_report
        pipeline_result["performance"] = perf_report
        pipeline_result["security"] = sast_report
        pipeline_result["status"] = qg_verdict["verdict"]

        # ---------------- ARTIFACT GENERATION ---------------- #
        self.log("\n[ARTIFACTS] Generating CI/CD Test Artifacts & Executive Reports...")
        json_path = self.report_gen.save_json_report(pipeline_result)
        xml_path = self.report_gen.save_junit_xml(plugin.details)
        html_path = self.report_gen.save_html_executive_report(pipeline_result)
        self.log(f"   -> JSON Artifact: {json_path}")
        self.log(f"   -> JUnit XML:     {xml_path}")
        self.log(f"   -> HTML Report:   {html_path}")

        self.log("\n==================================================================")
        self.log(f"[SUCCESS] PIPELINE FINISHED IN {total_duration}s - VERDICT: {qg_verdict['verdict']}")
        self.log("==================================================================")

        return pipeline_result

if __name__ == "__main__":
    runner = ContinuousTestingRunner()
    res = runner.run_full_pipeline()
    sys.exit(0 if res["quality_gate"]["can_deploy"] else 1)
