"""Model usage accounting: tokens (estimated), latency, errors, quotas and admin statistics."""

import math
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from app.config import settings
from app.services.storage_service import storage_service


def estimate_tokens(text: str) -> int:
    """Rough token count (about four characters per token). Marked as an estimate in the UI."""
    return math.ceil(len(text or "") / 4)


def _now() -> datetime:
    return datetime.now(timezone.utc)


def record(owner_id: str, bot_id: str, model: str, channel: str, prompt_tokens: int,
           completion_tokens: int, latency_ms: int, ok: bool) -> None:
    with storage_service.database.connect() as c:
        c.execute(
            "INSERT INTO usage_events(owner_id, bot_id, model, channel, prompt_tokens, completion_tokens, "
            "latency_ms, ok, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (owner_id, bot_id, model, channel, prompt_tokens, completion_tokens, latency_ms,
             1 if ok else 0, _now().isoformat()))


def tokens_today(owner_id: str) -> int:
    start = _now().replace(hour=0, minute=0, second=0, microsecond=0).isoformat()
    with storage_service.database.connect() as c:
        row = c.execute("SELECT COALESCE(SUM(prompt_tokens + completion_tokens), 0) FROM usage_events "
                        "WHERE owner_id = ? AND created_at >= ?", (owner_id, start)).fetchone()
    return int(row[0])


def quota_status(owner_id: str) -> Optional[str]:
    """Return a message when the member cannot use the model right now."""
    with storage_service.database.connect() as c:
        row = c.execute("SELECT disabled, token_limit FROM users WHERE id = ?", (owner_id,)).fetchone()
    if row is None:
        return None
    if row["disabled"]:
        return "El teu compte està suspès."
    if row["token_limit"] and tokens_today(owner_id) >= row["token_limit"]:
        return "Has arribat al límit diari d'ús. Torna-ho a provar demà."
    return None


def cost(tokens_in: int, tokens_out: int) -> float:
    return round(tokens_in / 1e6 * settings.TOKEN_PRICE_IN_PER_M + tokens_out / 1e6 * settings.TOKEN_PRICE_OUT_PER_M, 4)


def _pct(values: List[int], q: float) -> int:
    if not values:
        return 0
    ordered = sorted(values)
    return ordered[min(len(ordered) - 1, int(math.ceil(q * len(ordered))) - 1)]


