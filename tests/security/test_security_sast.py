"""
Pytest Security & DevSecOps Validation Test
Enforces zero critical/high security vulnerabilities in the continuous testing pipeline.
"""
import pytest
from tests.security.security_scanner import DevSecOpsScanner

def test_sast_code_vulnerabilities():
    """Ensure no critical or high severity security vulnerabilities exist in application source."""
    scanner = DevSecOpsScanner()
    report = scanner.scan_sast()
    
    assert report["critical_or_high"] == 0, f"Found {report['critical_or_high']} high/critical vulnerabilities: {report['findings']}"
    assert report["passed"] is True

def test_sqli_resilience_probe(client):
    """Ensure database query layer handles SQL injection injection probes securely."""
    scanner = DevSecOpsScanner()
    report = scanner.scan_sqli_resilience(client)
    assert report["all_resilient"] is True

def test_dast_security_headers(client):
    """Verify HTTP response headers adhere to expected security & telemetry standards."""
    scanner = DevSecOpsScanner()
    report = scanner.scan_dast_headers(client)
    assert report["passed"] is True
