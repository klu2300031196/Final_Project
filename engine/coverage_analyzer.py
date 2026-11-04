"""
Code Coverage Analyzer for AUT (Application Under Test).
Uses coverage.py to measure actual executed Python source lines.
"""

import os
from typing import Dict, Any

from coverage import Coverage


class CodeCoverageAnalyzer:
    """Measures application source-code coverage without rerunning pytest."""

    def __init__(self, target_dir: str = None):
        self.project_dir = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "..")
        )

        self.target_dir = os.path.abspath(
            target_dir or os.path.join(self.project_dir, "app")
        )

        self.coverage_file = os.path.join(
            self.project_dir, ".coverage"
        )

    def run_coverage_analysis(self) -> Dict[str, Any]:
        """
        Read coverage data collected during functional testing.
        Does not execute tests again.
        """

        if not os.path.isdir(self.target_dir):
            raise FileNotFoundError(
                f"Application source directory not found: {self.target_dir}"
            )

        if not os.path.isfile(self.coverage_file):
            raise FileNotFoundError(
                "Coverage data not found. Run the functional tests with coverage enabled."
            )

        cov = Coverage(
            data_file=self.coverage_file,
            source=[self.target_dir]
        )

        cov.load()

        data = cov.get_data()
        measured_files = sorted(data.measured_files())

        files_summary = []
        total_statements = 0
        total_covered = 0

        for filepath in measured_files:
            filepath = os.path.abspath(filepath)

            if not filepath.startswith(self.target_dir + os.sep):
                continue

            if not filepath.endswith(".py"):
                continue

            if not os.path.isfile(filepath):
                continue

            analysis = cov.analysis2(filepath)

            executable_lines = set(analysis[1])
            missing_lines = set(analysis[3])

            total = len(executable_lines)
            missed = len(missing_lines)
            covered = total - missed

            coverage_pct = (
                round(covered / total * 100.0, 1)
                if total > 0 else 0.0
            )

            total_statements += total
            total_covered += covered

            relative_name = os.path.relpath(
                filepath, self.target_dir
            )

            files_summary.append({
                "module": f"app/{relative_name.replace(os.sep, '/')}",
                "total_statements": total,
                "covered_statements": covered,
                "missed_statements": missed,
                "coverage_pct": coverage_pct
            })

        overall_pct = (
            round(total_covered / total_statements * 100.0, 1)
            if total_statements > 0 else 0.0
        )

        if total_statements == 0:
            raise RuntimeError(
                "No application source statements were measured. "
                "Check the coverage configuration and test imports."
            )

        return {
            "measurement_type": "coverage.py executed source-line coverage",
            "total_statements": total_statements,
            "covered_statements": total_covered,
            "missed_statements": total_statements - total_covered,
            "overall_coverage_pct": overall_pct,
            "modules": files_summary
        }


if __name__ == "__main__":
    import json

    analyzer = CodeCoverageAnalyzer()
    result = analyzer.run_coverage_analysis()

    print(json.dumps(result, indent=2))