"""
ChromaDB Local Setup — knowledge_base collection
--------------------------------------------------
Creates a persistent local ChromaDB with a "knowledge_base" collection
seeded with Ticketflow policy docs, FAQs, and resolved ticket summaries.

No API key needed — runs fully local.

Setup:
    pip install chromadb

Run:
    python chroma_setup.py
"""

import chromadb
from chromadb.utils import embedding_functions

# ─────────────────────────────────────────────
# 1. Client — persistent local storage
# ─────────────────────────────────────────────
# Data is saved to ./chroma_data/ folder on disk.
# Next time you run, it loads existing data automatically.

client = chromadb.PersistentClient(path="./chroma_data")
print("✅ ChromaDB client ready  →  ./chroma_data/")


# ─────────────────────────────────────────────
# 2. Embedding function
# ─────────────────────────────────────────────
# Uses sentence-transformers locally — no API key needed.
# Downloads ~90MB model on first run, cached after that.
# Swap for OpenAIEmbeddingFunction if you prefer.

embedding_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
    model_name="all-MiniLM-L6-v2"   # fast, small, good quality
)


# ─────────────────────────────────────────────
# 3. Create (or load) the knowledge_base collection
# ─────────────────────────────────────────────

collection = client.get_or_create_collection(
    name="knowledge_base",
    embedding_function=embedding_fn,
    metadata={"description": "Ticketflow policy docs, FAQs, resolved ticket summaries"},
)

print(f"✅ Collection ready: '{collection.name}'")


# ─────────────────────────────────────────────
# 4. Seed documents
# ─────────────────────────────────────────────
# Each document needs: id (unique), document (text), metadata (dict)
# Chroma auto-generates the embedding via embedding_fn above.

documents = [

    # ── Billing policies ──────────────────────
    {
        "id":       "policy-billing-001",
        "text":     "Customers can request a full refund within 30 days of purchase. "
                    "Refunds are processed within 5-7 business days to the original payment method. "
                    "For annual subscriptions, a pro-rated refund is issued for unused months.",
        "metadata": {"category": "billing", "type": "policy", "source": "billing-policy-v2"},
    },
    {
        "id":       "policy-billing-002",
        "text":     "Invoice discrepancies must be reported within 60 days of the invoice date. "
                    "To dispute a charge, contact billing with your order number and the incorrect amount. "
                    "Credits are applied to the next billing cycle if a discrepancy is confirmed.",
        "metadata": {"category": "billing", "type": "policy", "source": "billing-policy-v2"},
    },

    # ── Tech support ──────────────────────────
    {
        "id":       "policy-tech-001",
        "text":     "API rate limits are 1000 requests per minute for standard tier, "
                    "5000 for premium, and unlimited for enterprise customers. "
                    "Rate limit errors return HTTP 429. Use exponential backoff for retries.",
        "metadata": {"category": "tech", "type": "policy", "source": "api-docs-v3"},
    },
    {
        "id":       "policy-tech-002",
        "text":     "Webhook failures are retried up to 5 times with exponential backoff. "
                    "If all retries fail, the webhook is marked as failed and an alert is sent. "
                    "You can replay failed webhooks from the developer dashboard.",
        "metadata": {"category": "tech", "type": "policy", "source": "api-docs-v3"},
    },

    # ── SLA policies ─────────────────────────
    {
        "id":       "policy-sla-001",
        "text":     "SLA response times by priority: urgent = 4 hours, high = 8 hours, "
                    "medium = 24 hours, low = 72 hours. "
                    "Enterprise customers get 2x faster response times across all priorities. "
                    "SLA breaches trigger automatic escalation to a senior agent.",
        "metadata": {"category": "policy", "type": "sla", "source": "sla-policy-v1"},
    },
    {
        "id":       "policy-sla-002",
        "text":     "Planned maintenance windows are every Sunday 2-4am UTC. "
                    "Emergency maintenance notifications are sent at least 30 minutes in advance. "
                    "SLA timers are paused during approved maintenance windows.",
        "metadata": {"category": "policy", "type": "sla", "source": "sla-policy-v1"},
    },

    # ── Resolved ticket summaries ─────────────
    {
        "id":       "resolved-001",
        "text":     "Customer was charged twice for the same order due to a payment gateway timeout. "
                    "Resolution: duplicate charge identified in payment logs, refund issued within 24 hours. "
                    "Root cause: payment provider retry bug, now fixed.",
        "metadata": {"category": "billing", "type": "resolved_ticket", "source": "TKT-2024-088"},
    },
    {
        "id":       "resolved-002",
        "text":     "Webhook endpoint returning 500 errors for all POST requests after a deployment. "
                    "Resolution: a missing environment variable caused null pointer in webhook handler. "
                    "Fix: re-deploy with correct env vars. All queued webhooks replayed successfully.",
        "metadata": {"category": "tech", "type": "resolved_ticket", "source": "TKT-2024-112"},
    },

    # ── FAQs ─────────────────────────────────
    {
        "id":       "faq-001",
        "text":     "How do I cancel my subscription? "
                    "You can cancel anytime from Account Settings → Subscription → Cancel Plan. "
                    "Your access continues until the end of the current billing period. "
                    "No cancellation fees apply.",
        "metadata": {"category": "policy", "type": "faq", "source": "help-center"},
    },
    {
        "id":       "faq-002",
        "text":     "How do I upgrade from standard to premium? "
                    "Go to Account Settings → Plan → Upgrade. "
                    "You are charged the pro-rated difference immediately. "
                    "Premium features are available instantly after upgrade.",
        "metadata": {"category": "billing", "type": "faq", "source": "help-center"},
    },
]