def stats(days: int = 30) -> Dict[str, Any]:
    days = max(1, min(days, 365))
    since = (_now() - timedelta(days=days)).isoformat()
    week = (_now() - timedelta(days=7)).isoformat()
    with storage_service.database.connect() as c:
        events = c.execute("SELECT * FROM usage_events WHERE created_at >= ? ORDER BY id", (since,)).fetchall()
        users = c.execute("SELECT id, username, role, email, name, provider, disabled, token_limit, created_at, last_seen "
                          "FROM users").fetchall()
        bot_rows = c.execute("SELECT owner_id, payload FROM bots").fetchall()
        msg_counts = {r[0]: r[1] for r in c.execute("SELECT owner_id, COUNT(*) FROM messages GROUP BY owner_id")}
    import json

    bots: Dict[str, Dict[str, Any]] = {}
    dots_per_owner: Dict[str, int] = {}
    for row in bot_rows:
        try:
            payload = json.loads(row["payload"])
        except (TypeError, ValueError):
            continue
        bots[payload.get("id", "")] = {"name": payload.get("name", "?"), "owner": row["owner_id"]}
        dots_per_owner[row["owner_id"]] = dots_per_owner.get(row["owner_id"], 0) + 1
    names = {u["id"]: (u["name"] or u["email"] or u["username"]) for u in users}
    has_members = any(u["id"] != "local-user" for u in users)
    if has_members:  # the built-in local owner and its demo Dots are not customers
        dots_per_owner.pop("local-user", None)
        msg_counts.pop("local-user", None)

    daily: Dict[str, Dict[str, Any]] = {}
    for i in range(days):
        d = (_now() - timedelta(days=days - 1 - i)).strftime("%Y-%m-%d")
        daily[d] = {"date": d, "requests": 0, "tokens": 0, "errors": 0, "users": set()}
    by_model: Dict[str, Dict[str, Any]] = {}
    by_channel: Dict[str, int] = {}
    by_user: Dict[str, Dict[str, int]] = {}
    by_dot: Dict[str, Dict[str, int]] = {}
    latencies: List[int] = []
    tin = tout = errors = 0
    for e in events:
        day = e["created_at"][:10]
        tok = e["prompt_tokens"] + e["completion_tokens"]
        tin += e["prompt_tokens"]
        tout += e["completion_tokens"]
        errors += 0 if e["ok"] else 1
        if e["ok"]:
            latencies.append(e["latency_ms"])
        if day in daily:
            d = daily[day]
            d["requests"] += 1
            d["tokens"] += tok
            d["errors"] += 0 if e["ok"] else 1
            d["users"].add(e["owner_id"])
        m = by_model.setdefault(e["model"] or "?", {"model": e["model"] or "?", "requests": 0, "tokens": 0, "errors": 0})
        m["requests"] += 1; m["tokens"] += tok; m["errors"] += 0 if e["ok"] else 1
        by_channel[e["channel"]] = by_channel.get(e["channel"], 0) + 1
        u = by_user.setdefault(e["owner_id"], {"requests": 0, "tokens": 0})
        u["requests"] += 1; u["tokens"] += tok
        if e["bot_id"]:
            b = by_dot.setdefault(e["bot_id"], {"requests": 0, "tokens": 0, "errors": 0})
            b["requests"] += 1; b["tokens"] += tok; b["errors"] += 0 if e["ok"] else 1

    total = len(events)
    active_7d = len({e["owner_id"] for e in events if e["created_at"] >= week})
    members = [u for u in users if u["role"] != "owner" or u["id"] != "local-user"]
    user_rows = []
    for u in members:
        use = by_user.get(u["id"], {"requests": 0, "tokens": 0})
        user_rows.append({
            "id": u["id"], "name": u["name"] or u["username"], "email": u["email"], "provider": u["provider"],
            "role": u["role"], "disabled": bool(u["disabled"]), "token_limit": u["token_limit"],
            "created_at": u["created_at"], "last_seen": u["last_seen"],
            "dots": dots_per_owner.get(u["id"], 0), "messages": msg_counts.get(u["id"], 0),
            "requests": use["requests"], "tokens": use["tokens"], "tokens_today": tokens_today(u["id"]),
            "cost": cost(use["tokens"], 0),
        })
    user_rows.sort(key=lambda r: r["tokens"], reverse=True)
    top_dots = sorted(
        ({"id": k, "name": bots.get(k, {}).get("name", "(esborrat)"),
          "owner": names.get(bots.get(k, {}).get("owner", ""), "?"), **v} for k, v in by_dot.items()),
        key=lambda r: r["tokens"], reverse=True)[:10]
    return {
        "days": days, "generated_at": _now().isoformat(), "token_note": "Tokens estimats (uns 4 caràcters per token).",
        "totals": {
            "members": len([u for u in members if u["role"] == "member"]), "active_7d": active_7d,
            "dots": sum(dots_per_owner.values()), "messages": sum(msg_counts.values()),
            "requests": total, "errors": errors, "error_rate": round(errors / total, 4) if total else 0,
            "tokens_in": tin, "tokens_out": tout, "est_cost_usd": cost(tin, tout),
            "avg_latency_ms": round(sum(latencies) / len(latencies)) if latencies else 0,
            "p50_latency_ms": _pct(latencies, .5), "p95_latency_ms": _pct(latencies, .95),
        },
        "daily": [{**d, "users": len(d["users"])} for d in daily.values()],
        "by_model": sorted(by_model.values(), key=lambda r: r["tokens"], reverse=True),
        "by_channel": [{"channel": k, "requests": v} for k, v in sorted(by_channel.items(), key=lambda kv: -kv[1])],
        "top_dots": top_dots,
        "users": user_rows,
    }
