"""
Embed All Support Articles into ChromaDB
-----------------------------------------
Single canonical file — 28 articles total:
  billing    : 9  (001-002 original + 003-009 new)
  tech       : 9  (001-002 original + 003-009 new)
  policy     : 2  (001-002 original)
  escalation : 2  (001-002 original)
  returns    : 6  (001-006 new)

Safe to run multiple times — skips already-embedded IDs.
First run downloads all-MiniLM-L6-v2 (~90MB), cached after that.

Setup:
    pip install chromadb sentence-transformers

Run:
    python embed_articles.py
"""

import os
import chromadb
from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction

# ─────────────────────────────────────────────
# 1. Client + collection
# ─────────────────────────────────────────────

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

client = chromadb.PersistentClient(path=os.path.join(BASE_DIR, "chroma_data"))

embedding_fn = SentenceTransformerEmbeddingFunction(
    model_name="all-MiniLM-L6-v2"
)

collection = client.get_or_create_collection(
    name="knowledge_base",
    embedding_function=embedding_fn,
)

print(f"✅ Collection '{collection.name}' ready")
print(f"   Documents before insert: {collection.count()}")


# ─────────────────────────────────────────────
# 2. All 28 articles
# ─────────────────────────────────────────────

ALL_ARTICLES = [

    # ════════════════════════════════════════════
    # BILLING (9)
    # ════════════════════════════════════════════

    {
        "id":   "article-billing-001",
        "text": (
            "Your monthly invoice is generated on the first of each month. "
            "It includes a breakdown of your base subscription, any add-ons, and applicable taxes. "
            "If you believe there is an error on your invoice, you must raise a dispute within 60 days. "
            "To dispute a charge, navigate to Billing → Invoices → Dispute. "
            "Our billing team reviews disputes within 3 business days. "
            "If the dispute is resolved in your favour, a credit is applied to your next invoice."
        ),
        "metadata": {"category": "billing", "type": "article",
                     "title": "Understanding Your Invoice", "source": "help-center"},
    },
    {
        "id":   "article-billing-002",
        "text": (
            "You may cancel your subscription at any time from Account Settings. "
            "Cancellations take effect at the end of the current billing period. "
            "Refund eligibility: monthly plans within 7 days, annual plans within 30 days. "
            "After these windows, refunds are issued on a pro-rated basis for unused months. "
            "Refunds are credited to the original payment method within 5-7 business days. "
            "Promotional or discounted plans may have separate refund terms stated at purchase."
        ),
        "metadata": {"category": "billing", "type": "article",
                     "title": "Refund and Cancellation Policy", "source": "help-center"},
    },
    {
        "id":   "article-billing-003",
        "text": (
            "Payment methods accepted include credit cards (Visa, Mastercard, Amex), "
            "debit cards, UPI, net banking, and bank transfers for enterprise customers. "
            "To update your payment method go to Account Settings → Billing → Payment Methods. "
            "If your card is declined, you receive an email with a link to update payment details. "
            "We retry failed payments 3 times over 7 days before suspending the account. "
            "A grace period of 3 days applies after suspension before data is affected."
        ),
        "metadata": {"category": "billing", "type": "article",
                     "title": "Accepted Payment Methods and Failed Payments", "source": "help-center"},
    },
    {
        "id":   "article-billing-004",
        "text": (
            "GST is applied at 18% on all INR invoices as per Indian tax regulations. "
            "Your GSTIN can be added under Account Settings → Billing → Tax Information. "
            "Once added, it appears on all future invoices automatically. "
            "To update the GSTIN on a past invoice, contact billing with the invoice number. "
            "Businesses registered outside India are not charged GST. "
            "Tax exemption certificates can be uploaded in the billing portal."
        ),
        "metadata": {"category": "billing", "type": "article",
                     "title": "GST and Tax Information on Invoices", "source": "help-center"},
    },
    {
        "id":   "article-billing-005",
        "text": (
            "To upgrade your plan, go to Account Settings → Plan → Upgrade. "
            "You are charged the pro-rated difference for the remaining billing period immediately. "
            "To downgrade, changes take effect at the end of the current billing period. "
            "Downgrading from Enterprise requires 30 days written notice. "
            "Feature access changes immediately on upgrade, and at period end on downgrade. "
            "Annual plan holders who upgrade are charged the difference for remaining months."
        ),
        "metadata": {"category": "billing", "type": "article",
                     "title": "Upgrading and Downgrading Your Plan", "source": "help-center"},
    },
    {
        "id":   "article-billing-006",
        "text": (
            "Overdue invoices accrue a late fee of 1.5% per month after the due date. "
            "You receive email reminders at 7 days, 3 days, and 1 day before the due date. "
            "After 14 days overdue, account features are restricted to read-only. "
            "After 30 days overdue, the account is suspended. "
            "To request a payment extension, contact billing before the due date. "
            "Paying a partial amount does not reset the overdue timer."
        ),
        "metadata": {"category": "billing", "type": "article",
                     "title": "Overdue Invoices and Late Fees", "source": "help-center"},
    },
    {
        "id":   "article-billing-007",
        "text": (
            "Annual plans are billed once per year and offer a 20% discount over monthly billing. "
            "The renewal date is exactly 12 months from the initial purchase date. "
            "You receive a renewal reminder 30 days before the renewal date. "
            "Auto-renewal is enabled by default and can be disabled from the billing portal. "
            "If auto-renewal is disabled, the account reverts to free tier after expiry. "
            "Early renewal is available at any time — contact sales for a custom quote."
        ),
        "metadata": {"category": "billing", "type": "article",
                     "title": "Annual Plan Billing and Renewal", "source": "help-center"},
    },
    {
        "id":   "article-billing-008",
        "text": (
            "Promo codes and discounts can be applied at checkout or from the billing portal. "
            "Go to Account Settings → Billing → Apply Promo Code. "
            "Each promo code can only be used once per account. "
            "Promo codes cannot be applied to invoices already issued. "
            "Discounts from promo codes do not stack with referral credits. "
            "Credits expire 12 months from the date they were issued."
        ),
        "metadata": {"category": "billing", "type": "article",
                     "title": "Promo Codes, Discounts, and Credits", "source": "help-center"},
    },
    {
        "id":   "article-billing-009",
        "text": (
            "Enterprise billing is handled through a custom contract with dedicated invoicing. "
            "Payment terms for enterprise are Net 30 by default, negotiable up to Net 60. "
            "Bank transfer and purchase order (PO) payments are supported for enterprise. "
            "A dedicated billing contact is assigned to each enterprise account. "
            "Consolidated billing is available for organisations with multiple sub-accounts. "
            "To request custom billing terms, contact your account manager."
        ),
        "metadata": {"category": "billing", "type": "article",
                     "title": "Enterprise Billing and Custom Contracts", "source": "help-center"},
    },


    # ════════════════════════════════════════════
    # TECH SUPPORT (9)
    # ════════════════════════════════════════════

    {
        "id":   "article-tech-001",
        "text": (
            "Webhooks deliver real-time event notifications to your endpoint. "
            "Common causes of webhook failures: endpoint returning non-2xx status, "
            "SSL certificate errors, request timeout over 30 seconds, or firewall blocking. "
            "Our system retries failed webhooks up to 5 times using exponential backoff. "
            "After 5 failures the webhook is marked as failed and you receive an email alert. "
            "To replay failed webhooks, go to Developer → Webhooks → Failed Events → Replay. "
            "For persistent 500 errors, check server logs for null pointer exceptions "
            "or missing environment variables."
        ),
        "metadata": {"category": "tech", "type": "article",
                     "title": "Troubleshooting Webhook Failures", "source": "dev-docs"},
    },
    {
        "id":   "article-tech-002",
        "text": (
            "Rate limits apply per API key per minute. "
            "Standard tier: 1,000 requests/min. Premium: 5,000. Enterprise: unlimited. "
            "When you exceed the rate limit, the API returns HTTP 429 Too Many Requests "
            "with a Retry-After header indicating when to retry. "
            "Best practices: implement exponential backoff, cache responses where possible, "
            "and monitor your usage on the Developer Dashboard. "
            "If your use case requires higher limits, contact sales for a custom plan."
        ),
        "metadata": {"category": "tech", "type": "article",
                     "title": "API Rate Limits and Best Practices", "source": "dev-docs"},
    },
    {
        "id":   "article-tech-003",
        "text": (
            "Authentication uses OAuth 2.0 and API keys. "
            "API keys are generated from Developer Settings → API Keys → Generate New Key. "
            "Each key has a name, expiry date, and optional IP whitelist. "
            "Rotate your API key immediately if you suspect it has been compromised. "
            "Old keys remain valid for 24 hours after rotation to allow zero-downtime migration. "
            "Use environment variables to store keys — never hardcode them in source code. "
            "Keys beginning with 'sk_live_' are production; 'sk_test_' are sandbox."
        ),
        "metadata": {"category": "tech", "type": "article",
                     "title": "API Authentication and Key Management", "source": "dev-docs"},
    },
    {
        "id":   "article-tech-004",
        "text": (
            "Our REST API uses standard HTTP status codes. "
            "200 OK: success. 201 Created: resource created. "
            "400 Bad Request: invalid parameters. 401 Unauthorized: invalid API key. "
            "403 Forbidden: insufficient permissions. 404 Not Found: resource missing. "
            "429 Too Many Requests: rate limit exceeded — check Retry-After header. "
            "500 Internal Server Error: retry with exponential backoff. "
            "503 Service Unavailable: check status.ticketflow.com."
        ),
        "metadata": {"category": "tech", "type": "article",
                     "title": "API Error Codes and Troubleshooting", "source": "dev-docs"},
    },
    {
        "id":   "article-tech-005",
        "text": (
            "Pagination is supported on all list endpoints using cursor-based pagination. "
            "Pass the cursor parameter from the previous response's next_cursor field. "
            "Page size is controlled by the limit parameter, default 20, maximum 100. "
            "To fetch all records, loop until next_cursor is null in the response. "
            "Offset-based pagination is deprecated and will be removed in API v3. "
            "Filtering is available via filter[field]=value query parameters. "
            "Sorting uses sort=field ascending or sort=-field descending."
        ),
        "metadata": {"category": "tech", "type": "article",
                     "title": "Pagination and Filtering in the API", "source": "dev-docs"},
    },
    {
        "id":   "article-tech-006",
        "text": (
            "Sandbox environment is available at api-sandbox.ticketflow.com. "
            "Use sk_test_ API keys for sandbox — they do not affect live data. "
            "Sandbox data resets every 24 hours at midnight UTC. "
            "Payment simulation: card 4111111111111111 for success, 4000000000000002 for declined. "
            "Webhook events in sandbox are sent to your configured test endpoint. "
            "Rate limits in sandbox are 100 requests per minute regardless of plan."
        ),
        "metadata": {"category": "tech", "type": "article",
                     "title": "Sandbox Environment and Testing", "source": "dev-docs"},
    },
    {
        "id":   "article-tech-007",
        "text": (
            "Data is available for export in JSON, CSV, and Excel formats. "
            "Bulk exports are available from Settings → Data → Export. "
            "Large exports are processed asynchronously — you receive a download link by email. "
            "The download link expires after 24 hours. "
            "Real-time data streaming is available via our Kafka-compatible event stream API. "
            "To set up streaming, contact your account manager for credentials."
        ),
        "metadata": {"category": "tech", "type": "article",
                     "title": "Data Export and Streaming", "source": "dev-docs"},
    },
    {
        "id":   "article-tech-008",
        "text": (
            "Two-factor authentication (2FA) is available via TOTP apps like Google Authenticator. "
            "Enable 2FA from Account Settings → Security → Two-Factor Authentication. "
            "Backup codes are generated when 2FA is enabled — store them securely offline. "
            "Enterprise accounts can enforce 2FA for all team members via the admin panel. "
            "SSO via SAML 2.0 is available for enterprise — contact support to configure. "
            "Session tokens expire after 24 hours of inactivity."
        ),
        "metadata": {"category": "tech", "type": "article",
                     "title": "Two-Factor Authentication and Security", "source": "dev-docs"},
    },
    {
        "id":   "article-tech-009",
        "text": (
            "Integration with Slack allows you to receive ticket notifications in your workspace. "
            "Install the Ticketflow Slack app from Settings → Integrations → Slack. "
            "Configure which events trigger notifications: new tickets, status changes, SLA breaches. "
            "Zapier integration is available for connecting Ticketflow to 5000+ apps. "
            "Native integrations: Jira, GitHub, PagerDuty, Salesforce, HubSpot. "
            "Integration setup guides are available at docs.ticketflow.com/integrations."
        ),
        "metadata": {"category": "tech", "type": "article",
                     "title": "Third-Party Integrations and Slack", "source": "dev-docs"},
    },


    # ════════════════════════════════════════════
    # POLICY (2)
    # ════════════════════════════════════════════

    {
        "id":   "article-policy-001",
        "text": (
            "Our SLA defines guaranteed response and resolution times for support tickets. "
            "Urgent (P1): first response within 4 hours, resolution within 24 hours. "
            "High (P2): first response within 8 hours, resolution within 48 hours. "
            "Medium (P3): first response within 24 hours, resolution within 5 business days. "
            "Low (P4): first response within 72 hours, resolution within 10 business days. "
            "Enterprise customers receive 2x faster response times. "
            "SLA timers pause on weekends for standard/premium. Enterprise SLAs run 24/7."
        ),
        "metadata": {"category": "policy", "type": "article",
                     "title": "SLA Overview", "source": "policy-docs"},
    },
    {
        "id":   "article-policy-002",
        "text": (
            "We retain customer data for the duration of the subscription plus 90 days. "
            "After account deletion, all personal data is purged within 30 days. "
            "Ticket history and audit logs are retained for 2 years for compliance. "
            "You can request a full data export from Account Settings → Privacy. "
            "We comply with GDPR, CCPA, and ISO 27001. "
            "Data is encrypted at rest (AES-256) and in transit (TLS 1.3)."
        ),
        "metadata": {"category": "policy", "type": "article",
                     "title": "Data Retention and Privacy Policy", "source": "policy-docs"},
    },


    # ════════════════════════════════════════════
    # ESCALATION (2)
    # ════════════════════════════════════════════

    {
        "id":   "article-escalation-001",
        "text": (
            "A ticket is automatically escalated when the SLA deadline is breached, "
            "when an enterprise customer has no response within 1 hour, "
            "or when the customer explicitly requests escalation. "
            "Manual escalation: change priority to Urgent and assign to the escalation queue. "
            "Escalated tickets are routed to senior agents and flagged in the dashboard. "
            "For VIP customers, a dedicated account manager is notified immediately. "
            "Escalation does not reset the SLA timer."
        ),
        "metadata": {"category": "escalation", "type": "article",
                     "title": "When and How Tickets Are Escalated", "source": "agent-handbook"},
    },
    {
        "id":   "article-escalation-002",
        "text": (
            "When a customer is frustrated, acknowledge the issue before offering solutions. "
            "Use empathetic language such as: I understand how frustrating this must be. "
            "Do not be defensive or blame other teams. "
            "If the customer demands a supervisor, escalate immediately without pushback. "
            "For refund demands outside policy, escalate to billing — do not make unauthorised promises. "
            "Document tone and complaints in ticket notes. "
            "Always confirm next steps and timeline before closing the interaction."
        ),
        "metadata": {"category": "escalation", "type": "article",
                     "title": "Handling Frustrated Customers", "source": "agent-handbook"},
    },


    # ════════════════════════════════════════════
    # RETURNS (6)
    # ════════════════════════════════════════════

    {
        "id":   "article-returns-001",
        "text": (
            "To initiate a return, go to Account Settings → Orders → select the order → Request Return. "
            "Returns must be initiated within the return window for your plan. "
            "Once submitted, you receive a Return Reference Number (RRN) by email. "
            "Return requests are reviewed within 2 business days. "
            "You are notified by email once the return is approved or rejected. "
            "Approved returns trigger the refund process automatically."
        ),
        "metadata": {"category": "returns", "type": "article",
                     "title": "How to Initiate a Return", "source": "returns-policy"},
    },
    {
        "id":   "article-returns-002",
        "text": (
            "Return eligibility windows: monthly plans 7 days, annual plans 30 days, "
            "enterprise contracts 30-60 days, add-ons and one-time purchases 14 days. "
            "Returns are not accepted after these windows under standard policy. "
            "Exceptions may be made for billing errors, technical failures, or duplicate charges. "
            "Free trial periods do not count toward the return window."
        ),
        "metadata": {"category": "returns", "type": "article",
                     "title": "Return Eligibility and Time Windows", "source": "returns-policy"},
    },
    {
        "id":   "article-returns-003",
        "text": (
            "Non-refundable items: setup fees, delivered onboarding packages, "
            "custom development work, and consumed API call credits. "
            "Partially used subscription months are refunded on a pro-rated basis. "
            "Domain registration fees are non-refundable after 24 hours. "
            "Annual plans are not refundable after 30 days regardless of usage."
        ),
        "metadata": {"category": "returns", "type": "article",
                     "title": "Non-Refundable Items and Pro-Rated Refunds", "source": "returns-policy"},
    },
    {
        "id":   "article-returns-004",
        "text": (
            "Refunds are processed to the original payment method used at purchase. "
            "Credit card refunds take 5-7 business days. "
            "UPI and net banking refunds take 3-5 business days. "
            "Bank transfer refunds take 7-10 business days. "
            "If you no longer have access to the original payment method, "
            "refunds can be issued as account credits or bank transfer. "
            "If 10 business days have passed with no refund, contact support with your RRN."
        ),
        "metadata": {"category": "returns", "type": "article",
                     "title": "Refund Processing Times and Methods", "source": "returns-policy"},
    },
    {
        "id":   "article-returns-005",
        "text": (
            "If you were charged for a renewal you did not intend, "
            "request a refund within 7 days of the charge. "
            "To prevent future auto-renewals, disable auto-renew before the renewal date. "
            "After 7 days, renewal charges are non-refundable. "
            "First-time renewal refund requests are usually approved as a goodwill gesture. "
            "Repeated renewal refund requests on the same account are declined."
        ),
        "metadata": {"category": "returns", "type": "article",
                     "title": "Unintended Renewal Charges and Refunds", "source": "returns-policy"},
    },
    {
        "id":   "article-returns-006",
        "text": (
            "Chargebacks filed with your bank are handled by our disputes team. "
            "Filing a chargeback without contacting support first may result in account suspension. "
            "Always contact support first — we resolve disputes faster than the bank process. "
            "If a chargeback is filed, our team submits evidence to the bank within 7 days. "
            "Accounts with open chargebacks cannot make new purchases until resolved. "
            "Contact billing at billing@ticketflow.com to resolve disputes directly."
        ),
        "metadata": {"category": "returns", "type": "article",
                     "title": "Chargebacks and Billing Disputes", "source": "returns-policy"},
    },
]


