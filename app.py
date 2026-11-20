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


def parse_bool(value, default=False):
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in ("true", "1", "yes", "on"):
            return True
        if normalized in ("false", "0", "no", "off", ""):
            return False
    return default


def get_db_connection():
    """Creates a new PostgreSQL database connection."""
    return psycopg2.connect(**DB_CONFIG)


def init_db():
    """Automatically creates required tables and seeds initial data if empty."""
    conn = None
    cur = None
    try:
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
    except Exception as exc:
        if conn:
            conn.rollback()
        print(f"[DB INIT ERROR] {exc}")
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()


def load_urls_json():
    """Loads URL definitions safely from urls.json."""
    fallback = {
        "service": "Python TaskFlow & Persistence Engine",
        "base_url": "http://localhost:5000",
        "urls": []
    }
    if not URLS_FILE.exists():
        return fallback
    try:
        with URLS_FILE.open("r", encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, dict) else fallback
    except Exception as exc:
        print(f"[URLS JSON ERROR] {exc}")
        return fallback


# ==========================================
# 2. Multi-Page UI Routes
# ==========================================
@app.route("/")
@app.route("/audit")
@app.route("/urls")
@app.route("/status")
def multi_page_app():
    resp = send_from_directory(app.static_folder, "index.html")
    resp.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    return resp


# ==========================================
# 3. REST API Endpoints (Tasks, Audit, URLs & Status)
# ==========================================
@app.route("/api/tasks", methods=["GET"])
def get_tasks():
    conn = None
    cur = None
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("SELECT id, title, completed FROM tasks ORDER BY id ASC;")
        tasks = cur.fetchall()
        for row in tasks:
            row["completed"] = bool(row["completed"])
        return jsonify(tasks), 200
    except Exception as exc:
        return jsonify({"error": f"Database error: {exc}"}), 500
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()


@app.route("/api/tasks", methods=["POST"])
def create_task():
    data = request.get_json(silent=True) or {}
    title = str(data.get("title", "")).strip()
    completed = parse_bool(data.get("completed", False), default=False)

    if not title:
        return jsonify({"error": "Task title is required"}), 400

    conn = None
    cur = None
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)

        cur.execute(
            "INSERT INTO tasks (title, completed) VALUES (%s, %s) RETURNING id, title, completed;",
            (title, completed)
        )
        new_task = cur.fetchone()
        new_task["completed"] = bool(new_task["completed"])

        status_label = "Completed" if completed else "Pending"
        cur.execute(
            "INSERT INTO task_audit_log (operation_type, details) VALUES (%s, %s);",
            ("INSERT", f"Created task #{new_task['id']}: '{title}' ({status_label})")
        )

        conn.commit()
        return jsonify(new_task), 201
    except Exception as exc:
        if conn:
            conn.rollback()
        return jsonify({"error": f"Failed to create task: {exc}"}), 500
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()


@app.route("/api/tasks/<int:task_id>", methods=["PUT"])
def update_task(task_id):
    data = request.get_json(silent=True) or {}

    conn = None
    cur = None
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)

        cur.execute("SELECT id, title, completed FROM tasks WHERE id = %s;", (task_id,))
        existing = cur.fetchone()
        if not existing:
            return jsonify({"error": "Task not found"}), 404

        new_title = (
            str(data["title"]).strip()
            if "title" in data and data["title"] is not None
            else existing["title"]
        )
        if not new_title:
            return jsonify({"error": "Task title cannot be empty"}), 400

        new_completed = (
            parse_bool(data["completed"], default=bool(existing["completed"]))
            if "completed" in data
            else bool(existing["completed"])
        )

        cur.execute(
            "UPDATE tasks SET title = %s, completed = %s WHERE id = %s RETURNING id, title, completed;",
            (new_title, new_completed, task_id)
        )
        updated_task = cur.fetchone()
        updated_task["completed"] = bool(updated_task["completed"])

        status_text = "Completed" if new_completed else "Pending"
        cur.execute(
            "INSERT INTO task_audit_log (operation_type, details) VALUES (%s, %s);",
            ("UPDATE", f"Updated task #{task_id} ('{new_title}') -> {status_text}")
        )

        conn.commit()
        return jsonify(updated_task), 200
    except Exception as exc:
        if conn:
            conn.rollback()
        return jsonify({"error": f"Failed to update task: {exc}"}), 500
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()


@app.route("/api/tasks/<int:task_id>", methods=["DELETE"])
def delete_task(task_id):
    conn = None
    cur = None
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)

        cur.execute("DELETE FROM tasks WHERE id = %s RETURNING id, title;", (task_id,))
        deleted_task = cur.fetchone()

        if not deleted_task:
            return jsonify({"error": "Task not found"}), 404

        cur.execute(
            "INSERT INTO task_audit_log (operation_type, details) VALUES (%s, %s);",
            ("DELETE", f"Deleted task #{task_id}: '{deleted_task['title']}'")
        )

        conn.commit()
        return jsonify({"message": "Deleted successfully", "id": deleted_task["id"]}), 200
    except Exception as exc:
        if conn:
            conn.rollback()
        return jsonify({"error": f"Failed to delete task: {exc}"}), 500
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()


@app.route("/api/audit", methods=["GET"])
def get_audit_logs():
    conn = None
    cur = None
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("""
            SELECT id, operation_type AS "operationType", details, timestamp
            FROM task_audit_log
            ORDER BY id ASC;
        """)
        logs = cur.fetchall()
        return jsonify(logs), 200
    except Exception as exc:
        return jsonify({"error": f"Failed to load audit logs: {exc}"}), 500
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()


@app.route("/api/urls", methods=["GET"])
def get_urls():
    return jsonify(load_urls_json()), 200


@app.route("/api/status", methods=["GET"])
def api_status():
    conn = None
    cur = None
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)

        cur.execute("SELECT COUNT(*) AS total_tasks FROM tasks;")
        total_tasks = cur.fetchone()["total_tasks"]

        cur.execute("SELECT COUNT(*) AS completed_tasks FROM tasks WHERE completed = TRUE;")
        completed_tasks = cur.fetchone()["completed_tasks"]

        cur.execute("SELECT COUNT(*) AS total_audits FROM task_audit_log;")
        total_audits = cur.fetchone()["total_audits"]

        url_map = {item["name"]: item["url"] for item in load_urls_json().get("urls", [])}

        return jsonify({
            "service": "Python TaskFlow & Persistence Engine",
            "status": "running",
            "database": DB_CONFIG["dbname"],
            "urls_file": str(URLS_FILE),
            "urls": url_map,
            "counts": {
                "tasks": total_tasks,
                "completed_tasks": completed_tasks,
                "pending_tasks": total_tasks - completed_tasks,
                "audit_logs": total_audits
            }
        }), 200
    except Exception as exc:
        return jsonify({"service": "Python TaskFlow & Persistence Engine", "status": "degraded", "error": str(exc)}), 500
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()


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