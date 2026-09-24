"""Read-only service checks. Never seed data or send a test email."""

import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path


def system_readiness():
    checks = []
    try:
        import pymongo
        from database.connection import db

        with pymongo.timeout(4):
            db.command("ping")
            counts = {name: db[name].count_documents({}) for name in (
                "products", "inventory", "bom", "production_lines", "demand_history",
            )}
        missing = [name for name, count in counts.items() if not count]
        checks.append({
            "name": "Factory database", "source": "MongoDB",
            "status": "needs_attention" if missing else "ready",
            "message": f"Empty collections: {', '.join(missing)}." if missing else "Connected. Factory records are available.",
            "counts": counts,
        })
    except Exception:
        checks.append({"name": "Factory database", "source": "MongoDB", "status": "unavailable",
                       "message": "Cannot read factory records. Check the database connection and network access."})

    db_dir = Path(__file__).resolve().parent.parent / "database" / "supply_chain" / "sqlite_db"
    for label, filename, table in (
        ("Supplier records", "mock-erp.db", "suppliers"),
        ("Shipment records", "mock-tms.db", "shipments"),
    ):
        try:
            conn = sqlite3.connect(f"{(db_dir / filename).as_uri()}?mode=ro", uri=True)
            try:
                count = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            finally:
                conn.close()
            checks.append({"name": label, "source": "Local ERP / TMS", "status": "ready" if count or table == "shipments" else "needs_attention",
                           "message": f"{count} records available."})
        except (sqlite3.Error, OSError):
            checks.append({"name": label, "source": "Local ERP / TMS", "status": "unavailable",
                           "message": "Local records are unavailable. Check the supply-chain database setup."})

    knowledge_dir = Path(__file__).resolve().parent.parent / "knowledge"
    for label, store, collection in (
        ("Production SOP retrieval", knowledge_dir / "chroma_store" / "chroma.sqlite3", "production_sops"),
        ("Market retrieval", knowledge_dir / "chroma_store" / "chroma.sqlite3", "market_context"),
        ("Supplier contract retrieval", knowledge_dir / "supply_chain" / "rag" / "chroma_store" / "chroma.sqlite3", "supplier_contracts"),
    ):
        try:
            conn = sqlite3.connect(f"{store.as_uri()}?mode=ro", uri=True)
            try:
                exists = conn.execute("SELECT 1 FROM collections WHERE name = ?", (collection,)).fetchone()
            finally:
                conn.close()
            checks.append({"name": label, "source": "ChromaDB", "status": "ready" if exists else "needs_attention",
                           "message": "Collection available." if exists else "Collection missing. Rebuild the knowledge index."})
        except (sqlite3.Error, OSError):
            checks.append({"name": label, "source": "ChromaDB", "status": "unavailable",
                           "message": "Vector store unavailable. Rebuild the knowledge index."})

    llm_configured = bool(os.getenv("GROQ_API_KEY", "").strip())
    checks.append({"name": "Language model", "status": "configured" if llm_configured else "needs_attention",
                   "message": "Credentials configured; provider connectivity has not been tested." if llm_configured else "Language-model credentials are missing."})
    from backend.supply_chain.email_service import email_configuration_status
    checks.append({"name": "Supplier email", **email_configuration_status()})
    return {
        "status": "needs_attention" if any(check["status"] in {"unavailable", "needs_attention"} for check in checks) else "ready",
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "checks": checks,
    }
