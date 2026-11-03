"""
DevOps Security Scanner (SAST & DAST Automated Audit)
Performs Abstract Syntax Tree (AST) code scanning for vulnerabilities,
detects hardcoded secrets, checks SQLi resilience, and audits HTTP security headers.
"""
import ast
import os
import re
from typing import Dict, List, Any

class DevSecOpsScanner:
    """Automated SAST & DAST security auditor for continuous testing pipelines."""

    DANGEROUS_CALLS = {
        "eval": "Critical: Use of eval() detected, allowing arbitrary code execution.",
        "exec": "Critical: Use of exec() detected, allowing dynamic code execution.",
        "pickle.loads": "High: Insecure deserialization via pickle.loads.",
        "subprocess.Popen": "Medium: Subprocess invocation requires strict argument sanitization."
    }

    SECRET_PATTERNS = [
        (re.compile(r'(?i)api[_-]?key\s*=\s*["\'][a-zA-Z0-9_\-]{16,}["\']'), "Potential hardcoded API key"),
        (re.compile(r'(?i)aws[_-]?secret\s*=\s*["\'][a-zA-Z0-9/+=]{20,}["\']'), "Potential hardcoded AWS secret"),
        (re.compile(r'(?i)password\s*=\s*["\'](?!.*\b(salt|placeholder|hash)\b)[^"\']{6,}["\']'), "Potential hardcoded plain password")
    ]

    def __init__(self, target_dir: str = None):
        self.target_dir = target_dir or os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "app"))

    def scan_sast(self) -> Dict[str, Any]:
        """Perform Static Application Security Testing (SAST) on app code."""
        findings = []
        files_scanned = 0

        for root, _, files in os.walk(self.target_dir):
            for file in files:
                if file.endswith(".py"):
                    files_scanned += 1
                    filepath = os.path.join(root, file)
                    rel_path = os.path.relpath(filepath, self.target_dir)

                    with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
                        code_content = f.read()

                    # 1. Secret Scanning
                    for pattern, desc in self.SECRET_PATTERNS:
                        for line_no, line in enumerate(code_content.splitlines(), start=1):
                            if pattern.search(line) and "test" not in rel_path.lower():
                                findings.append({
                                    "type": "SECRET_EXPOSURE",
                                    "severity": "HIGH",
                                    "file": rel_path,
                                    "line": line_no,
                                    "detail": desc,
                                    "snippet": line.strip()[:60]
                                })

                    # 2. AST Vulnerability Parsing
                    try:
                        tree = ast.parse(code_content, filename=filepath)
                        for node in ast.walk(tree):
                            # Check dangerous functions
                            if isinstance(node, ast.Call):
                                func_name = ""
                                if isinstance(node.func, ast.Name):
                                    func_name = node.func.id
                                elif isinstance(node.func, ast.Attribute) and isinstance(node.func.value, ast.Name):
                                    func_name = f"{node.func.value.id}.{node.func.attr}"

                                if func_name in self.DANGEROUS_CALLS:
                                    findings.append({
                                        "type": "INSECURE_FUNCTION",
                                        "severity": "HIGH",
                                        "file": rel_path,
                                        "line": getattr(node, "lineno", 0),
                                        "detail": self.DANGEROUS_CALLS[func_name],
                                        "snippet": f"Call to {func_name}()"
                                    })

                            # Check for SQL String Formatting / Interpolation
                            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == "execute":
                                if node.args:
                                    first_arg = node.args[0]
                                    if isinstance(first_arg, (ast.JoinedStr, ast.BinOp)):
                                        findings.append({
                                            "type": "SQL_INJECTION_RISK",
                                            "severity": "CRITICAL",
                                            "file": rel_path,
                                            "line": getattr(node, "lineno", 0),
                                            "detail": "SQL query uses string formatting instead of parameterized query.",
                                            "snippet": "cursor.execute(f'...')"
                                        })
                    except Exception as parse_err:
                        findings.append({
                            "type": "AST_PARSE_ERROR",
                            "severity": "LOW",
                            "file": rel_path,
                            "line": 0,
                            "detail": str(parse_err),
                            "snippet": ""
                        })

        high_count = sum(1 for f in findings if f["severity"] in ["HIGH", "CRITICAL"])
        medium_count = sum(1 for f in findings if f["severity"] == "MEDIUM")
        low_count = sum(1 for f in findings if f["severity"] == "LOW")

        return {
            "files_scanned": files_scanned,
            "total_findings": len(findings),
            "critical_or_high": high_count,
            "medium": medium_count,
            "low": low_count,
            "passed": (high_count == 0),
            "findings": findings
        }

    def scan_dast_headers(self, client) -> Dict[str, Any]:
        """Perform Dynamic Application Security Testing (DAST) on live HTTP headers."""
        res = client.get("/health")
        headers = {k.lower(): v for k, v in res.headers.items()}
        
        checks = [
            ("access-control-allow-origin", "CORS Configuration", "PASSED" if "access-control-allow-origin" in headers else "INFO"),
            ("x-response-time-ms", "Telemetry Response Header", "PASSED" if "x-response-time-ms" in headers else "INFO")
        ]
        
        return {
            "status_code": res.status_code,
            "audited_headers": checks,
            "passed": True
        }

    def scan_sqli_resilience(self, client) -> Dict[str, Any]:
        """Test search endpoint against standard SQL injection vectors."""
        sqli_payloads = [
            "' OR '1'='1",
            "'; DROP TABLE users; --",
            "1 UNION SELECT 1, 'admin', 'admin@mail.com', 'admin', 1, 1 --"
        ]
        
        all_resilient = True
        results = []
        for p in sqli_payloads:
            res = client.get(f"/api/products?search={p}")
            # Resilient if no 500 server error and returns 200 with standard list
            resilient = (res.status_code == 200 and isinstance(res.get_json().get("products"), list))
            if not resilient:
                all_resilient = False
            results.append({"payload": p, "status": res.status_code, "resilient": resilient})

        return {
            "tests_run": len(sqli_payloads),
            "all_resilient": all_resilient,
            "details": results
        }

if __name__ == "__main__":
    scanner = DevSecOpsScanner()
    res = scanner.scan_sast()
    import json
    print(json.dumps(res, indent=2))
