"""
Code Coverage Analyzer for AUT (Application Under Test)
Analyzes executable AST statements vs executed statements to compute exact code coverage.
"""
import ast
import os
import sys
from typing import Dict, Any, List

class CodeCoverageAnalyzer:
    """Analyzes Python code coverage across Application Under Test modules."""

    def __init__(self, target_dir: str = None):
        self.target_dir = target_dir or os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "app"))

    def _get_executable_lines(self, filepath: str) -> set:
        """Parse Python file using AST to extract all executable statement line numbers."""
        executable = set()
        with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()

        try:
            tree = ast.parse(content, filename=filepath)
            for node in ast.walk(tree):
                # Nodes that represent executable statements
                if isinstance(node, (ast.stmt, ast.expr)) and hasattr(node, "lineno"):
                    # Exclude docstrings and module-level trivial statements
                    if isinstance(node, ast.Expr) and isinstance(node.value, ast.Constant) and isinstance(node.value.value, str):
                        continue
                    executable.add(node.lineno)
        except Exception:
            pass
        return executable

    def run_coverage_analysis(self) -> Dict[str, Any]:
        """Run full coverage analysis by executing test suite with trace tracking."""
        covered_lines_by_file = {}
        for root, _, files in os.walk(self.target_dir):
            for file in files:
                if file.endswith(".py") and not file.startswith("__"):
                    filepath = os.path.abspath(os.path.join(root, file))
                    covered_lines_by_file[filepath] = set()

        def trace_calls(frame, event, arg):
            if event == "line":
                filename = os.path.abspath(frame.f_code.co_filename)
                if filename in covered_lines_by_file:
                    covered_lines_by_file[filename].add(frame.f_lineno)
            return trace_calls

        # Temporarily enable system trace
        old_trace = sys.gettrace()
        sys.settrace(trace_calls)

        try:
            # Run pytest suite programmatically
            import pytest
            tests_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "tests"))
            pytest.main(["-q", tests_dir, "--disable-warnings"])
        finally:
            sys.settrace(old_trace)

        # Calculate module-wise and global coverage
        files_summary = []
        total_exec = 0
        total_covered = 0

        for filepath, covered_lines in covered_lines_by_file.items():
            rel_name = os.path.relpath(filepath, self.target_dir)
            exec_lines = self._get_executable_lines(filepath)
            
            # Hit count
            hits = len(exec_lines.intersection(covered_lines))
            total = len(exec_lines)
            cov_pct = round((hits / total) * 100.0, 1) if total > 0 else 100.0

            total_exec += total
            total_covered += hits

            files_summary.append({
                "module": f"app/{rel_name.replace(chr(92), '/')}",
                "total_statements": total,
                "covered_statements": hits,
                "missed_statements": total - hits,
                "coverage_pct": cov_pct
            })

        global_pct = round((total_covered / total_exec) * 100.0, 1) if total_exec > 0 else 0.0

        return {
            "total_statements": total_exec,
            "covered_statements": total_covered,
            "missed_statements": total_exec - total_covered,
            "overall_coverage_pct": global_pct,
            "modules": sorted(files_summary, key=lambda x: x["module"])
        }

if __name__ == "__main__":
    analyzer = CodeCoverageAnalyzer()
    res = analyzer.run_coverage_analysis()
    import json
    print(json.dumps(res, indent=2))
