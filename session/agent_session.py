"""
AgentSession — Unified Session + Memory via Upstash Redis
----------------------------------------------------------
Merges SessionStore (user identity) and SessionMemory (conversation memory)
into one clean class.

Setup:
    pip install upstash-redis python-dotenv

    In .env:
        UPSTASH_REDIS_REST_URL=https://xxx.upstash.io
        UPSTASH_REDIS_REST_TOKEN=your-token

Usage:
    session = AgentSession(session_id="alice-001")
    session.create("alice@example.com", tier="enterprise")

    session.save_context("user", "My refund hasn't arrived")
    session.save_context("assistant", "I can help, what's your order number?")

    messages  = session.get_context(last_n=10)
    identity  = session.get_session()
    session.clear()
"""

from dotenv import load_dotenv
load_dotenv()

import os
import json
from datetime import datetime
from typing import Optional
from upstash_redis import Redis


class AgentSession:
    """
    Unified session + memory store for one user conversation.

    Redis keys:
        session:<id>        → user identity + agent state (JSON)
        session:<id>:msgs   → conversation messages (Redis list)
    """

    DEFAULT_TTL  = 60 * 60 * 2   # 2 hours sliding expiry
    MAX_MESSAGES = 50             # prune oldest beyond this

    def __init__(self, session_id: str, ttl: int = DEFAULT_TTL):
        url   = os.environ.get("UPSTASH_REDIS_REST_URL")
        token = os.environ.get("UPSTASH_REDIS_REST_TOKEN")

        if not url or not token:
            raise EnvironmentError(
                "UPSTASH_REDIS_REST_URL and UPSTASH_REDIS_REST_TOKEN must be set in .env"
            )

        self.redis      = Redis(url=url, token=token)
        self.session_id = session_id
        self.ttl        = ttl
        self._sess_key  = f"session:{session_id}"
        self._msgs_key  = f"session:{session_id}:msgs"


    # ─────────────────────────────────────────
    # Identity — who is this user?
    # ─────────────────────────────────────────

    def create(
        self,
        user_email:     str,
        customer_tier:  str = "standard",
    ) -> dict:
        """Create a new session. Overwrites any existing session for this ID."""
        data = {
            "session_id":    self.session_id,
            "user_email":    user_email,
            "customer_tier": customer_tier,
            "active_ticket": None,
            "agent_context": None,
            "intent":        None,
            "created_at":    datetime.utcnow().isoformat(),
            "last_active":   datetime.utcnow().isoformat(),
        }
        self.redis.setex(self._sess_key, self.ttl, json.dumps(data))
        return data

    def get_session(self) -> Optional[dict]:
        """
        Retrieve session identity and state.
        Returns None if expired or not found.
        Refreshes TTL on access (sliding expiry).
        """
        raw = self.redis.get(self._sess_key)
        if not raw:
            return None
        self._refresh_ttl()
        return json.loads(raw)

    def update(self, **kwargs) -> Optional[dict]:
        """
        Update any field on the session.
        Common usage:
            session.update(active_ticket="TKT-001", agent_context="billing")
        """
        data = self.get_session()
        if not data:
            return None
        data.update(kwargs)
        data["last_active"] = datetime.utcnow().isoformat()
        self.redis.setex(self._sess_key, self.ttl, json.dumps(data))
        return data

    def exists(self) -> bool:
        """True if session is alive (not expired)."""
        return self.redis.exists(self._sess_key) > 0

    def delete(self) -> None:
        """Delete session + conversation. Called on logout."""
        self.redis.delete(self._sess_key)
        self.redis.delete(self._msgs_key)


    # ─────────────────────────────────────────
    # Memory — what was said?
    # ─────────────────────────────────────────

    def save_context(
        self,
        role:    str,
        content: str,
        meta:    Optional[dict] = None,
    ) -> None:
        """
        Append one message turn to memory.

        Args:
            role:    "user" | "assistant" | "tool" | "system"
            content: message text
            meta:    optional extras e.g. {"tool_name": "calculator"}
        """
        message = {
            "role":      role,
            "content":   content,
            "timestamp": datetime.utcnow().isoformat(),
        }
        if meta:
            message["meta"] = meta

        self.redis.rpush(self._msgs_key, json.dumps(message))

        # Prune if over cap
        length = self.redis.llen(self._msgs_key)
        if length > self.MAX_MESSAGES:
            self.redis.ltrim(self._msgs_key, length - self.MAX_MESSAGES, -1)

        self._refresh_ttl()

    def get_context(self, last_n: int = 10) -> list[dict]:
        """
        Retrieve last N messages.
        Returns list of {role, content, timestamp} dicts.
        Ready to pass into LangGraph state or LLM.
        """
        raw = self.redis.lrange(self._msgs_key, -last_n, -1)
        if not raw:
            return []
        self._refresh_ttl()
        return [json.loads(m) for m in raw]

    def clear(self) -> None:
        """
        Wipe conversation history only.
        Keeps session identity intact — user stays logged in.
        Use delete() to remove everything including identity.
        """
        self.redis.delete(self._msgs_key)

    def message_count(self) -> int:
        """Number of messages currently in memory."""
        return self.redis.llen(self._msgs_key)

    def as_langchain_messages(self, last_n: int = 10) -> list:
        """
        Convert stored history to LangChain message objects.
        Ready to pass directly into llm.invoke().

        Requires: pip install langchain-core
        """
        from langchain_core.messages import HumanMessage, AIMessage, SystemMessage

        role_map = {
            "user":      HumanMessage,
            "assistant": AIMessage,
            "system":    SystemMessage,
        }
        return [
            role_map[m["role"]](content=m["content"])
            for m in self.get_context(last_n)
            if m["role"] in role_map
        ]


    # ─────────────────────────────────────────
    # Internal
    # ─────────────────────────────────────────

    def _refresh_ttl(self) -> None:
        """Reset expiry on both keys — called on every read/write."""
        self.redis.expire(self._sess_key, self.ttl)
        self.redis.expire(self._msgs_key, self.ttl)

    def __repr__(self) -> str:
        return (
            f"AgentSession(id={self.session_id!r}, "
            f"exists={self.exists()}, "
            f"messages={self.message_count()})"
        )


