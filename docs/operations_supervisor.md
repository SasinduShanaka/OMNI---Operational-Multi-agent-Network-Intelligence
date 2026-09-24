# Operations supervisor

`agents/operations/operations_agent.py` owns the chat entry point, intent
parsing, entity extraction and prompt-injection checks. Its active graph is
built by `agents/operations/operations_workflow.py`:

```text
START -> understand_goal -> supervisor
                         -> inventory ---------|
                         -> forecast ----------|
                         -> production --------|-> supervisor
                         -> supply_chain ------|
                         -> knowledge ---------|
                         -> report ------------|
                         -> reviewer ----------|
                         -> ask_user -> synthesize -> END
                         -> synthesize -> END
```

The supervisor stores a structured goal, selected plan steps, specialist
evidence, short operational rationales and a step count. It reviews the
blackboard after every specialist call and selects another action or finishes.
The bound is eight supervisor cycles; a limit returns a partial answer.
Simple stock questions call Inventory alone. For an order-feasibility question,
Production supplies capacity and BOM facts. If it reports shortages, the
Operations supervisor asks the Supply Chain domain for compliant sourcing
options, then calls Production again with the supplier lead time. Forecast and
knowledge calls occur only when the request asks for those perspectives.

Specialists now return validated `AgentResult` objects with facts, risks,
assumptions, confidence levels and optional `AgentRequest`s. Operations owns
the queue of requests and checks each target against its allowed capabilities.
For example, Production can request read-only Supply Chain lead-time evidence;
Supply Chain can request Production to recheck the remaining schedule. The
specialists do not call each other's sensitive tools. Short task, question and
challenge messages are kept on the shared blackboard. The bounded reviewer
checks the final evidence for missing facts and contradictions and can request
one Production reassessment; it stops after two review rounds. It has no tools.

The tool-free Conversation Manager turns the verified conclusion into a
cause–impact–next-step answer. It reads the result and does not change numeric
facts, approval state or specialist decisions. A model may choose among the
supervisor's allowed evidence actions when several are useful; the fallback is
deterministic, and model output cannot authorize a write.

The API stores short-term `ConversationContext` per authenticated user and
session for 15 minutes. It retains the active order, verified blocking materials,
unanswered questions, recent verdicts, pending approval references and limited
sourcing evidence. A follow-up such as “order the insufficient materials for
this order” uses the saved shortage quantity and material code to enter the
existing supplier-selection flow. Supplier selection drafts a PO only after the
user picks a server-listed supplier; approval still requires a manager. A new
business topic clears old shortage references. Supplier lead times may be
reused for the same material set for five minutes; quantities and cost estimates
are recomputed or omitted. A quantity-only or date-only follow-up reuses the
missing product/date context. Purchase and approval intent is never inherited
from an earlier turn. `AgentMemoryStore` separately retains bounded historical
domain observations for 24 hours; these are context, never live stock or ERP
facts. No credentials, hidden prompts or private reasoning are stored.

Factory calculations remain behind Factory Operations MCP. Supply Chain
retains its existing chat supervisor and persisted procurement pipeline.
`analyze_shortages` is its read-only sourcing entry point. Feasibility and
supplier research do not draft POs. An explicit order request may enter the
existing draft pipeline; manager approval remains in the authenticated HTTP
workflow. Both chat and Supply Chain approval endpoints require the authenticated
manager role, even though ordinary write access can include other users. ERP
accepts only atomic `draft`/`pending_approval` to `approved`
transitions, and TMS checks ERP approval before shipment booking.

Knowledge routing is domain-aware: the indexed production SOP and market
corpora can provide contextual passages. Inventory, forecasting and general
policy corpora are explicitly marked unavailable until indexed; market notes
are never presented as inventory policy. Supplier contract compliance remains
inside the Supply Chain sourcing process.

The response preserves `answer`, `workflow`, `graph`, `delegated_to`, `result`,
`procurement` and `requires_approval` where applicable. It adds `goal`,
`completed_steps`, `plan_summary`, `evidence_sources` and structured `evidence`.
It also returns optional confidence level, assumptions, risks, agent messages,
review status, contradictions and bounded operational events.
These contain operational facts and brief reasons, not private model reasoning.

Current limits: the optional model selects only among bounded evidence actions;
the deterministic planner still recognizes specific request types. Conditional
capacity assumes production begins after the longest verified supplier lead
time and is an estimate, not a reservation or a full reschedule. Supplier cost
is a planning estimate. The legacy graph helpers remain in `operations_agent`
for compatibility but are not the active graph. Session and domain memory are
process-local; they do not survive a restart or coordinate across server
replicas. The reviewer checks defined business invariants, not every possible
claim. The Conversation Manager currently uses grounded templates rather than
a separate text-generation model. Direct local ERP MCP access is a trusted
backend boundary; authenticated manager authorization is enforced at HTTP
approval entry points, so the MCP server must not be exposed as a public API.
