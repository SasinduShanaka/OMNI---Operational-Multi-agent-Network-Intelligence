"""Validated messages exchanged through the Operations supervisor blackboard."""

from typing import Literal

from pydantic import BaseModel, Field


AgentName = Literal["operations", "inventory", "forecast", "production", "supply_chain", "knowledge", "report", "reviewer"]


class AgentMessage(BaseModel):
    sender: AgentName
    recipient: AgentName
    message_type: Literal["task", "question", "evidence", "warning", "challenge", "response"]
    content: str = Field(min_length=1, max_length=500)
    facts: dict = Field(default_factory=dict)
    confidence: float | None = Field(default=None, ge=0, le=1)
    references: list[str] = Field(default_factory=list)
    requires_response: bool = False


class AgentRequest(BaseModel):
    target_agent: AgentName
    task: str = Field(min_length=1, max_length=500)
    reason: str = Field(min_length=1, max_length=500)
    required_facts: list[str] = Field(default_factory=list)


class AgentResult(BaseModel):
    agent: AgentName
    status: Literal["success", "partial", "needs_collaboration", "needs_user_input", "error"]
    conclusion: str | None = None
    facts: dict = Field(default_factory=dict)
    risks: list[str] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)
    confidence: float | None = Field(default=None, ge=0, le=1)
    confidence_level: Literal["high", "medium", "low"] | None = None
    requests: list[AgentRequest] = Field(default_factory=list)
    messages: list[AgentMessage] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)


class ReviewResult(BaseModel):
    valid: bool
    issues: list[str] = Field(default_factory=list)
    missing_checks: list[str] = Field(default_factory=list)
    contradictions: list[str] = Field(default_factory=list)
    recommended_actions: list[AgentRequest] = Field(default_factory=list)
