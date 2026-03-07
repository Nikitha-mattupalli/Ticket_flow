"""
Embed Sample Articles into ChromaDB
-------------------------------------
Uses HuggingFace sentence-transformers (free, local, no API key).
Model: all-MiniLM-L6-v2  (~90MB, downloads once, cached forever)

Setup:
    pip install chromadb sentence-transformers

Run:
    python embed_articles.py
"""

import chromadb
from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction

# ─────────────────────────────────────────────
# 1. Client + embedding function
# ─────────────────────────────────────────────

client = chromadb.PersistentClient(path="./chroma_data")

embedding_fn = SentenceTransformerEmbeddingFunction(
    model_name="all-MiniLM-L6-v2"  # free, local, no API key needed
)

collection = client.get_or_create_collection(
    name="knowledge_base",
    embedding_function=embedding_fn,
)

print(f"✅ Collection '{collection.name}' ready")
print(f"   Documents before insert: {collection.count()}")


# ─────────────────────────────────────────────
# 2. Sample articles
# ─────────────────────────────────────────────

articles = [

    # ── Billing ───────────────────────────────
    {
        "id":    "article-billing-001",
        "title": "Understanding Your Invoice",
        "text": (
            "Your monthly invoice is generated on the first of each month. "
            "It includes a breakdown of your base subscription, any add-ons, "
            "and applicable taxes. If you believe there is an error on your invoice, "
            "you must raise a dispute within 60 days of the invoice date. "
            "To dispute a charge, navigate to Billing → Invoices → Dispute. "
            "Our billing team reviews disputes within 3 business days. "
            "If the dispute is resolved in your favour, a credit is applied "
            "to your next invoice automatically."
        ),
        "metadata": {
            "category": "billing",
            "type":     "article",
            "title":    "Understanding Your Invoice",
            "source":   "help-center",
        },
    },
    {
        "id":    "article-billing-002",
        "title": "Refund and Cancellation Policy",
        "text": (
            "You may cancel your subscription at any time from Account Settings. "
            "Cancellations take effect at the end of the current billing period — "
            "you retain full access until then. "
            "Refund eligibility: monthly plans are eligible for a full refund within 7 days "
            "of the initial purchase. Annual plans are eligible within 30 days. "
            "After these windows, refunds are issued on a pro-rated basis for unused months. "
            "Refunds are credited to the original payment method within 5-7 business days. "
            "Promotional or discounted plans may have separate refund terms stated at purchase."
        ),
        "metadata": {
            "category": "billing",
            "type":     "article",
            "title":    "Refund and Cancellation Policy",
            "source":   "help-center",
        },
    },

    # ── Tech Support ──────────────────────────
    {
        "id":    "article-tech-001",
        "title": "Troubleshooting Webhook Failures",
        "text": (
            "Webhooks deliver real-time event notifications to your endpoint. "
            "Common causes of webhook failures: endpoint returning non-2xx status, "
            "SSL certificate errors, request timeout (>30 seconds), or firewall blocking. "
            "Our system retries failed webhooks up to 5 times using exponential backoff: "
            "1min, 5min, 30min, 2hr, 8hr. "
            "After 5 failures the webhook is marked as failed and you receive an email alert. "
            "To replay failed webhooks, go to Developer → Webhooks → Failed Events → Replay. "
            "For persistent 500 errors, check your server logs for null pointer exceptions "
            "or missing environment variables — these are the most common root causes."
        ),
        "metadata": {
            "category": "tech",
            "type":     "article",
            "title":    "Troubleshooting Webhook Failures",
            "source":   "dev-docs",
        },
    },
    {
        "id":    "article-tech-002",
        "title": "API Rate Limits and Best Practices",
        "text": (
            "Rate limits apply per API key per minute. "
            "Standard tier: 1,000 requests/min. Premium: 5,000. Enterprise: unlimited. "
            "When you exceed the rate limit, the API returns HTTP 429 Too Many Requests "
            "with a Retry-After header indicating when to retry. "
            "Best practices: implement exponential backoff, cache responses where possible, "
            "use bulk endpoints instead of looping single-item calls, "
            "and monitor your usage on the Developer Dashboard. "
            "If your use case requires higher limits, contact sales for a custom plan."
        ),
        "metadata": {
            "category": "tech",
            "type":     "article",
            "title":    "API Rate Limits and Best Practices",
            "source":   "dev-docs",
        },
    },

    # ── Policy ────────────────────────────────
    {
        "id":    "article-policy-001",
        "title": "Service Level Agreement (SLA) Overview",
        "text": (
            "Our SLA defines the guaranteed response and resolution times for support tickets. "
            "Response time targets by priority: "
            "Urgent (P1): first response within 4 hours, resolution within 24 hours. "
            "High (P2): first response within 8 hours, resolution within 48 hours. "
            "Medium (P3): first response within 24 hours, resolution within 5 business days. "
            "Low (P4): first response within 72 hours, resolution within 10 business days. "
            "Enterprise customers receive 2x faster response times. "
            "SLA timers pause during weekends and public holidays for standard/premium tiers. "
            "Enterprise SLAs run 24/7. Breached SLAs trigger automatic escalation."
        ),
        "metadata": {
            "category": "policy",
            "type":     "article",
            "title":    "SLA Overview",
            "source":   "policy-docs",
        },
    },
    {
        "id":    "article-policy-002",
        "title": "Data Retention and Privacy Policy",
        "text": (
            "We retain customer data for the duration of the subscription plus 90 days. "
            "After account deletion, all personal data is purged within 30 days. "
            "Ticket history and audit logs are retained for 2 years for compliance purposes. "
            "You can request a full data export at any time from Account Settings → Privacy. "
            "We comply with GDPR, CCPA, and ISO 27001 standards. "
            "Data is encrypted at rest (AES-256) and in transit (TLS 1.3). "
            "For data deletion requests, contact privacy@ticketflow.com."
        ),
        "metadata": {
            "category": "policy",
            "type":     "article",
            "title":    "Data Retention and Privacy Policy",
            "source":   "policy-docs",
        },
    },

    # ── Escalation ────────────────────────────
    {
        "id":    "article-escalation-001",
        "title": "When and How Tickets Are Escalated",
        "text": (
            "A ticket is automatically escalated when: the SLA deadline is breached, "
            "the customer tier is enterprise and no agent has responded within 1 hour, "
            "or the customer explicitly requests escalation. "
            "Manual escalation: any agent can escalate a ticket by changing the priority "
            "to Urgent and assigning it to the escalation queue. "
            "Escalated tickets are routed to senior agents and flagged in the dashboard. "
            "For VIP customers, a dedicated account manager is notified immediately. "
            "Escalation does not reset the SLA timer — the original deadline remains."
        ),
        "metadata": {
            "category": "escalation",
            "type":     "article",
            "title":    "When and How Tickets Are Escalated",
            "source":   "agent-handbook",
        },
    },
    {
        "id":    "article-escalation-002",
        "title": "Handling Angry or Frustrated Customers",
        "text": (
            "When a customer is frustrated, acknowledge the issue before offering solutions. "
            "Use empathetic language: 'I understand how frustrating this must be.' "
            "Do not be defensive or blame other teams. "
            "If the customer demands a supervisor, escalate immediately without pushback. "
            "For refund demands outside policy, escalate to billing team — do not promise "
            "refunds you are not authorised to approve. "
            "Document the tone and specific complaints in the ticket notes for context. "
            "Always close the interaction by confirming the next steps and timeline."
        ),
        "metadata": {
            "category": "escalation",
            "type":     "article",
            "title":    "Handling Frustrated Customers",
            "source":   "agent-handbook",
        },
    },
]


