import json
from pathlib import Path
from flask import Flask, request, jsonify, send_from_directory
import psycopg2
from psycopg2.extras import RealDictCursor

BASE_DIR = Path(__file__).resolve().parent
URLS_FILE = BASE_DIR / "urls.json"

app = Flask(__name__, static_folder="static")

# ==========================================
# 1. PostgreSQL Database Configuration
# ==========================================
DB_CONFIG = {
    "dbname": "task_db",
    "user": "postgres",
    "password": "your_secure_password",  # <-- UPDATE THIS TO YOUR POSTGRES PASSWORD
    "host": "localhost",
    "port": "5432"
}


def get_db_connection():
    return psycopg2.connect(**DB_CONFIG)


def init_db():
    """Automatically creates tables in PostgreSQL if they do not exist."""
    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS tasks (
            id SERIAL PRIMARY KEY,
            title VARCHAR(255) NOT NULL,
            completed BOOLEAN NOT NULL DEFAULT FALSE
        );
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS task_audit_log (
            id SERIAL PRIMARY KEY,
            operation_type VARCHAR(50) NOT NULL,
            details TEXT NOT NULL,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)

    cur.execute("SELECT COUNT(*) FROM tasks;")
    if cur.fetchone()[0] == 0:
        cur.execute(
            "INSERT INTO tasks (title, completed) VALUES (%s, %s) RETURNING id;",
            ("Welcome to Full-Stack Python & PostgreSQL Engine", False)
        )
        new_id = cur.fetchone()[0]
        cur.execute(
            "INSERT INTO task_audit_log (operation_type, details) VALUES (%s, %s);",
            ("INSERT", f"Initialized system with sample task ID #{new_id}")
        )

    conn.commit()
    cur.close()
    conn.close()


def load_urls_json():
    """Loads URL definitions from urls.json."""
    if not URLS_FILE.exists():
        return {
            "service": "Python TaskFlow & Persistence Engine",
            "base_url": "http://localhost:5000",
            "urls": []
        }
    with URLS_FILE.open("r", encoding="utf-8") as f:
        return json.load(f)


# ==========================================
# 2. Multi-Page UI Routes (All serve index.html with route-aware state)
# ==========================================
@app.route("/")
@app.route("/audit")
@app.route("/urls")
@app.route("/status")
def multi_page_app():
    return send_from_directory(app.static_folder, "index.html")


# ==========================================
# 3. REST API Endpoints (Tasks, Audit, URLs & Status)
# ==========================================
@app.route("/api/tasks", methods=["GET"])
def get_tasks():
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute("SELECT id, title, completed FROM tasks ORDER BY id ASC;")
    tasks = cur.fetchall()
    cur.close()
    conn.close()
    return jsonify(tasks), 200


@app.route("/api/tasks", methods=["POST"])
def create_task():
    data = request.get_json(silent=True) or {}
    title = str(data.get("title", "")).strip()
    if not title:
        return jsonify({"error": "Task title is required"}), 400

    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)

    cur.execute(
        "INSERT INTO tasks (title, completed) VALUES (%s, %s) RETURNING id, title, completed;",
        (title, False)
    )
    new_task = cur.fetchone()

    cur.execute(
        "INSERT INTO task_audit_log (operation_type, details) VALUES (%s, %s);",
        ("INSERT", f"Created task #{new_task['id']}: '{title}'")
    )

    conn.commit()
    cur.close()
    conn.close()
    return jsonify(new_task), 201


@app.route("/api/tasks/<int:task_id>", methods=["PUT"])
def update_task(task_id):
    data = request.get_json(silent=True) or {}
    title = data.get("title")
    completed = data.get("completed")

    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)

    cur.execute(
        "UPDATE tasks SET title = %s, completed = %s WHERE id = %s RETURNING id, title, completed;",
        (title, completed, task_id)
    )
    updated_task = cur.fetchone()

    if not updated_task:
        cur.close()
        conn.close()
        return jsonify({"error": "Task not found"}), 404

    status_text = "Completed" if completed else "Pending"
    cur.execute(
        "INSERT INTO task_audit_log (operation_type, details) VALUES (%s, %s);",
        ("UPDATE", f"Updated task #{task_id} ('{title}') status to {status_text}")
    )

    conn.commit()
    cur.close()
    conn.close()
    return jsonify(updated_task), 200


@app.route("/api/tasks/<int:task_id>", methods=["DELETE"])
def delete_task(task_id):
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)

    cur.execute("DELETE FROM tasks WHERE id = %s RETURNING id, title;", (task_id,))
    deleted_task = cur.fetchone()

    if not deleted_task:
        cur.close()
        conn.close()
        return jsonify({"error": "Task not found"}), 404

    cur.execute(
        "INSERT INTO task_audit_log (operation_type, details) VALUES (%s, %s);",
        ("DELETE", f"Deleted task #{task_id}: '{deleted_task['title']}'")
    )

    conn.commit()
    cur.close()
    conn.close()
    return jsonify({"message": "Deleted successfully"}), 200


@app.route("/api/audit", methods=["GET"])
def get_audit_logs():
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute("""
        SELECT id, operation_type AS "operationType", details, timestamp
        FROM task_audit_log
        ORDER BY id ASC;
    """)
    logs = cur.fetchall()
    cur.close()
    conn.close()
    return jsonify(logs), 200


@app.route("/api/urls", methods=["GET"])
def get_urls():
    return jsonify(load_urls_json()), 200


@app.route("/api/status", methods=["GET"])
def api_status():
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)

    cur.execute("SELECT COUNT(*) AS total_tasks FROM tasks;")
    total_tasks = cur.fetchone()["total_tasks"]

    cur.execute("SELECT COUNT(*) AS total_audits FROM task_audit_log;")
    total_audits = cur.fetchone()["total_audits"]

    cur.close()
    conn.close()

    url_map = {item["name"]: item["url"] for item in load_urls_json().get("urls", [])}

    return jsonify({
        "service": "Python TaskFlow & Persistence Engine",
        "status": "running",
        "database": DB_CONFIG["dbname"],
        "urls_file": str(URLS_FILE),
        "urls": url_map,
        "counts": {
            "tasks": total_tasks,
            "audit_logs": total_audits
        }
    }), 200


# ==========================================
# 4. Application Entry Point
# ==========================================
if __name__ == "__main__":
    print("==========================================")
    print("Initializing PostgreSQL Schema...")
    init_db()
    print("Python TaskFlow Engine is running!")
    print("Workspace : http://localhost:5000/")
    print("Audit Page: http://localhost:5000/audit")
    print("URLs Page : http://localhost:5000/urls")
    print("Status    : http://localhost:5000/status")
    print("==========================================")
    app.run(host="0.0.0.0", port=5000, debug=True)