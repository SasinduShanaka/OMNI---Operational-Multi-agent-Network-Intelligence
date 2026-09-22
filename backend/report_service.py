"""MongoDB report snapshots and restart-safe daily/monthly schedule execution."""
from datetime import datetime, timedelta, timezone
from functools import lru_cache
import logging
import math
import os
from threading import Event, Thread
from uuid import uuid4

from bson import ObjectId
from pymongo import MongoClient, ReturnDocument, timeout

from agents.reports.report_agent import utcnow
from backend.mcp.factory_operations.client import generate_management_report as build_report

logger = logging.getLogger(__name__)
COLOMBO = timezone(timedelta(hours=5, minutes=30), name="Asia/Colombo")


@lru_cache(maxsize=1)
def get_db():
    uri = os.getenv("MONGO_URI")
    if not uri:
        raise RuntimeError("MONGO_URI is required for report history.")
    client = MongoClient(uri, serverSelectionTimeoutMS=5000, connectTimeoutMS=5000,
                         socketTimeoutMS=15000, tz_aware=True)
    db = client[os.getenv("MONGO_DB_NAME", "OMNI_DB")]
    try:
        db.reports.create_index([("generated_at", -1)])
        db.report_schedules.create_index([("enabled", 1), ("next_run", 1)])
    except Exception:
        client.close()
        raise
    return db


def serializable(value):
    if isinstance(value, dict):
        return {key: serializable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [serializable(item) for item in value]
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, ObjectId):
        return str(value)
    if isinstance(value, float) and not math.isfinite(value):
        return None
    return value


def generate_report(scope, report_id=None, schedule_id=None, scheduled_for=None):
    db = get_db()
    report_id = report_id or str(uuid4())
    existing = db.reports.find_one({"_id": report_id})
    if existing:
        return serializable(existing)
    # Bound Mongo operations across collection/analysis below the schedule lease.
    with timeout(120):
        report = serializable(build_report(scope))
    report.update({"_id": report_id, "schedule_id": schedule_id,
                   "scheduled_for": serializable(scheduled_for)})
    # A retried schedule occurrence can never overwrite an earlier snapshot.
    db.reports.update_one({"_id": report_id}, {"$setOnInsert": report}, upsert=True)
    return serializable(db.reports.find_one({"_id": report_id}))


def list_reports(limit=20, skip=0):
    db = get_db()
    projection = {"evidence": 0, "sections": 0, "findings": 0, "recommendations": 0}
    rows = list(db.reports.find({}, projection).sort("generated_at", -1).skip(skip).limit(limit))
    return {"reports": serializable(rows), "total": db.reports.count_documents({})}


def get_report(report_id):
    return serializable(get_db().reports.find_one({"_id": report_id}, {"evidence": 0}))


def next_occurrence(schedule, after):
    """First occurrence strictly after `after`, in fixed Sri Lanka time."""
    local = after.astimezone(COLOMBO)
    hour, minute = map(int, schedule["time"].split(":"))
    candidate = local.replace(hour=hour, minute=minute, second=0, microsecond=0)
    if schedule["frequency"] == "daily":
        if candidate <= local:
            candidate += timedelta(days=1)
    else:
        candidate = candidate.replace(day=schedule.get("day_of_month", 1))
        if candidate <= local:
            month = candidate.month % 12 + 1
            candidate = candidate.replace(year=candidate.year + (candidate.month == 12), month=month)
    return candidate.astimezone(timezone.utc)


def create_schedule(config):
    now = utcnow()
    schedule = {**config, "_id": str(uuid4()), "enabled": True,
                "timezone": "Asia/Colombo", "created_at": now,
                "next_run": next_occurrence(config, now), "last_status": "not_run"}
    get_db().report_schedules.insert_one(schedule)
    return serializable(schedule)


def list_schedules():
    return serializable(list(get_db().report_schedules.find({}, {"lease_token": 0}).sort("created_at", -1)))


def set_schedule_enabled(schedule_id, enabled):
    db = get_db()
    schedule = db.report_schedules.find_one({"_id": schedule_id})
    if not schedule:
        return None
    patch = {"enabled": enabled}
    if enabled and not schedule["enabled"]:
        patch["next_run"] = next_occurrence(schedule, utcnow())
    db.report_schedules.update_one({"_id": schedule_id}, {"$set": patch})
    return serializable(db.report_schedules.find_one({"_id": schedule_id}, {"lease_token": 0}))


def run_due_schedule():
    """Claim one due run atomically; duplicate workers share the same occurrence ID.

    A crash leaves next_run unchanged. After the five-minute lease, another worker
    resumes the same occurrence. Missed intervals are coalesced into one current
    snapshot; no fabricated historical backfill is generated.
    """
    db, now, token = get_db(), utcnow(), str(uuid4())
    schedule = db.report_schedules.find_one_and_update(
        {"enabled": True, "next_run": {"$lte": now},
         "$or": [{"lease_until": {"$exists": False}}, {"lease_until": {"$lte": now}}]},
        {"$set": {"lease_until": now + timedelta(minutes=5), "lease_token": token}},
        sort=[("next_run", 1)], return_document=ReturnDocument.AFTER,
    )
    if not schedule:
        return False
    try:
        report_id = f"{schedule['_id']}--{schedule['next_run'].isoformat()}"
        report = generate_report(schedule["scope"], report_id, schedule["_id"], schedule["next_run"])
        patch = {"last_status": report["status"], "last_report_id": report_id,
                 "last_error": None, "last_run": utcnow(),
                 "next_run": next_occurrence(schedule, utcnow())}
    except Exception:
        logger.exception("Scheduled report could not be saved")
        # Keep this occurrence pending. Retry after the lease; persist the failure
        # so the dashboard distinguishes storage failures from source failures.
        patch = {"last_status": "retrying", "last_error": "Report could not be saved; retrying after five minutes.", "last_run": utcnow()}
        db.report_schedules.update_one({"_id": schedule["_id"], "lease_token": token}, {"$set": patch})
        return True
    db.report_schedules.update_one({"_id": schedule["_id"], "lease_token": token},
                                   {"$set": patch, "$unset": {"lease_until": "", "lease_token": ""}})
    return True


def start_scheduler():
    stop = Event()

    def worker():
        while not stop.is_set():
            try:
                worked = run_due_schedule()
            except Exception:
                logger.warning("Report scheduler cannot reach report storage; will retry.")
                worked = False
            stop.wait(1 if worked else 30)

    thread = Thread(target=worker, name="omni-report-scheduler", daemon=True)
    thread.start()
    return stop, thread
