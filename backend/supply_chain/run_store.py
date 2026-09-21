"""Persist procurement decisions alongside the ERP purchase orders."""

import json
from contextlib import closing
from datetime import datetime, timezone

from database.supply_chain.sqlite_db.db import get_erp_db_connection


def _ensure_table(conn):
    conn.execute("""CREATE TABLE IF NOT EXISTS procurement_runs (
        run_id TEXT PRIMARY KEY, po_id INTEGER, status TEXT NOT NULL,
        state_json TEXT NOT NULL, updated_at TEXT NOT NULL
    )""")


def save_run(run_id, state):
    with closing(get_erp_db_connection()) as conn, conn:
        _ensure_table(conn)
        conn.execute("""INSERT INTO procurement_runs VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(run_id) DO UPDATE SET po_id=excluded.po_id,
            status=excluded.status, state_json=excluded.state_json, updated_at=excluded.updated_at""",
            (run_id, (state.get("po") or {}).get("po_id"), state.get("status", "unknown"),
             json.dumps(state), datetime.now(timezone.utc).isoformat()))


def load_run(run_id=None, po_id=None):
    with closing(get_erp_db_connection()) as conn:
        if not conn.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='procurement_runs'").fetchone():
            return None
        if run_id is not None:
            row = conn.execute("SELECT * FROM procurement_runs WHERE run_id=?", (run_id,)).fetchone()
        else:
            row = conn.execute("SELECT * FROM procurement_runs WHERE po_id=? ORDER BY updated_at DESC LIMIT 1", (po_id,)).fetchone()
        return {**json.loads(row["state_json"]), "run_id": row["run_id"], "status": row["status"]} if row else None


def claim_approval(run_id):
    # Claim in SQLite before awaiting any agent, including across API workers.
    with closing(get_erp_db_connection()) as conn, conn:
        updated = conn.execute("""UPDATE procurement_runs SET status='approving'
            WHERE run_id=? AND status='awaiting_approval'
            AND EXISTS (SELECT 1 FROM purchase_orders po WHERE po.po_id=procurement_runs.po_id
                        AND po.status IN ('draft', 'pending_approval'))""", (run_id,))
        return updated.rowcount == 1


def reject_run(run_id):
    with closing(get_erp_db_connection()) as conn, conn:
        conn.execute("BEGIN IMMEDIATE")
        row = conn.execute("SELECT * FROM procurement_runs WHERE run_id=?", (run_id,)).fetchone()
        if not row:
            return {"error": "Purchase-order run was not found."}
        state = json.loads(row["state_json"])
        if row["status"] == "rejected":
            return {**state, "run_id": run_id, "status": "rejected"}
        if row["status"] != "awaiting_approval":
            return {"error": "This order is no longer awaiting approval. Refresh its status."}
        updated = conn.execute("""UPDATE purchase_orders SET status='rejected'
            WHERE po_id=? AND status IN ('draft', 'pending_approval')""", (row["po_id"],))
        if updated.rowcount != 1:
            return {"error": "The purchase order has already changed. Refresh its status."}
        state.update(status="rejected", po={**(state.get("po") or {}), "status": "rejected"})
        conn.execute("UPDATE procurement_runs SET status='rejected', state_json=?, updated_at=? WHERE run_id=?",
                     (json.dumps(state), datetime.now(timezone.utc).isoformat(), run_id))
        return {**state, "run_id": run_id}
