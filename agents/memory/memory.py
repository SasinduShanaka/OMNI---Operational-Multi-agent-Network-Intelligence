"""Lightweight, bounded domain observations; not a source of live facts."""

from datetime import datetime, timedelta, timezone
from threading import Lock
import re


class AgentMemoryStore:
    def __init__(self, max_per_agent: int = 50, ttl_hours: int = 24):
        self.max_per_agent = max_per_agent
        self.ttl = timedelta(hours=ttl_hours)
        self._items: dict[str, list[dict]] = {}
        self._lock = Lock()

    def save_observation(self, agent: str, observation: dict) -> None:
        """Keep only a short operational finding, never prompts or credentials."""
        if agent not in {"production", "forecast", "supply_chain", "inventory"}:
            raise ValueError("Unsupported domain memory agent.")
        topic = str(observation.get("topic") or "")[:80]
        finding = str(observation.get("finding") or "")[:240]
        if not topic or not finding:
            raise ValueError("A topic and finding are required.")
        if re.search(r"\b(?:api\s*key|password|secret|access\s*token|system\s*prompt|hidden\s*instructions?)\b",
                     topic + " " + finding, re.IGNORECASE):
            raise ValueError("Sensitive content cannot be stored in domain memory.")
        row = {"topic": topic, "finding": finding,
               "source": str(observation.get("source") or "verified_tool")[:80],
               "captured_at": datetime.now(timezone.utc)}
        with self._lock:
            current = [item for item in self._items.get(agent, [])
                       if datetime.now(timezone.utc) - item["captured_at"] <= self.ttl]
            self._items[agent] = [*current, row][-self.max_per_agent:]

    def get_relevant(self, agent: str, query: str) -> list[dict]:
        """Return historical context only; callers must still use live MCP data."""
        with self._lock:
            current = [item.copy() for item in self._items.get(agent, [])
                       if datetime.now(timezone.utc) - item["captured_at"] <= self.ttl]
        if query:
            key = query.lower()
            current = [item for item in current if key in item["topic"].lower() or key in item["finding"].lower()]
        return current


domain_memory = AgentMemoryStore()


def remember_domain(agent: str, observation: dict) -> bool:
    """Domain memory is optional; a rejected observation cannot fail analysis."""
    try:
        domain_memory.save_observation(agent, observation)
        return True
    except ValueError:
        return False
