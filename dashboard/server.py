
"""
DevOps Continuous Testing Dashboard - Backend Server
Provides real-time pipeline execution, SSE log streaming,
telemetry analytics, and report downloads.
"""

import os
import sys
import json
import time
import queue
import threading
from datetime import datetime

from flask import (
    Flask,
    jsonify,
    request,
    Response,
    render_template,
    send_from_directory
)
import requests

from engine.test_runner import ContinuousTestingRunner


app = Flask(
    __name__,
    template_folder="templates",
    static_folder="static"
)


# Global in-memory log queue & pipeline execution lock
LOG_QUEUES = []
PIPELINE_LOCK = threading.Lock()
PIPELINE_RUNNING = False
LATEST_RESULT = None
RUN_HISTORY = []

REPORTS_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "reports")
)


def load_initial_reports():
    global LATEST_RESULT, RUN_HISTORY

    json_path = os.path.join(REPORTS_DIR, "test_report.json")

    if os.path.exists(json_path):
        try:
            with open(json_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            LATEST_RESULT = data

            RUN_HISTORY.append({
                "id": data.get("pipeline_id", "CT-INIT"),
                "timestamp": data.get(
                    "timestamp",
                    datetime.utcnow().isoformat()
                ),
                "duration": data.get("duration_seconds", 5.2),
                "verdict": data.get(
                    "quality_gate", {}
                ).get("verdict", "PASSED"),
                "tests": data.get("total_tests", 53)
            })

        except Exception as e:
            print(f"[WARNING] Could not load initial report: {e}")


load_initial_reports()


def broadcast_log(line: str):
    """Deliver log line to all active SSE subscribers."""

    for q in list(LOG_QUEUES):
        try:
            q.put_nowait(line)
        except queue.Full:
            pass
        except Exception:
            pass


@app.route("/")
def index():
    return render_template("dashboard.html")


@app.route("/api/status")
def get_status():
    """Return dashboard status and AUT connectivity."""

    aut_status = "UNKNOWN"

    # Local development uses localhost.
    # Docker Compose overrides this with http://aut-service:5000/health.
    aut_url = os.environ.get(
        "AUT_HEALTH_URL",
        "http://127.0.0.1:5000/health"
    )

    try:
        res = requests.get(
            aut_url,
            timeout=2
        )

        if res.status_code == 200:
            aut_status = "ONLINE"
        else:
            aut_status = "OFFLINE"

    except requests.RequestException as e:
        print(f"[INFO] AUT health check unavailable: {e}")
        aut_status = "STANDALONE_READY"

    return jsonify({
        "aut_status": aut_status,
        "pipeline_running": PIPELINE_RUNNING,
        "latest_pipeline_id": (
            LATEST_RESULT.get("pipeline_id")
            if LATEST_RESULT else None
        ),
        "timestamp": datetime.utcnow().isoformat()
    })


@app.route("/api/latest-report")
def get_latest_report():
    if LATEST_RESULT:
        return jsonify(LATEST_RESULT)

    return jsonify({
        "message": "No pipeline runs yet. Click 'Trigger Pipeline' to run!"
    }), 404


@app.route("/api/history")
def get_history():
    try:
        # Lazy import: load database models only when history is requested.
        from app.models import get_test_records

        records = get_test_records(limit=20)
        formatted_runs = []

        for r in records:
            formatted_runs.append({
                "id": r["pipeline_id"],
                "timestamp": r["executed_at"],
                "duration": r["duration_seconds"],
                "verdict": r["verdict"],
                "tests": r["total_tests"],
                "passed": r["passed_tests"],
                "failed": r["failed_tests"],
                "coverage": r["code_coverage_pct"],
                "latency_p95": r["p95_latency_ms"]
            })

        return jsonify({"runs": formatted_runs})

    except Exception as e:
        print(f"[WARNING] Could not load pipeline history: {e}")

        return jsonify({
            "runs": list(reversed(RUN_HISTORY))
        })


@app.route("/api/pipeline/trigger", methods=["POST"])
def trigger_pipeline():
    global PIPELINE_RUNNING

    if PIPELINE_RUNNING:
        return jsonify({
            "error": "A pipeline run is already in progress"
        }), 409

    def worker():
        global PIPELINE_RUNNING, LATEST_RESULT, RUN_HISTORY

        with PIPELINE_LOCK:
            PIPELINE_RUNNING = True

            broadcast_log(
                "[START] Continuous Testing Pipeline initiated via Web Hub..."
            )

            try:
                runner = ContinuousTestingRunner(
                    log_callback=broadcast_log
                )

                result = runner.run_full_pipeline()

                LATEST_RESULT = result

                RUN_HISTORY.append({
                    "id": result.get("pipeline_id"),
                    "timestamp": result.get("timestamp"),
                    "duration": result.get("duration_seconds"),
                    "verdict": result.get(
                        "quality_gate", {}
                    ).get("verdict", "PASSED"),
                    "tests": result.get("total_tests")
                })

                broadcast_log(
                    "[COMPLETE] Pipeline execution finished with verdict: "
                    f"{result['quality_gate']['verdict']}"
                )

            except Exception as e:
                broadcast_log(
                    f"[ERROR] Pipeline execution failed: {str(e)}"
                )

            finally:
                PIPELINE_RUNNING = False

    thread = threading.Thread(
        target=worker,
        daemon=True
    )

    thread.start()

    return jsonify({
        "message": "Continuous Testing Pipeline triggered successfully",
        "timestamp": datetime.utcnow().isoformat()
    }), 202


@app.route("/api/pipeline/logs/stream")
def stream_logs():
    """SSE endpoint for streaming real-time pipeline execution logs."""

    q = queue.Queue(maxsize=500)
    LOG_QUEUES.append(q)

    def event_stream():
        yield "data: [CONNECTED] Connected to Continuous Testing Log Stream\n\n"

        try:
            while True:
                try:
                    line = q.get(timeout=25.0)
                    yield f"data: {line}\n\n"

                except queue.Empty:
                    # Keep-alive heartbeat
                    yield ": ping\n\n"

        except GeneratorExit:
            if q in LOG_QUEUES:
                LOG_QUEUES.remove(q)

    return Response(
        event_stream(),
        mimetype="text/event-stream"
    )


@app.route("/reports/<path:filename>")
def download_report(filename):
    return send_from_directory(
        REPORTS_DIR,
        filename
    )


def run_dashboard(host="0.0.0.0", port=8080):
    print(
        f"[*] Starting DevOps Continuous Testing Dashboard "
        f"on http://localhost:{port}"
    )

    app.run(
        host=host,
        port=port,
        debug=False,
        threaded=True
    )


if __name__ == "__main__":
    run_dashboard()