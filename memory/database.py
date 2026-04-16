import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "logs" / "calls.db"


def _connect() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def initialize_db() -> None:
    with _connect() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS calls (
                id               INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp        TEXT    NOT NULL,
                prospect_name    TEXT    NOT NULL,
                persona          TEXT    NOT NULL,
                script_version   INTEGER NOT NULL,
                outcome          TEXT    NOT NULL,
                turn_count       INTEGER NOT NULL,
                objections_raised TEXT,
                call_quality     TEXT,
                improvement_note TEXT,
                conversation     TEXT    NOT NULL
            )
        """)


def save_call(result: dict, analysis: dict) -> int:
    timestamp = datetime.now(timezone.utc).isoformat()

    try:
        with _connect() as conn:
            cursor = conn.execute(
                """
                INSERT INTO calls (
                    timestamp, prospect_name, persona, script_version,
                    outcome, turn_count, objections_raised,
                    call_quality, improvement_note, conversation
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    timestamp,
                    result["prospect_name"],
                    result["persona"],
                    result["script_version"],
                    result["outcome"],
                    result["turn_count"],
                    json.dumps(analysis.get("objections_raised", [])),
                    analysis.get("call_quality"),
                    analysis.get("improvement_note"),
                    json.dumps(result["conversation"]),
                ),
            )
            return cursor.lastrowid
    except Exception as e:
        print(f"  [DB write error: {e} — call result not saved]")
        return -1


def fetch_recent_calls(limit: int = 10) -> list[dict]:
    with _connect() as conn:
        rows = conn.execute(
            "SELECT * FROM calls ORDER BY id DESC LIMIT ?", (limit,)
        ).fetchall()

    calls = []
    for row in rows:
        record = dict(row)
        record["objections_raised"] = json.loads(record["objections_raised"] or "[]")
        record["conversation"] = json.loads(record["conversation"])
        calls.append(record)
    return calls


def fetch_calls_for_version(script_version: int) -> list[dict]:
    with _connect() as conn:
        rows = conn.execute(
            "SELECT * FROM calls WHERE script_version = ? ORDER BY id ASC",
            (script_version,)
        ).fetchall()

    calls = []
    for row in rows:
        record = dict(row)
        record["objections_raised"] = json.loads(record["objections_raised"] or "[]")
        record["conversation"] = json.loads(record["conversation"])
        calls.append(record)
    return calls


def get_conversion_rate(script_version: int | None = None) -> dict:
    with _connect() as conn:
        if script_version is not None:
            rows = conn.execute(
                "SELECT outcome FROM calls WHERE script_version = ?",
                (script_version,)
            ).fetchall()
        else:
            rows = conn.execute("SELECT outcome FROM calls").fetchall()

    total = len(rows)
    if total == 0:
        return {"total": 0, "converted": 0, "rejected": 0, "incomplete": 0, "rate": 0.0}

    outcomes = [r["outcome"] for r in rows]
    converted = outcomes.count("converted")
    rejected = outcomes.count("rejected")
    incomplete = outcomes.count("incomplete")

    return {
        "total": total,
        "converted": converted,
        "rejected": rejected,
        "incomplete": incomplete,
        "rate": round(converted / total * 100, 1),
    }
