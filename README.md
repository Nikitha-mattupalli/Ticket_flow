# TICKET FLOW Agent Customer Support System

> A production-grade, multi-agent AI system that autonomously handles
> customer support tickets end-to-end using LangGraph, Groq, and a
> fully free-tier tech stack.

![Status](https://img.shields.io/badge/status-in--development-yellow)
![Python](https://img.shields.io/badge/python-3.11-blue)
![LangGraph](https://img.shields.io/badge/LangGraph-latest-purple)

---

## What It Does

DispatchAI replaces rigid support chatbots with a coordinated team of
autonomous AI agents. Each ticket is classified, routed, and resolved
by a specialist agent — with full observability, human-in-the-loop
controls, and zero paid LLM costs.

---

## Architecture
```
Incoming Ticket
      ↓
Supervisor Agent (classify → sentiment → priority → route)
      ↓
┌─────────────────────────────────────────┐
│  Billing   │  Technical  │  Returns  │  Escalation  │
│  Agent     │  Agent(RAG) │  Agent    │  Agent       │
└─────────────────────────────────────────┘
      ↓
Human-in-the-Loop (interrupt on high-stakes decisions)
      ↓
Resolution + LangSmith Trace
```

---

## Agent Roles

| Agent | Responsibility | Tools |
|-------|---------------|-------|
| Supervisor | Classify, sentiment score, route | Groq LLM |
| Billing | Invoices, refunds, confirmations | Supabase, Stripe, Resend |
| Technical | Diagnose issues, KB search | ChromaDB RAG, Jira mock |
| Returns | Eligibility, labels, store credit | Supabase, ShipStation mock |
| Escalation | Summarise, alert, escalate | Slack, Zendesk mock |

---

## Tech Stack (100% Free Tier)

| Layer | Technology |
|-------|-----------|
| LLM | Groq (Llama 3.1) |
| Agent Framework | LangGraph + LangChain |
| Observability | LangSmith |
| API | FastAPI + Celery |
| Vector DB | ChromaDB |
| Session Memory | Upstash Redis |
| Database | Supabase (PostgreSQL) |
| Email | Resend |
| Payments | Stripe test mode |
| Alerts | Slack API |
| Deployment | Railway + Docker |
| UI | Streamlit |

---

## Project Structure
```
DispatchAI/
├── agents/       # Supervisor + 4 specialist agents
├── tools/        # All LangChain tool definitions
├── memory/       # Redis session + ChromaDB vector store
├── api/          # FastAPI routes + Celery tasks
├── workflows/    # LangGraph state graph
├── tests/        # Pytest test suite
├── docs/         # Architecture diagrams
└── docker/       # Docker + docker-compose
```

---

## Getting Started

### Prerequisites
- Python 3.11
- Docker Desktop

### Installation
```bash
git clone https://github.com/yourusername/dispatchai.git
cd dispatchai
python -m venv ticket_flow
ticket_flow\Scripts\activate       # Windows
pip install -r requirements.txt
cp .env.example .env               # Fill in your API keys
```

### Run Locally
```bash
# coming soon — Phase 5
```

---

## Roadmap

- [x] Phase 0 — Environment & Foundations
- [ ] Phase 1 — Core Infrastructure
- [ ] Phase 2 — Supervisor Agent
- [ ] Phase 3 — Specialist Agents
- [ ] Phase 4 — Human-in-the-Loop
- [ ] Phase 5 — Observability & Deployment
- [ ] Phase 6 — Frontend & Polish

---

## Demo

> Coming in Week 15 — Streamlit dashboard + screen recording

---

## Author

Built by [Your Name] as a portfolio project demonstrating
production-grade agentic AI engineering.

- LinkedIn: your-linkedin
- GitHub: your-github