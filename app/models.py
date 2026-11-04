"""
Database Models & SQLite Operations for the Application Under Test (AUT).
"""
import sqlite3
import os
import json
import hashlib
from datetime import datetime, timezone
DB_FILE = os.environ.get("AUT_DB_FILE", os.path.join(os.path.dirname(__file__), "aut_database.sqlite"))

def get_connection(db_path=None):
    path = db_path or DB_FILE
    conn = sqlite3.connect(path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def hash_password(password: str, salt: str = "devops_salt_2026") -> str:
    """Hash password using SHA-256 with salt."""
    return hashlib.sha256(f"{salt}:{password}".encode("utf-8")).hexdigest()

def init_db(db_path=None):
    """Initialize database tables and seed sample data."""
    conn = get_connection(db_path)
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        email TEXT UNIQUE NOT NULL,
        role TEXT NOT NULL DEFAULT 'customer',
        created_at TEXT NOT NULL
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS products (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        category TEXT NOT NULL,
        price REAL NOT NULL,
        stock INTEGER NOT NULL,
        description TEXT,
        created_at TEXT NOT NULL
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS orders (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        items_json TEXT NOT NULL,
        subtotal REAL NOT NULL,
        discount REAL NOT NULL DEFAULT 0.0,
        total_amount REAL NOT NULL,
        status TEXT NOT NULL DEFAULT 'PENDING',
        created_at TEXT NOT NULL,
        FOREIGN KEY (user_id) REFERENCES users(id)
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS payments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        order_id INTEGER NOT NULL,
        amount REAL NOT NULL,
        method TEXT NOT NULL,
        transaction_id TEXT NOT NULL,
        status TEXT NOT NULL DEFAULT 'SUCCESS',
        processed_at TEXT NOT NULL,
        FOREIGN KEY (order_id) REFERENCES orders(id)
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS test_records (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        pipeline_id TEXT NOT NULL UNIQUE,
        total_tests INTEGER NOT NULL,
        passed_tests INTEGER NOT NULL,
        failed_tests INTEGER NOT NULL,
        duration_seconds REAL NOT NULL,
        code_coverage_pct REAL NOT NULL,
        p95_latency_ms REAL NOT NULL,
        security_vulnerabilities INTEGER NOT NULL,
        verdict TEXT NOT NULL,
        executed_at TEXT NOT NULL
    )
    """)

    conn.commit()

    # Seed initial test data if users table is empty
    cur.execute("SELECT COUNT(*) FROM users")
    if cur.fetchone()[0] == 0:
        seed_data(conn)

    conn.close()

def seed_data(conn):
    cur = conn.cursor()
    now = datetime.now(timezone.utc).isoformat()

    # Default Users
    admin_hash = hash_password("Admin@123")
    user_hash = hash_password("User@123")
    cur.execute("INSERT INTO users (username, password_hash, email, role, created_at) VALUES (?, ?, ?, ?, ?)",
                ("admin", admin_hash, "admin@company.com", "admin", now))
    cur.execute("INSERT INTO users (username, password_hash, email, role, created_at) VALUES (?, ?, ?, ?, ?)",
                ("qa_tester", user_hash, "tester@company.com", "tester", now))
    cur.execute("INSERT INTO users (username, password_hash, email, role, created_at) VALUES (?, ?, ?, ?, ?)",
                ("john_doe", user_hash, "john@example.com", "customer", now))

    # Sample Products
    products = [
        ("Cloud Microservice License", "Software", 199.99, 50, "Scalable cloud orchestration license"),
        ("DevOps CI/CD Pipeline Kit", "Tools", 89.50, 100, "Automated Jenkins and GitHub Actions template suite"),
        ("Continuous Testing Agent", "Automation", 149.00, 30, "AI-driven test agent for regression validation"),
        ("Docker Container Security Suite", "Security", 249.99, 20, "Vulnerability scanner for OCI containers"),
        ("Kubernetes Cluster Monitor", "Monitoring", 120.00, 45, "Real-time telemetry and Prometheus exporter")
    ]
    for p in products:
        cur.execute("INSERT INTO products (name, category, price, stock, description, created_at) VALUES (?, ?, ?, ?, ?, ?)",
                    (p[0], p[1], p[2], p[3], p[4], now))

    conn.commit()

def save_test_record(pipeline_id: str, total_tests: int, passed_tests: int, failed_tests: int,
                     duration_seconds: float, code_coverage_pct: float, p95_latency_ms: float,
                     security_vulnerabilities: int, verdict: str, db_path=None) -> int:
    """Save automated test pipeline run into SQLite test_records table."""
    conn = get_connection(db_path)
    cur = conn.cursor()
    now = datetime.now(timezone.utc).isoformat()
    cur.execute("""
    INSERT OR REPLACE INTO test_records 
    (pipeline_id, total_tests, passed_tests, failed_tests, duration_seconds, code_coverage_pct, p95_latency_ms, security_vulnerabilities, verdict, executed_at)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (pipeline_id, total_tests, passed_tests, failed_tests, duration_seconds, code_coverage_pct, p95_latency_ms, security_vulnerabilities, verdict, now))
    conn.commit()
    record_id = cur.lastrowid
    conn.close()
    return record_id

def get_test_records(limit: int = 10, db_path=None):
    """Retrieve recent test pipeline runs from SQLite test_records table."""
    conn = get_connection(db_path)
    cur = conn.cursor()
    cur.execute("SELECT * FROM test_records ORDER BY id DESC LIMIT ?", (limit,))
    rows = cur.fetchall()
    conn.close()
    return [dict(r) for r in rows]
