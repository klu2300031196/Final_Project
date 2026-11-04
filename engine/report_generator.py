
"""Report Generator for Continuous Testing Pipelines.

Produces JSON metrics, JUnit XML and an executive HTML dashboard.
"""

import os
import json
import html
import xml.etree.ElementTree as ET

from datetime import datetime, timezone
from typing import Dict, Any


class TestReportGenerator:
    """Generates multi-format Continuous Testing artifacts."""

    def __init__(self, output_dir: str = None):
        self.output_dir = output_dir or os.path.abspath(
            os.path.join(os.path.dirname(__file__), "..", "reports")
        )
        os.makedirs(self.output_dir, exist_ok=True)

    @staticmethod
    def _safe(value):
        return html.escape(str(value))

    def save_json_report(self, pipeline_data: Dict[str, Any]) -> str:
        path = os.path.join(self.output_dir, "test_report.json")
        with open(path, "w", encoding="utf-8") as file:
            json.dump(pipeline_data, file, indent=2, default=str)
        return path

    def save_junit_xml(
        self,
        test_details: list,
        suite_name="DevOps-Continuous-Testing"
    ) -> str:

        passed = sum(t.get("status") == "PASSED" for t in test_details)
        failed = sum(t.get("status") == "FAILED" for t in test_details)
        skipped = sum(t.get("status") == "SKIPPED" for t in test_details)
        errors = sum(t.get("status") == "ERROR" for t in test_details)

        total_time = sum(
            float(t.get("duration", 0.0) or 0.0)
            for t in test_details
        )

        root = ET.Element(
            "testsuites",
            name="ContinuousTestingFramework",
            tests=str(len(test_details)),
            failures=str(failed),
            errors=str(errors),
            skipped=str(skipped)
        )

        suite = ET.SubElement(
            root,
            "testsuite",
            name=suite_name,
            tests=str(len(test_details)),
            failures=str(failed),
            errors=str(errors),
            skipped=str(skipped),
            time=str(round(total_time, 3)),
            timestamp=datetime.now(timezone.utc).isoformat()
        )

        for test in test_details:
            case = ET.SubElement(
                suite,
                "testcase",
                classname=str(test.get("classname", "DevOpsTests")),
                name=str(test.get("name", "test")),
                time=str(round(float(test.get("duration", 0.001) or 0.001), 4))
            )

            status = test.get("status")

            if status == "FAILED":
                failure = ET.SubElement(
                    case,
                    "failure",
                    message=str(test.get("error_msg", "Assertion Failed"))
                )
                failure.text = str(test.get("traceback", ""))

            elif status == "SKIPPED":
                ET.SubElement(
                    case,
                    "skipped",
                    message=str(test.get("error_msg", "Test skipped"))
                )

            elif status == "ERROR":
                error = ET.SubElement(
                    case,
                    "error",
                    message=str(test.get("error_msg", "Test execution error"))
                )
                error.text = str(test.get("traceback", ""))

        path = os.path.join(self.output_dir, "junit_report.xml")
        ET.ElementTree(root).write(
            path,
            encoding="utf-8",
            xml_declaration=True
        )
        return path

    def save_html_executive_report(
        self,
        pipeline_data: Dict[str, Any]
    ) -> str:

        qg = pipeline_data.get("quality_gate", {})
        perf = pipeline_data.get("performance", {})
        sec = pipeline_data.get("security", {})
        cov = pipeline_data.get("coverage", {})

        verdict = qg.get("verdict", "UNKNOWN")

        verdict_color = (
            "#10b981" if verdict == "PASSED" else "#ef4444"
        )
        verdict_bg = (
            "rgba(16,185,129,0.15)"
            if verdict == "PASSED"
            else "rgba(239,68,68,0.15)"
        )

        functional = pipeline_data.get("stages", {}).get(
            "functional_tests", {}
        )

        total_tests = pipeline_data.get(
            "total_tests", functional.get("total", 0)
        )
        passed_tests = functional.get("passed", 0)
        failed_tests = functional.get("failed", 0)
        skipped_tests = functional.get("skipped", 0)

        security_count = sec.get("critical_or_high", "N/A")
        security_passed = sec.get("passed", False)

        security_color = (
            "#10b981" if security_passed else "#ef4444"
        )
        security_status = (
            "PASSED" if security_passed else "FAILED / NOT VERIFIED"
        )

        coverage_pct = cov.get("overall_coverage_pct", 0.0)
        measurement_type = cov.get(
            "measurement_type", "Coverage measurement"
        )

        timestamp = pipeline_data.get(
            "timestamp", datetime.now(timezone.utc).isoformat()
        )

        checks_rows = ""

        for check in qg.get("checks", []):
            check_status = check.get("status", "UNKNOWN")

            if check_status == "PASSED":
                badge = (
                    '<span style="color:#10b981;font-weight:bold;">PASSED</span>'
                )
            else:
                badge = (
                    '<span style="color:#ef4444;font-weight:bold;">FAILED</span>'
                )

            checks_rows += f"""
            <tr>
                <td>{self._safe(check.get('rule', 'N/A'))}</td>
                <td>{self._safe(check.get('threshold', 'N/A'))}</td>
                <td>{self._safe(check.get('actual', 'N/A'))}</td>
                <td>{badge}</td>
            </tr>
            """

        modules_rows = ""

        for module in cov.get("modules", []):
            module_pct = float(module.get("coverage_pct", 0))
            module_pct = max(0.0, min(100.0, module_pct))

            bar_color = (
                "#10b981" if module_pct >= 80 else "#f59e0b"
            )

            modules_rows += f"""
            <tr>
                <td><code>{self._safe(module.get('module', 'N/A'))}</code></td>
                <td>{self._safe(module.get('total_statements', 0))}</td>
                <td>{self._safe(module.get('covered_statements', 0))}</td>
                <td>{self._safe(module.get('missed_statements', 0))}</td>
                <td>
                    <div style="display:flex;align-items:center;gap:10px;">
                        <div style="flex:1;background:#334155;height:8px;border-radius:4px;overflow:hidden;">
                            <div style="width:{module_pct}%;background:{bar_color};height:100%;"></div>
                        </div>
                        <span>{module_pct}%</span>
                    </div>
                </td>
            </tr>
            """

        recommendation = qg.get(
            "recommendation", "No recommendation available."
        )

        html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>DevOps Continuous Testing - Executive Report</title>
