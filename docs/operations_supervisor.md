# Operations supervisor

`agents/operations_agent.py` still parses requests and protects the chat
security boundary. Its active graph is built by `agents/operations_workflow.py`:

```text
START -> understand_goal -> supervisor
                         -> inventory ---------|
                         -> forecast ----------|
                         -> production --------|-> supervisor
                         -> supply_chain ------|
                         -> knowledge ---------|
                         -> report ------------|
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

Factory calculations remain behind Factory Operations MCP. Supply Chain
retains its existing chat supervisor and persisted procurement pipeline.
`analyze_shortages` is its read-only sourcing entry point. Feasibility and
supplier research do not draft POs. An explicit order request may enter the
existing draft pipeline; manager approval remains in the authenticated HTTP
workflow. ERP accepts only atomic `draft`/`pending_approval` to `approved`
transitions, and TMS checks ERP approval before shipment booking.

The response preserves `answer`, `workflow`, `graph`, `delegated_to`, `result`,
`procurement` and `requires_approval` where applicable. It adds `goal`,
`completed_steps`, `plan_summary`, `evidence_sources` and structured `evidence`.
These contain operational facts and brief reasons, not private model reasoning.

Current limits: the optional model selects only among bounded evidence actions;
the deterministic planner still recognizes specific request types. Conditional
capacity assumes production begins after the longest verified supplier lead
time and is an estimate, not a reservation or a full reschedule. Supplier cost
is a planning estimate. The legacy graph helpers remain in `operations_agent`
for compatibility but are not the active graph. Conversation context still
lives outside the supervisor state and is not persisted as long-term memory.