# ─────────────────────────────────────────────
# 3. Insert — skip already embedded IDs
# ─────────────────────────────────────────────

existing_ids = set(collection.get()["ids"])
to_insert    = [a for a in ALL_ARTICLES if a["id"] not in existing_ids]

if to_insert:
    print(f"\n📥 Embedding {len(to_insert)} new articles "
          f"(skipping {len(existing_ids)} already embedded)...")
    collection.add(
        ids       = [a["id"]       for a in to_insert],
        documents = [a["text"]     for a in to_insert],
        metadatas = [a["metadata"] for a in to_insert],
    )
    print(f"✅ Done.")
else:
    print(f"\n✅ All {len(ALL_ARTICLES)} articles already embedded — nothing to add.")

print(f"   Total documents in collection: {collection.count()}")


# ─────────────────────────────────────────────
# 4. Summary
# ─────────────────────────────────────────────

print("\n" + "=" * 65)
print("KNOWLEDGE BASE SUMMARY")
print("=" * 65)

all_docs = collection.get(include=["metadatas"])
category_counts = {}

for doc_id, meta in zip(all_docs["ids"], all_docs["metadatas"]):
    cat   = meta.get("category", "?")
    title = meta.get("title", meta.get("source", "untitled"))
    print(f"  {doc_id:35} [{cat:10}] {title}")
    category_counts[cat] = category_counts.get(cat, 0) + 1

