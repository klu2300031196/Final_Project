"""
Main Flask REST API Application Under Test (AUT)
Serves RESTful endpoints for Auth, Products, Orders, and Payments.
Includes telemetry metrics and health check for DevOps Continuous Testing.
"""
import os
import time
import json
from datetime import datetime
from flask import Flask, request, jsonify, render_template, send_from_directory
from app.models import get_connection, init_db, hash_password, save_test_record, get_test_records
from app.auth import generate_token, authenticate_user, login_required
from app.services import PricingService, OrderStateMachine, PaymentSimulator

# Telemetry metrics storage
METRICS = {
    "total_requests": 0,
    "status_2xx": 0,
    "status_4xx": 0,
    "status_5xx": 0,
    "start_time": time.time(),
    "latencies_ms": []
}

def create_app(db_path=None):
    app = Flask(__name__, static_folder="static", static_url_path="/static")
    
    # Store custom db_path in app config if provided
    if db_path:
        app.config["DB_PATH"] = db_path
    else:
        app.config["DB_PATH"] = os.path.join(os.path.dirname(__file__), "aut_database.sqlite")

    # Initialize SQLite database
    init_db(app.config["DB_PATH"])

    def get_db():
        return get_connection(app.config["DB_PATH"])

    # Middleware: Track telemetry & request latency
    @app.before_request
    def before_request():
        request._start_time = time.time()
        METRICS["total_requests"] += 1

    @app.after_request
    def after_request(response):
        duration_ms = round((time.time() - getattr(request, "_start_time", time.time())) * 1000, 2)
        METRICS["latencies_ms"].append(duration_ms)
        if len(METRICS["latencies_ms"]) > 1000:
            METRICS["latencies_ms"].pop(0)

        code = response.status_code
        if 200 <= code < 300:
            METRICS["status_2xx"] += 1
        elif 400 <= code < 500:
            METRICS["status_4xx"] += 1
        elif code >= 500:
            METRICS["status_5xx"] += 1

        response.headers["X-Response-Time-Ms"] = str(duration_ms)
        response.headers["Access-Control-Allow-Origin"] = "*"
        response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
        response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, PATCH, OPTIONS"
        return response

    @app.route("/", methods=["GET"])
    def home():
        return send_from_directory(app.static_folder, "aut.html")

    # -------------------- HEALTH & TELEMETRY ENDPOINTS -------------------- #
    @app.route("/health", methods=["GET"])
    def health_check():
        try:
            conn = get_db()
            conn.execute("SELECT 1")
            conn.close()
            db_status = "healthy"
        except Exception as e:
            db_status = f"unhealthy: {str(e)}"

        uptime_seconds = round(time.time() - METRICS["start_time"], 1)
        return jsonify({
            "status": "UP",
            "service": "DevOps-AUT-OrderService",
            "version": "1.0.0",
            "database": db_status,
            "uptime_seconds": uptime_seconds,
            "timestamp": datetime.utcnow().isoformat()
        }), 200

    @app.route("/metrics", methods=["GET"])
    def metrics_endpoint():
        latencies = METRICS["latencies_ms"] or [0]
        avg_latency = round(sum(latencies) / len(latencies), 2)
        sorted_latencies = sorted(latencies)
        p95_idx = int(0.95 * len(sorted_latencies))
        p95_latency = round(sorted_latencies[min(p95_idx, len(sorted_latencies) - 1)], 2)

        return jsonify({
            "total_requests": METRICS["total_requests"],
            "status_2xx": METRICS["status_2xx"],
            "status_4xx": METRICS["status_4xx"],
            "status_5xx": METRICS["status_5xx"],
            "average_latency_ms": avg_latency,
            "p95_latency_ms": p95_latency,
            "active_samples": len(latencies)
        }), 200

    # -------------------- AUTHENTICATION ENDPOINTS -------------------- #
    @app.route("/api/auth/register", methods=["POST"])
    def register():
        data = request.get_json(silent=True) or {}
        username = data.get("username", "").strip()
        password = data.get("password", "").strip()
        email = data.get("email", "").strip()
        role = data.get("role", "customer").strip().lower()

        if not username or not password or not email:
            return jsonify({"error": "Missing required fields: username, password, email"}), 400

        if len(password) < 6:
            return jsonify({"error": "Password must be at least 6 characters"}), 400

        if role not in ["customer", "tester", "admin"]:
            role = "customer"

        conn = get_db()
        cur = conn.cursor()
        try:
            pwd_hash = hash_password(password)
            now = datetime.utcnow().isoformat()
            cur.execute("INSERT INTO users (username, password_hash, email, role, created_at) VALUES (?, ?, ?, ?, ?)",
                        (username, pwd_hash, email, role, now))
            conn.commit()
            user_id = cur.lastrowid
            token = generate_token(user_id, username, role)
            return jsonify({
                "message": "User registered successfully",
                "user_id": user_id,
                "username": username,
                "role": role,
                "token": token
            }), 201
        except Exception as e:
            conn.rollback()
            return jsonify({"error": "Username or email already exists", "detail": str(e)}), 409
        finally:
            conn.close()

    @app.route("/api/auth/login", methods=["POST"])
    def login():
        data = request.get_json(silent=True) or {}
        username = data.get("username", "").strip()
        password = data.get("password", "").strip()

        if not username or not password:
            return jsonify({"error": "Username and password required"}), 400

        user = authenticate_user(username, password)
        if not user:
            return jsonify({"error": "Invalid username or password"}), 401

        token = generate_token(user["id"], user["username"], user["role"])
        return jsonify({
            "message": "Authentication successful",
            "token": token,
            "user": {
                "id": user["id"],
                "username": user["username"],
                "email": user["email"],
                "role": user["role"]
            }
        }), 200

    @app.route("/api/auth/me", methods=["GET"])
    @login_required()
    def get_current_user():
        conn = get_db()
        cur = conn.cursor()
        cur.execute("SELECT id, username, email, role, created_at FROM users WHERE id = ?", (request.current_user["sub"],))
        user = cur.fetchone()
        conn.close()
        if not user:
            return jsonify({"error": "User not found"}), 404
        return jsonify({"user": dict(user)}), 200

    # -------------------- CONTINUOUS TESTING RECORDS ENDPOINTS -------------------- #
    @app.route("/api/test-records", methods=["GET"])
    def get_records():
        limit = request.args.get("limit", 10, type=int)
        records = get_test_records(limit=limit, db_path=app.config["DB_PATH"])
        return jsonify({"count": len(records), "records": records}), 200

    @app.route("/api/test-records", methods=["POST"])
    def add_record():
        data = request.get_json(silent=True) or {}
        pipeline_id = data.get("pipeline_id")
        if not pipeline_id:
            return jsonify({"error": "pipeline_id is required"}), 400

        try:
            rec_id = save_test_record(
                pipeline_id=pipeline_id,
                total_tests=int(data.get("total_tests", 0)),
                passed_tests=int(data.get("passed_tests", 0)),
                failed_tests=int(data.get("failed_tests", 0)),
                duration_seconds=float(data.get("duration_seconds", 0.0)),
                code_coverage_pct=float(data.get("code_coverage_pct", 0.0)),
                p95_latency_ms=float(data.get("p95_latency_ms", 0.0)),
                security_vulnerabilities=int(data.get("security_vulnerabilities", 0)),
                verdict=data.get("verdict", "PASSED"),
                db_path=app.config["DB_PATH"]
            )
            return jsonify({"message": "Test record saved", "id": rec_id, "pipeline_id": pipeline_id}), 201
        except Exception as e:
            return jsonify({"error": "Failed to save test record", "detail": str(e)}), 500

    # -------------------- PRODUCTS CATALOG ENDPOINTS -------------------- #
    @app.route("/api/products", methods=["GET"])
    def get_products():
        category = request.args.get("category")
        search = request.args.get("search")

        conn = get_db()
        cur = conn.cursor()
        query = "SELECT * FROM products WHERE 1=1"
        params = []

        if category:
            query += " AND category = ?"
            params.append(category)
        if search:
            query += " AND (name LIKE ? OR description LIKE ?)"
            params.extend([f"%{search}%", f"%{search}%"])

        cur.execute(query, params)
        rows = cur.fetchall()
        products = [dict(r) for r in rows]
        conn.close()
        return jsonify({"count": len(products), "products": products}), 200

    @app.route("/api/products/<int:prod_id>", methods=["GET"])
    def get_product(prod_id):
        conn = get_db()
        cur = conn.cursor()
        cur.execute("SELECT * FROM products WHERE id = ?", (prod_id,))
        row = cur.fetchone()
        conn.close()
        if not row:
            return jsonify({"error": "Product not found"}), 404
        return jsonify(dict(row)), 200

    @app.route("/api/products", methods=["POST"])
    @login_required(roles=["admin", "tester"])
    def create_product():
        data = request.get_json(silent=True) or {}
        name = data.get("name", "").strip()
        category = data.get("category", "General").strip()
        price = data.get("price")
        stock = data.get("stock", 0)
        desc = data.get("description", "")

        if not name or price is None:
            return jsonify({"error": "Product name and price are required"}), 400

        try:
            price = float(price)
            stock = int(stock)
            if price <= 0 or stock < 0:
                return jsonify({"error": "Price must be positive and stock non-negative"}), 400
        except ValueError:
            return jsonify({"error": "Invalid price or stock value"}), 400

        conn = get_db()
        cur = conn.cursor()
        now = datetime.utcnow().isoformat()
        cur.execute("INSERT INTO products (name, category, price, stock, description, created_at) VALUES (?, ?, ?, ?, ?, ?)",
                    (name, category, price, stock, desc, now))
        conn.commit()
        prod_id = cur.lastrowid
        conn.close()

        return jsonify({"message": "Product created", "id": prod_id, "name": name, "price": price, "stock": stock}), 201

    @app.route("/api/products/<int:prod_id>", methods=["DELETE"])
    @login_required(roles=["admin"])
    def delete_product(prod_id):
        conn = get_db()
        cur = conn.cursor()
        cur.execute("DELETE FROM products WHERE id = ?", (prod_id,))
        changes = conn.total_changes
        conn.commit()
        conn.close()
        if changes == 0:
            return jsonify({"error": "Product not found"}), 404
        return jsonify({"message": f"Product {prod_id} deleted successfully"}), 200

    # -------------------- ORDERS & CHECKOUT ENDPOINTS -------------------- #
    @app.route("/api/orders", methods=["POST"])
    @login_required()
    def create_order():
        data = request.get_json(silent=True) or {}
        items = data.get("items", [])
        promo_code = data.get("promo_code")

        if not items or not isinstance(items, list):
            return jsonify({"error": "Items list is required and cannot be empty"}), 400

        conn = get_db()
        cur = conn.cursor()

        try:
            enriched_items = []
            # Validate inventory and enrich item pricing
            for itm in items:
                prod_id = itm.get("product_id")
                qty = itm.get("quantity", 1)

                if not prod_id or qty <= 0:
                    return jsonify({"error": "Invalid product_id or quantity in items"}), 400

                cur.execute("SELECT id, name, price, stock FROM products WHERE id = ?", (prod_id,))
                prod = cur.fetchone()
                if not prod:
                    return jsonify({"error": f"Product with ID {prod_id} not found"}), 404

                if prod["stock"] < qty:
                    return jsonify({"error": f"Insufficient stock for {prod['name']}. Available: {prod['stock']}"}), 400

                enriched_items.append({
                    "product_id": prod["id"],
                    "name": prod["name"],
                    "price": prod["price"],
                    "quantity": qty
                })

            # Calculate pricing summary via service
            summary = PricingService.calculate_order_summary(enriched_items, promo_code)

            # Deduct inventory
            for itm in enriched_items:
                cur.execute("UPDATE products SET stock = stock - ? WHERE id = ?", (itm["quantity"], itm["product_id"]))

            now = datetime.utcnow().isoformat()
            user_id = request.current_user["sub"]
            cur.execute("""
            INSERT INTO orders (user_id, items_json, subtotal, discount, total_amount, status, created_at)
            VALUES (?, ?, ?, ?, ?, 'PENDING', ?)
            """, (user_id, json.dumps(enriched_items), summary["subtotal"], summary["discount"], summary["total_amount"], now))
            
            conn.commit()
            order_id = cur.lastrowid
            
            return jsonify({
                "message": "Order created successfully",
                "order_id": order_id,
                "summary": summary,
                "status": "PENDING"
            }), 201
        except ValueError as ve:
            conn.rollback()
            return jsonify({"error": str(ve)}), 400
        except Exception as e:
            conn.rollback()
            return jsonify({"error": "Failed to create order", "detail": str(e)}), 500
        finally:
            conn.close()

    @app.route("/api/orders", methods=["GET"])
    @login_required()
    def get_orders():
        user = request.current_user
        conn = get_db()
        cur = conn.cursor()

        if user.get("role") in ["admin", "tester"]:
            cur.execute("SELECT * FROM orders ORDER BY id DESC")
        else:
            cur.execute("SELECT * FROM orders WHERE user_id = ? ORDER BY id DESC", (user["sub"],))

        rows = cur.fetchall()
        orders = []
        for r in rows:
            d = dict(r)
            d["items"] = json.loads(d["items_json"])
            orders.append(d)
        conn.close()
        return jsonify({"count": len(orders), "orders": orders}), 200

    @app.route("/api/orders/<int:order_id>", methods=["GET"])
    @login_required()
    def get_order(order_id):
        conn = get_db()
        cur = conn.cursor()
        cur.execute("SELECT * FROM orders WHERE id = ?", (order_id,))
        row = cur.fetchone()
        conn.close()

        if not row:
            return jsonify({"error": "Order not found"}), 404

        order_data = dict(row)
        order_data["items"] = json.loads(order_data["items_json"])

        # Role authorization check: user can only see their own order unless admin/tester
        if request.current_user["role"] not in ["admin", "tester"] and order_data["user_id"] != request.current_user["sub"]:
            return jsonify({"error": "Unauthorized access to order"}), 403

        return jsonify(order_data), 200

    @app.route("/api/orders/<int:order_id>/pay", methods=["POST"])
    @login_required()
    def pay_order(order_id):
        conn = get_db()
        cur = conn.cursor()
        cur.execute("SELECT * FROM orders WHERE id = ?", (order_id,))
        order = cur.fetchone()

        if not order:
            conn.close()
            return jsonify({"error": "Order not found"}), 404

        if order["status"] != "PENDING":
            conn.close()
            return jsonify({"error": f"Cannot pay for order in state: {order['status']}"}), 400

        data = request.get_json(silent=True) or {}
        method = data.get("payment_method", "CREDIT_CARD")
        card_token = data.get("card_token", "CARD_VALID_1234")

        success, msg, txn_details = PaymentSimulator.process_payment(order["total_amount"], method, card_token)

        if not success:
            conn.close()
            return jsonify({"error": "Payment failed", "reason": msg}), 402

        now = datetime.utcnow().isoformat()
        cur.execute("""
        INSERT INTO payments (order_id, amount, method, transaction_id, status, processed_at)
        VALUES (?, ?, ?, ?, 'SUCCESS', ?)
        """, (order_id, txn_details["amount"], txn_details["method"], txn_details["transaction_id"], now))

        cur.execute("UPDATE orders SET status = 'PAID' WHERE id = ?", (order_id,))
        conn.commit()
        conn.close()

        return jsonify({
            "message": "Payment successful",
            "order_id": order_id,
            "status": "PAID",
            "payment": txn_details
        }), 200

    @app.route("/api/orders/<int:order_id>/status", methods=["PATCH"])
    @login_required(roles=["admin", "tester"])
    def update_order_status(order_id):
        data = request.get_json(silent=True) or {}
        new_status = data.get("status", "").upper()

        conn = get_db()
        cur = conn.cursor()
        cur.execute("SELECT status FROM orders WHERE id = ?", (order_id,))
        row = cur.fetchone()

        if not row:
            conn.close()
            return jsonify({"error": "Order not found"}), 404

        current_status = row["status"]
        if not OrderStateMachine.validate_transition(current_status, new_status):
            conn.close()
            return jsonify({"error": f"Invalid state transition from {current_status} to {new_status}"}), 400

        cur.execute("UPDATE orders SET status = ? WHERE id = ?", (new_status, order_id))
        conn.commit()
        conn.close()

        return jsonify({"message": "Order status updated", "order_id": order_id, "previous_status": current_status, "new_status": new_status}), 200

    return app

if __name__ == "__main__":
    app = create_app()
    app.run(host="0.0.0.0", port=5000, debug=True)