# Add only documents not already in the collection
existing_ids = set(collection.get()["ids"])
new_docs = [d for d in documents if d["id"] not in existing_ids]

if new_docs:
    collection.add(
        ids       = [d["id"]   for d in new_docs],
        documents = [d["text"] for d in new_docs],
        metadatas = [d["metadata"] for d in new_docs],
    )
    print(f"✅ Added {len(new_docs)} documents to knowledge_base")
else:
    print(f"✅ All documents already present — skipping insert")

print(f"   Total documents in collection: {collection.count()}")


# ─────────────────────────────────────────────
# 5. Test queries
# ─────────────────────────────────────────────

print("\n── Semantic Search Tests ──")

test_queries = [
    ("I was charged twice for my order",          "billing"),
    ("webhook keeps returning 500 errors",         "tech"),
    ("how long until I get a response?",           "sla"),
    ("can I get my money back?",                   "billing"),
]

for query_text, expected_category in test_queries:
    results = collection.query(
        query_texts=[query_text],
        n_results=1,
        include=["documents", "metadatas", "distances"],
    )

    top_doc      = results["documents"][0][0]
    top_meta     = results["metadatas"][0][0]
    top_distance = results["distances"][0][0]
    similarity   = round(1 - top_distance, 3)   # cosine similarity (higher = more relevant)

    print(f"\n  Query    : '{query_text}'")
    print(f"  Match    : [{top_meta['category']}] {top_doc[:80]}...")
    print(f"  Score    : {similarity}  ({'✅' if top_meta['category'] == expected_category else '⚠️ '} expected {expected_category})")


# ─────────────────────────────────────────────
# 6. Filtered query example
# ─────────────────────────────────────────────

print("\n── Filtered Query (billing docs only) ──")
billing_results = collection.query(
    query_texts=["payment problem"],
    n_results=3,
    where={"category": "billing"},       # metadata filter
    include=["documents", "metadatas"],
)

for doc, meta in zip(billing_results["documents"][0], billing_results["metadatas"][0]):
    print(f"  [{meta['type']}] {doc[:80]}...")