<style>
* {{ box-sizing:border-box; margin:0; padding:0; font-family:Arial,Helvetica,sans-serif; }}
body {{ background:#0f172a; color:#f8fafc; padding:2rem; line-height:1.5; }}
.container {{ max-width:1100px; margin:auto; }}
.header {{ display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:1rem; border-bottom:1px solid #334155; padding-bottom:1.5rem; margin-bottom:2rem; }}
.title h1 {{ font-size:1.8rem; }}
.title p {{ color:#94a3b8; font-size:0.9rem; }}
.verdict {{ background:{verdict_bg}; color:{verdict_color}; border:1px solid {verdict_color}; padding:8px 16px; border-radius:30px; font-weight:bold; }}
.kpi-grid {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(200px,1fr)); gap:1rem; margin-bottom:2rem; }}
.kpi-card,.card {{ background:#1e293b; border:1px solid #334155; border-radius:8px; padding:1.25rem; }}
.kpi-card .label {{ color:#94a3b8; font-size:0.8rem; text-transform:uppercase; margin-bottom:0.5rem; }}
.kpi-card .value {{ font-size:1.7rem; font-weight:bold; }}
.card {{ padding:1.5rem; margin-bottom:2rem; overflow-x:auto; }}
.card h2 {{ font-size:1.2rem; margin-bottom:1rem; border-bottom:1px solid #334155; padding-bottom:0.75rem; }}
table {{ width:100%; border-collapse:collapse; text-align:left; font-size:0.9rem; }}
th,td {{ padding:10px 12px; border-bottom:1px solid #334155; }}
th {{ color:#94a3b8; text-transform:uppercase; font-size:0.75rem; }}
.recommendation {{ background:rgba(59,130,246,0.1); border-left:4px solid #3b82f6; padding:1rem; margin-top:1rem; }}
footer {{ text-align:center; color:#64748b; margin-top:3rem; font-size:0.85rem; }}
</style>
</head>
<body>
<div class="container">
<header class="header">
<div class="title">
<h1>DevOps Continuous Testing Framework</h1>
<p>Automated Pipeline Run Report | {self._safe(timestamp)}</p>
</div>
<div class="verdict">GATE: {self._safe(verdict)}</div>
</header>

<section class="kpi-grid">
<div class="kpi-card">
<div class="label">Total Test Cases</div>
<div class="value">{self._safe(total_tests)}</div>
<div class="label">Passed: {self._safe(passed_tests)} | Failed: {self._safe(failed_tests)} | Skipped: {self._safe(skipped_tests)}</div>
</div>
<div class="kpi-card">
<div class="label">Code Coverage</div>
<div class="value">{self._safe(coverage_pct)}%</div>
<div class="label">{self._safe(measurement_type)}</div>
</div>
<div class="kpi-card">
<div class="label">Latency SLA (P95)</div>
<div class="value">{self._safe(perf.get('p95_latency_ms', 'N/A'))} ms</div>
<div class="label">Throughput: {self._safe(perf.get('requests_per_second', 'N/A'))} RPS</div>
</div>
<div class="kpi-card">
<div class="label">SAST Security Scan</div>
<div class="value" style="color:{security_color};">{self._safe(security_count)}</div>
<div class="label">High/Critical vulnerabilities | {security_status}</div>
</div>
</section>

<section class="card">
<h2>DevOps Quality Gate Evaluation</h2>
<p>{self._safe(qg.get('passed_checks', 0))} of {self._safe(qg.get('checks_count', 0))} rules passed</p>
<table>
<thead><tr><th>Quality Gate Policy</th><th>Required Threshold</th><th>Observed Value</th><th>Status</th></tr></thead>
<tbody>{checks_rows}</tbody>
</table>
<div class="recommendation"><strong>Quality Gate Policy Engine:</strong> {self._safe(recommendation)}</div>
</section>

<section class="card">
<h2>Application Code Coverage</h2>
<table>
<thead><tr><th>Application Module</th><th>Total Statements</th><th>Covered</th><th>Missed</th><th>Coverage</th></tr></thead>
<tbody>{modules_rows}</tbody>
</table>
</section>

<section class="card">
<h2>Performance &amp; Load Distribution (Simulated Traffic)</h2>
<p>Virtual Users: <strong>{self._safe(perf.get('concurrency', 'N/A'))}</strong></p>
<p>Minimum Latency: <strong>{self._safe(perf.get('min_latency_ms', 'N/A'))} ms</strong></p>
<p>Median Latency (P50): <strong>{self._safe(perf.get('p50_latency_ms', 'N/A'))} ms</strong></p>
<p>95th Percentile: <strong>{self._safe(perf.get('p95_latency_ms', 'N/A'))} ms</strong></p>
<p>Maximum Latency: <strong>{self._safe(perf.get('max_latency_ms', 'N/A'))} ms</strong></p>
<p>Error Rate: <strong>{self._safe(perf.get('error_rate_pct', 'N/A'))}%</strong></p>
</section>

<footer>Generated by DevOps-Based Continuous Testing Framework | Automated Testing Report</footer>
</div>
</body>
</html>
"""

        html_path = os.path.join(
            self.output_dir, "executive_dashboard.html"
        )

        with open(html_path, "w", encoding="utf-8") as file:
            file.write(html_content)

        return html_path