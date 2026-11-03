"""
DevOps Platform Launcher
Starts both the Target Application Under Test (AUT) and the Continuous Testing Dashboard.
Automatically opens the browser to the interactive testing hub.
"""
import os
import sys
import time
import webbrowser
import threading
from werkzeug.serving import run_simple

# Ensure root directory is on PYTHONPATH
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from app.app import create_app
from dashboard.server import app as dashboard_app

def start_aut():
    """Run Application Under Test on port 5000."""
    aut_app = create_app()
    run_simple("127.0.0.1", 5000, aut_app, threaded=True, use_reloader=False)

def start_dashboard():
    """Run DevOps Continuous Testing Dashboard on port 8080."""
    run_simple("0.0.0.0", 8080, dashboard_app, threaded=True, use_reloader=False)

def main():
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass

    print("=" * 70)
    print(" [*] DEVOPS CONTINUOUS TESTING FRAMEWORK - PLATFORM LAUNCHER [*]")
    print("=" * 70)
    print(" [*] Target Application Under Test (AUT) : http://localhost:5000")
    print(" [*] Continuous Testing Web Dashboard    : http://localhost:8080")
    print(" [*] Executive HTML Test Report         : http://localhost:8080/reports/executive_dashboard.html")
    print("=" * 70)
    print(" Starting microservices and launching browser...")

    # Start AUT in background thread
    aut_thread = threading.Thread(target=start_aut, daemon=True)
    aut_thread.start()

    time.sleep(1.0)

    # Launch browser to dashboard
    try:
        webbrowser.open("http://localhost:8080")
    except Exception:
        pass

    # Start Dashboard on main thread
    try:
        start_dashboard()
    except KeyboardInterrupt:
        print("\n [!] Shutting down DevOps platform services. Goodbye!")

if __name__ == "__main__":
    main()
