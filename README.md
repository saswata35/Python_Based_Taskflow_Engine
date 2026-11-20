# 🚀 Python_Taskflow_Engine 

A full-stack, multi-page task management and real-time audit logging application built with **Python (Flask)**, **PostgreSQL (`psycopg2`)**, and a responsive **Bootstrap 5** frontend (`TaskFlow Studio`). This system provides persistent task tracking, ACID transactions, endpoint metadata via `urls.json`, and a dedicated database operations audit trail tracking every `INSERT`, `UPDATE`, and `DELETE` action.

---

## 🛠️ Tech Stack & Architecture

- **Backend:** Python 3.13, Flask, RESTful JSON APIs
- **Database:** PostgreSQL (`psycopg2`, managed via `psql` CLI & pgAdmin 4)
- **Frontend:** HTML5, CSS3, JavaScript (ES6+), Bootstrap 5, Bootstrap Icons
- **Environment & Tooling:** Windows PowerShell, `.venv`, Visual Studio Code, Git & GitHub

---

## 📊 Database Schema

The application automatically initializes and uses two core relational tables in PostgreSQL (`task_db`):

### 1. `tasks` Table (Core Entity)
- `id`: `SERIAL` (Primary Key)
- `title`: `VARCHAR(255)` (Not Null)
- `completed`: `BOOLEAN` (Not Null, Default: `FALSE`)

### 2. `task_audit_log` Table (Audit Trail)
- `id`: `SERIAL` (Primary Key)
- `operation_type`: `VARCHAR(50)` (`INSERT`, `UPDATE`, `DELETE`)
- `details`: `TEXT` (Not Null — operation description)
- `timestamp`: `TIMESTAMP` (Default: `CURRENT_TIMESTAMP`)

---

## ✨ Key Features

- **Interactive Multi-Page UI (`TaskFlow Studio`):** Switch seamlessly across `/`, `/audit`, `/urls`, and `/status` using a desktop command rail or mobile bottom navigation dock.
- **Real-Time Statistics & Filtering:** Live counters for **Total Tasks**, **Completed**, and **Pending**, paired with `All`, `Pending`, and `Completed` filter buttons.
- **Automated Database Audit Trail:** Every task creation (`POST`), completion/title update (`PUT`), and deletion (`DELETE`) writes a timestamped audit entry into `task_audit_log`.
- **JSON Endpoint Registry (`urls.json`):** Stores route definitions and exposes them via `/api/urls` and `/api/status`, with a built-in JSON viewer in the UI.

---

## 📁 Project Structure

```text
Python_Taskflow_Engine/
├── .gitignore              # Excludes .venv/, __pycache__/, and *.pyc
├── app.py                  # Flask server, PostgreSQL schema init, & REST APIs
├── urls.json               # JSON registry of application pages & API endpoints
├── requirement.txt         # Python dependency list
├── README.md               # Project documentation
└── static/
    └── index.html          # Responsive multi-page Bootstrap 5 + JS interface

Github Link: https://github.com/saswata35/Python_Based_Taskflow_Engine.git
HTTP Link: 