print(f"\n{'─' * 65}")
for cat, count in sorted(category_counts.items()):
    print(f"  {cat:12} : {count} articles")
print(f"  {'TOTAL':12} : {collection.count()} articles")


# ─────────────────────────────────────────────
# 5. Smoke test
# ─────────────────────────────────────────────

print("\n" + "=" * 65)
print("SEMANTIC SEARCH SMOKE TEST")
print("=" * 65)

queries = [
    ("my invoice has a wrong charge",                       "billing"),
    ("webhook keeps returning 500 errors",                  "tech"),
    ("how long until I get a response to my ticket",        "policy"),
    ("I want to speak to a manager",                        "escalation"),
    ("can I get a refund for my annual plan",               "returns"),
    ("my API key stopped working",                          "tech"),
    ("chargeback filed with my bank",                       "returns"),
    ("promo code not working at checkout",                  "billing"),
    ("how do I test without affecting live data",           "tech"),
    ("refund took more than 10 days and still not arrived", "returns"),
]

for query, expected in queries:
    result  = collection.query(
        query_texts=[query], n_results=1,
        include=["metadatas", "distances"],
    )
    meta    = result["metadatas"][0][0]
    score   = round(1 - result["distances"][0][0], 3)
    title   = meta.get("title", meta.get("source", "?"))
    matched = meta.get("category") == expected
    print(f"\n  Query    : '{query}'")
    print(f"  Match    : {title}")
    print(f"  Category : {meta.get('category'):12} {'✅' if matched else '⚠️ '} expected={expected}  score={score}")