# ─────────────────────────────────────────────
# 3. Insert — skip already existing IDs
# ─────────────────────────────────────────────

existing_ids = set(collection.get()["ids"])
new_articles = [a for a in articles if a["id"] not in existing_ids]

if new_articles:
    print(f"\n📥 Embedding and inserting {len(new_articles)} articles...")
    collection.add(
        ids       = [a["id"]       for a in new_articles],
        documents = [a["text"]     for a in new_articles],
        metadatas = [a["metadata"] for a in new_articles],
    )
    print(f"✅ Done. Total documents now: {collection.count()}")
else:
    print(f"✅ All articles already embedded. Total: {collection.count()}")


# ─────────────────────────────────────────────
# 4. Semantic search tests
# ─────────────────────────────────────────────

print("\n" + "=" * 60)
print("SEMANTIC SEARCH TESTS")
print("=" * 60)

test_queries = [
    ("my invoice has a wrong charge",          "billing"),
    ("webhook is failing with 500 error",      "tech"),
    ("how fast will you respond to my ticket", "policy"),
    ("I want to speak to a manager",           "escalation"),
    ("can I get a refund for my annual plan",  "billing"),
    ("my API keeps hitting rate limits",       "tech"),
    ("delete all my personal data",            "policy"),
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
    similarity   = round(1 - top_distance, 3)

    matched = top_meta["category"] == expected_category
    print(f"\n  Query    : '{query_text}'")
    title   = top_meta.get("title") or top_meta.get("source", "untitled")
    print(f"Query    : '{query_text}'")
    print(f"  Article  : {title}")


# ─────────────────────────────────────────────
# 5. Category-filtered search
# ─────────────────────────────────────────────

print("\n" + "=" * 60)
print("FILTERED SEARCH — tech articles only")
print("=" * 60)

filtered = collection.query(
    query_texts=["something is broken on my integration"],
    n_results=2,
    where={"category": "tech"},
    include=["documents", "metadatas", "distances"],
)

for doc, meta, dist in zip(
    filtered["documents"][0],
    filtered["metadatas"][0],
    filtered["distances"][0],
):
    print(f"\n  [{meta.get('title', meta.get('source', 'untitled'))}]  score={round(1-dist, 3)}")
    print(f"  {doc[:120]}...")


# ─────────────────────────────────────────────
# 6. List all embedded articles
# ─────────────────────────────────────────────

print("\n" + "=" * 60)
print("ALL EMBEDDED ARTICLES")
print("=" * 60)

all_docs = collection.get(include=["metadatas"])
for id_, meta in zip(all_docs["ids"], all_docs["metadatas"]):
    print(f"  {id_:35} [{meta['category']:10}] {meta.get('title', meta.get('source', '?'))}")