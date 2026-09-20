"""Request-scoped progress for the local API worker."""

from contextlib import contextmanager
from contextvars import ContextVar
from threading import Lock
from time import monotonic

_request_id = ContextVar("omni_request_id", default=None)
_entries = {}
_lock = Lock()


def report_progress(agent, detail):
    request_id = _request_id.get()
    if not request_id:
        return
    with _lock:
        entry = _entries.setdefault(request_id, {"steps": []})
        steps = entry["steps"]
        if not steps or steps[-1] != agent:
            steps.append(agent)
        entry.update(agent=agent, detail=detail, status="processing", updated=monotonic())


def get_progress(request_id):
    with _lock:
        entry = _entries.get(request_id)
        return {**entry, "steps": list(entry["steps"])} if entry else {"status": "waiting"}


@contextmanager
def progress_scope(request_id):
    with _lock:
        expired = [key for key, entry in _entries.items() if monotonic() - entry["updated"] > 1800]
        for key in expired:
            _entries.pop(key, None)
        if len(_entries) >= 500:
            _entries.pop(next(iter(_entries)))
        _entries[request_id] = {"steps": [], "updated": monotonic()}
    token = _request_id.set(request_id)
    report_progress("Operations Agent", "Understanding your request")
    try:
        yield
    finally:
        with _lock:
            if request_id in _entries:
                _entries[request_id]["status"] = "finished"
        _request_id.reset(token)
