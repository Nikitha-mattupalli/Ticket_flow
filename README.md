# Ticket Flow

Ticket Flow is a portfolio-ready multi-agent customer-support workflow built
with LangGraph, LangChain, Groq, Pydantic, Chroma, Supabase, Stripe test mode,
and Resend.

The demo-ready v1 focuses on two complete specialist paths:

- Billing: RAG and payment investigation, typed refund proposal, optional
  human approval, Stripe execution, and customer confirmation.
- Technical: RAG-grounded classification and troubleshooting.

Returns and escalation are explicit terminal placeholders for later versions.

## Architecture

```text
Incoming Ticket
      |
      v
Supervisor (classify, prioritize, summarize, route)
      |
      +-- billing --> Billing RAG + read-only investigation
      |                    |
      |                    +-- no refund ----------------------> END
      |                    |
      |                    +-- approval required --> INTERRUPT
      |                    |                           |
      |                    |                 reject --> END
      |                    |                 approve --+
      |                    |
      |                    +-- no approval required ---+
      |                                                |
      |                                                v
      |                                      Stripe refund execution
      |                                                |
      |                                      success --> confirmation --> END
      |                                      failure ------------------> END
      |
      +-- technical --> Technical RAG --> TechnicalResult --> END
      +-- returns --------------------------------------------> END (stub)
      +-- escalation -----------------------------------------> END (stub)
```

See [docs/architecture.md](docs/architecture.md) for node responsibilities and
state ownership.

## Design highlights

- The Supervisor routes tickets but never resolves them.
- Billing uses two LLM stages: a tool-calling investigation followed by a
  separate structured-output formatter. This avoids Groq tool/response-format
  conflicts.
- Stripe is never called before a required `interrupt()` completes.
- Workflow execution data lives in `GraphState`; `BillingResult` contains only
  the agent's decision and proposed action.
- Refund execution uses a stable Stripe idempotency key.
- Billing and Technical agents share the generic Chroma retrieval package.
- The graph is compiled with `InMemorySaver` and resumed with the same
  `thread_id`.

## Requirements

- Python 3.11 or 3.12 recommended
- A Groq API key for live agent calls
- Supabase, Stripe test-mode, and Resend credentials for live Billing execution

Python 3.14 currently produces a LangChain/Pydantic compatibility warning.

## Setup

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
```

Fill in `.env`. Keep `STRIPE_SECRET_KEY` in test mode (`sk_test_...`).

Build or rebuild the knowledge indexes:

```powershell
python -c "from retrieval.index_builder import build_index; build_index('billing')"
python -c "from retrieval.index_builder import build_index; build_index('technical')"
```

If the embedding model is already cached and the machine is offline:

```powershell
$env:HF_HUB_OFFLINE='1'
```

## Safe deterministic demo

This runs the real compiled LangGraph and its HITL interrupt/resume behavior,
while mocking Groq, Supabase, Stripe, and Resend. It creates no external side
effects.

```powershell
python scripts/demo_workflow.py --scenario all
```

Individual scenarios:

```powershell
python scripts/demo_workflow.py --scenario approval
python scripts/demo_workflow.py --scenario rejection
python scripts/demo_workflow.py --scenario no_approval
python scripts/demo_workflow.py --scenario technical
```

## Interactive live Billing demo

After configuring test credentials and verifying the sample IDs in `main.py`:

```powershell
python main.py
```

The initial invocation pauses for high-value refunds. The terminal collects the
reviewer's decision and resumes the same graph thread. This path can create a
Stripe test refund and send a real email through Resend.

## Tests

The focused suite uses `unittest`, so it does not require pytest:

```powershell
$env:HF_HUB_OFFLINE='1'
python -m unittest `
  tests.test_billing_workflow `
  tests.test_technical_agent `
  tests.test_demo_workflow -v
```

The older `tests/test_integration.py` exercises the separate FastAPI/Celery/
Supabase pipeline and requires those services to be running. It is not part of
the focused LangGraph v1 test command above.

## Repository map

```text
agents/
  supervisor/       routing decision
  billing/          investigation, schemas, approval, execution
  technical/        typed RAG-grounded troubleshooting
graph/              state, nodes, routing, workflow assembly
retrieval/          shared embeddings, splitting, Chroma retrieval
knowledge/          billing and technical Markdown sources
tools/              Supabase, Stripe, and Resend tools
scripts/            deterministic demo and data helpers
tests/              focused workflow and legacy integration tests
docs/               architecture notes
```

## Current v1 status

- [x] Supervisor routing
- [x] Two-stage Billing Agent
- [x] Billing RAG and verified invoice/payment lookup
- [x] Refund proposal and typed workflow state
- [x] HITL approval/rejection with checkpointing
- [x] Approved and no-approval refund execution routes
- [x] Confirmation and failure routes
- [x] Technical Agent with RAG and `TechnicalResult`
- [x] Deterministic four-scenario graph demo
- [x] Focused offline tests
- [ ] Persistent production checkpointer
- [ ] Implemented Returns and Escalation agents
- [ ] Deployment/UI polish
