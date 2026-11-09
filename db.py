
import sqlite3
import json
from pathlib import Path
from uuid import uuid4
from datetime import datetime, timezone

DB_PATH = Path(__file__).resolve().parent / "agent_eval.db"


def save_run(results, model_name):
    run_id = str(uuid4())
    created_at = datetime.now(timezone.utc).isoformat()

    conn = sqlite3.connect(DB_PATH)

    try:
        with conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS real_agent_results (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    run_id TEXT NOT NULL,
                    model_name TEXT NOT NULL,
                    test_case_id TEXT NOT NULL,
                    status TEXT NOT NULL,
                    reason TEXT,
                    latency_ms REAL,
                    tool_calls_json TEXT,
                    created_at TEXT NOT NULL
                )
            """)

            data = []

            for item in results:
                data.append((
                    run_id,
                    model_name,
                    item["id"],
                    item["status"],
                    item["reason"],
                    item["latency_ms"],
                    json.dumps(
                        item["tool_calls"],
                        ensure_ascii=False
                    ),
                    created_at
                ))

            conn.executemany("""
                INSERT INTO real_agent_results
                (run_id, model_name, test_case_id,
                 status, reason, latency_ms,
                 tool_calls_json, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, data)

    finally:
        conn.close()

    return run_id


def get_run_results(run_id):
    conn = sqlite3.connect(DB_PATH)

    try:
        rows = conn.execute("""
            SELECT test_case_id, status, reason, latency_ms
            FROM real_agent_results
            WHERE run_id = ?
            ORDER BY id
        """, (run_id,)).fetchall()

        return rows

    finally:
        conn.close()
