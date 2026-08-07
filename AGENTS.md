# Ticket Flow — Development Context

## Project Goal

Ticket Flow is a multi-agent AI customer-support system built primarily
for AI Engineer portfolio/interview purposes.

Core stack:
- Python
- LangChain
- LangGraph
- Groq LLM
- Pydantic
- ChromaDB
- HuggingFace embeddings
- Supabase
- Stripe test mode
- Resend

The design should remain modular, production-oriented, and easy to
explain in AI Engineer interviews.

---

## Architecture

Incoming Ticket
    ↓
Supervisor Agent
    ↓
Conditional LangGraph routing
    ├── Billing Agent
    ├── Technical Agent
    ├── Returns stub
    └── Escalation stub

Billing flow:

Ticket
    ↓
Supervisor
    ↓
Billing Node
    ↓
Chroma RAG retrieval
    ↓
Billing tool-calling investigation
    ↓
BillingResult
    ↓
Refund proposal
    ↓
Human approval if required
    ↓
Refund execution
    ↓
Confirmation
    ↓
END

---

## Important Design Decisions

### Supervisor

The Supervisor does NOT resolve tickets.

Responsibilities:
- determine intent
- priority
- sentiment
- summarize ticket
- decide human requirement
- choose next agent

Supervisor structured output:
- IntentType
- PriorityLevel
- Sentiment
- SupervisorDecision

LangChain structured output is used.

---

## GraphState

GraphState is a Pydantic BaseModel.

Important fields include:

- ticket
- supervisor_decision
- billing_result
- technical_result (to be added)
- pending_refund
- approval_status
- approval_reviewer
- approval_comment
- refund_result
- workflow_status
- retry_count
- error_message

LangGraph graph.invoke() may return a dict, so use:

GraphState.model_validate(result)

when a Pydantic object is needed afterward.

---

## Billing Agent

Billing Agent uses a TWO-STAGE architecture because Groq tool calling
and structured response generation caused conflicts.

Stage 1:
Tool-calling investigation agent.

Stage 2:
Separate structured-output formatter producing BillingResult.

Do NOT combine tool calling and BillingResult response_format in the
same Groq request.

### Billing Tools

Implemented and independently tested:

1. fetch_invoice
   - Supabase
   - fetches invoice and associated payments

2. process_refund
   - Stripe test mode
   - uses Stripe PaymentIntent ID
   - Stripe IDs begin with pi_
   - amount is passed in smallest currency unit

3. send_confirmation
   - Resend
   - independently tested

---

## Billing RAG

Reusable retrieval package implemented:

retrieval/
- embeddings.py
- splitter.py
- vector_store.py
- index_builder.py
- retriever.py

Embedding model:
sentence-transformers/all-MiniLM-L6-v2

Vector DB:
Chroma

KnowledgeRetriever is instantiated:

billing_retriever = KnowledgeRetriever(
    domain="billing",
    top_k=3,
)

Then:

context = billing_retriever.retrieve(
    subject=ticket.subject,
    description=ticket.description,
)

Do NOT call instance methods directly on KnowledgeRetriever class.

Knowledge folders:

knowledge/
- billing/
- technical/
- returns/

Vector stores:

vector_stores/
- billing_db/
- technical_db/
- returns_db/

---

## Database

Supabase currently includes:
- customers
- orders
- tickets
- invoices
- payments
- refunds

Payments table contains:
- invoice_id
- customer_id
- stripe_payment_intent_id
- stripe_charge_id
- status
- amount
- currency
- payment_method
- timestamps

Refunds table stores refund lifecycle / approval data.

Database migrations were added for payments and refunds.

---

## Duplicate Payment Test

For a duplicate-charge test:

One invoice should have two different succeeded payment rows.

Both should:
- point to the same invoice_id
- point to the same customer_id
- normally have same amount/currency
- have different Stripe PaymentIntent IDs
- have different Stripe Charge IDs

Do not reuse the same pi_ ID.

---

## Billing Schemas

BillingResult describes AGENT DECISION.

Workflow execution state belongs in GraphState.

BillingResult contains:
- issue_category
- resolution_status
- confidence
- requires_human
- response_to_customer
- reasoning
- proposed_refund

RefundRequest contains:
- payment_id
- invoice_id
- customer_id
- payment_intent_id
- amount
- currency
- reason

ApprovalStatus:
- NOT_REQUIRED
- PENDING
- APPROVED
- REJECTED

GraphState contains:
- pending_refund
- approval_status
- approval_reviewer
- approval_comment
- refund_result

Do not put approval execution results back into BillingResult.

---

## Human-in-the-Loop — Current Day 3 Work

approval_node.py has been created.

refund_approval_node:

- reads state.pending_refund
- calls langgraph.types.interrupt()
- sends refund information for review
- on resume reads:
    approved
    reviewer
    comment
- updates approval_status
- updates workflow_status

Never call Stripe before interrupt().

The graph must be compiled with a checkpointer.

For local testing use InMemorySaver.

Every resumable invocation must use the same thread_id.

Initial call:

graph.invoke(initial_state, config=config)

Resume:

graph.invoke(
    Command(
        resume={
            "approved": True/False,
            "reviewer": "...",
            "comment": "..."
        }
    ),
    config=config
)

---

## Current Priority

Complete a stable demo-ready v1.

Do these tasks IN ORDER:

1. Stabilize Billing Agent tests.
2. Finish refund_execution_node.
3. Add route_after_billing.
4. Add route_after_approval.
5. Add approved/rejected branches.
6. Add confirmation node.
7. Test HITL end-to-end:
   - approval
   - rejection
   - no approval needed
8. Build Technical Agent using existing generic RAG.
9. Add TechnicalResult to GraphState.
10. Replace technical stub with real node.
11. Add focused tests.
12. Clean logging/configuration.
13. Update README + architecture diagram.
14. Create demo script.
15. Final repo cleanup.

---

## Technical Agent Scope

Keep Technical Agent small for v1.

Technical categories:
- login_issue
- password_reset
- network_connectivity
- service_outage
- api_timeout
- other

Use existing Technical knowledge base and Chroma retrieval.

For v1:
Ticket + Technical RAG Context
    ↓
Technical Agent
    ↓
TechnicalResult

Jira/status tools are optional future improvements.

---

## Coding Preferences

When helping:
- inspect existing code before replacing it
- preserve the current architecture
- make focused changes
- avoid overengineering
- explain architectural changes
- keep LangChain + LangGraph usage explicit
- use typed Pydantic schemas
- avoid duplicated agent/retrieval implementations
- use project-level config for constants
- prefer runnable/testable changes
- do not silently replace working components

Before making a large change, summarize:
1. what currently exists
2. what needs changing
3. which files will change

---

## Definition of Done for v1

A user can submit either:

### Billing ticket
Supervisor
→ Billing
→ RAG
→ verified payment investigation
→ refund proposal
→ HITL when required
→ approve/reject
→ refund execution
→ confirmation
→ final state

### Technical ticket
Supervisor
→ Technical
→ RAG
→ grounded troubleshooting
→ final TechnicalResult

Repository should contain:
- clean README
- setup instructions
- .env.example
- tests
- architecture diagram
- requirements
- demo script