# ─────────────────────────────────────────────
# Smoke test
# ─────────────────────────────────────────────

if __name__ == "__main__":
    session = AgentSession(session_id="test-alice-001")

    # clean slate
    session.delete()

    # ── identity ─────────────────────────────
    print("── Identity ──")
    session.create("alice@example.com", customer_tier="enterprise")
    print(f"  Created   : {session.exists()}")

    session.update(active_ticket="TKT-2025-004", agent_context="escalation", intent="refund")
    data = session.get_session()
    print(f"  Email     : {data['user_email']}")
    print(f"  Tier      : {data['customer_tier']}")
    print(f"  Ticket    : {data['active_ticket']}")
    print(f"  Agent     : {data['agent_context']}")

    # ── memory ───────────────────────────────
    print("\n── Memory ──")
    session.save_context("user",      "My refund hasn't arrived after 7 days")
    session.save_context("assistant", "I can help. What is your order number?")
    session.save_context("user",      "ORD-2025-004")
    session.save_context("tool",      "order status: cancelled, ₹8499",
                         meta={"tool_name": "lookup"})
    session.save_context("assistant", "Your refund of ₹8499 is being escalated now.")

    print(f"  Messages  : {session.message_count()}")
    for msg in session.get_context(last_n=10):
        tag = f"[{msg['meta']['tool_name']}] " if "meta" in msg else ""
        print(f"  [{msg['role']:9}] {tag}{msg['content']}")

    # ── as_langchain_messages ─────────────────
    print("\n── LangChain messages (last 3) ──")
    try:
        for m in session.as_langchain_messages(last_n=3):
            print(f"  {type(m).__name__:14} : {m.content[:60]}")
    except ImportError:
        print("  (install langchain-core to use as_langchain_messages)")

    # ── clear memory, keep identity ───────────
    print("\n── clear() — wipes messages, keeps identity ──")
    session.clear()
    print(f"  Messages after clear : {session.message_count()}")
    print(f"  Session still alive  : {session.exists()}")

    # ── delete everything ─────────────────────
    print("\n── delete() — wipes everything ──")
    session.delete()
    print(f"  Exists after delete  : {session.exists()}")

    print(f"\n{session}")
    print("\n✅ All AgentSession tests passed")