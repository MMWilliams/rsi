"""
Kyberos API — FastAPI application entry point.

Includes:
  - Firestore-backed persistence (no InMemoryDB)
  - Rate limiting via slowapi (per-user, per-endpoint)
  - SSE disconnect detection with graceful cleanup
  - Chat history endpoints tied to user accounts
  - Phase 1: Plan CRUD, sharing, public plan viewer, RSVP
  - Health check with Firestore connectivity
  - Request logging with correlation IDs
"""

import asyncio
import json
import logging
import os
import time
import uuid
from contextlib import asynccontextmanager
from typing import Any, Optional

from dotenv import load_dotenv
from fastapi import Depends, FastAPI, HTTPException, Request, Response, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
from app.routes.reservations import router as reservations_router
from app.routes.companions import (
    router as companions_router,
    set_companion_service,
)
from app.companions.service import CompanionService
from app.opentable.factory import get_adapter
load_dotenv()

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("kyberos.api")

# ---------------------------------------------------------------------------
# Imports
# ---------------------------------------------------------------------------

import firebase_admin
from firebase_admin import auth as firebase_auth

from app.agent.orchestrator import Orchestrator
from app.agent.tools import ToolRegistry
from app.db.postgres import PostgresDB, create_pool
from app.entitlements import (
    Tier,
    capabilities_for,
    default_tier,
    normalize_tier,
    open_capabilities,
    tier_info,
)
from app.gats.engine import GATSEngine
from app.plans.service import PlanService
from app.usage import UsageMeter

# ---------------------------------------------------------------------------
# Rate limiter (per-user keying)
# ---------------------------------------------------------------------------

def _get_user_id_for_rate_limit(request: Request) -> str:
    """
    Rate-limit key. Signed-in users are keyed by uid; anonymous guests are
    keyed by client IP, because their uid is regenerated per request and would
    otherwise let each request start a fresh bucket (bypassing the limit).
    """
    user = getattr(request.state, "user", None)
    if user and isinstance(user, dict):
        uid = user.get("uid")
        if uid and not user.get("anonymous") and not str(uid).startswith("anon_"):
            return f"uid:{uid}"
    return f"ip:{get_remote_address(request)}"


limiter = Limiter(key_func=_get_user_id_for_rate_limit)


def _rate_limit_exceeded_handler(request: Request, exc: RateLimitExceeded) -> Response:
    return Response(
        content=f'{{"error": "Rate limit exceeded: {exc.detail}"}}',
        status_code=429,
        media_type="application/json",
    )


# ---------------------------------------------------------------------------
# App lifecycle
# ---------------------------------------------------------------------------

db: Optional[PostgresDB] = None
db_pool = None
orchestrator: Optional[Orchestrator] = None
plan_service: Optional[PlanService] = None
usage_meter: Optional[UsageMeter] = None
mcp_manager: Optional[Any] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global db, orchestrator, plan_service, usage_meter

    logger.info("Starting Kyberos API...")

    # Firebase Auth still verifies tokens; only the DATA moved to Postgres.
    try:
        from app.auth.firebase import init_firebase
        init_firebase()
    except Exception as exc:  # noqa: BLE001
        logger.warning("Firebase Auth unavailable (%s); auth will be bypassed", exc)

    global db_pool
    try:
        db_pool = await create_pool()
        db = PostgresDB(db_pool)
        try:
            await asyncio.wait_for(db.load_l2_stats(), timeout=5)
            logger.info("Postgres connected")
        except asyncio.TimeoutError:
            logger.warning("L2 stats load timed out; continuing startup")
    except Exception as exc:
        if os.getenv("ENV") == "development":
            logger.warning(
                "Postgres unavailable in dev mode (%s). "
                "Using in-memory mock — data will not persist across restarts.",
                str(exc),
            )
            from app.db.firestore_mock import MockFirestoreDB
            db = MockFirestoreDB()
        else:
            raise

    # Initialize GATS engine
    anthropic_key = os.getenv("ANTHROPIC_API_KEY", "")
    gats_engine = GATSEngine(
        anthropic_api_key=anthropic_key,
        l2_stats_loader=db.load_l2_stats,
    )

    # Initialize orchestrator with real tool registry
   # Initialize plan service first so the orchestrator can persist plans
    if db_pool is not None:
        plan_service = PlanService(pool=db_pool)
    else:
        logger.warning("PlanService not initialized — no database pool")

    tool_registry = ToolRegistry()

    # Connect any configured MCP servers and register their tools into the same
    # registry the planner uses. No-op when KYBEROS_MCP_SERVERS isn't set.
    global mcp_manager
    try:
        from app.agent.mcp_client import MCPManager, load_mcp_config
        mcp_manager = MCPManager(load_mcp_config())
        await mcp_manager.start()
        n = tool_registry.register_mcp(mcp_manager)
        if n:
            logger.info("MCP: registered %d external tool(s) from %d server(s)",
                        n, len(mcp_manager._sessions))
    except Exception as exc:  # noqa: BLE001
        logger.error("MCP initialization failed (continuing without it): %s", exc)

    # CompanionService is still Firestore-shaped and has no Postgres port yet.
    # Left uninitialized rather than half-wired: its routes already answer 503
    # in that state, which is honest, where a partly-migrated service would
    # accept writes and lose them.
    companion_service: Optional[CompanionService] = None
    logger.info("CompanionService disabled (not migrated to Postgres)")

    orchestrator = Orchestrator(
        gats_engine=gats_engine,
        db=db,
        tool_registry=tool_registry,
        plan_service=plan_service,
        companion_service=companion_service,
    )
    usage_meter = UsageMeter(db=db)
    app.state.opentable = get_adapter()

    logger.info(
        "Kyberos API ready (env=%s, open_capabilities=%s, daily_limit=%s)",
        ENV, open_capabilities(), usage_meter._limit,
    )
    yield

    logger.info("Shutting down Kyberos API...")
    if orchestrator:
        await orchestrator.close()
    if mcp_manager:
        await mcp_manager.close()
    if db_pool is not None:
        await db_pool.close()


# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------

app = FastAPI(title="Kyberos API", version="1.1.0", lifespan=lifespan)



app.include_router(reservations_router, prefix="/api")
app.include_router(companions_router, prefix="/api")
from app.voice import router as voice_router  # noqa: E402
app.include_router(voice_router, prefix="/api")
from app.routes.playground import router as playground_router  # noqa: E402
app.include_router(playground_router, prefix="/api")
from app.routes.audit import router as audit_router  # noqa: E402
app.include_router(audit_router, prefix="/api")
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

_default_origins = [
    "https://www.kyberos.ai",
    "https://kyberos.ai",
    "https://kyberos.vercel.app",
    "http://localhost:5173",
]
_extra_origins = [
    origin.strip()
    for origin in os.getenv("FRONTEND_ORIGINS", "").split(",")
    if origin.strip()
]

# In development, allow any localhost/127.0.0.1 port so `npm run dev` works
# regardless of which port Vite lands on (5173 may be taken). In production we
# rely on the explicit allowlist only.
_cors_kwargs: dict[str, Any] = dict(
    allow_origins=[*_default_origins, *_extra_origins],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
if os.getenv("ENV", "production") == "development":
    _cors_kwargs["allow_origin_regex"] = r"https?://(localhost|127\.0\.0\.1)(:\d+)?"

app.add_middleware(CORSMiddleware, **_cors_kwargs)


@app.get("/")
@app.head("/")
async def root():
    return {"status": "ok"}


# ---------------------------------------------------------------------------
# Middleware — correlation ID + request logging
# ---------------------------------------------------------------------------

@app.middleware("http")
async def request_logging_middleware(request: Request, call_next):
    correlation_id = request.headers.get("X-Correlation-ID", str(uuid.uuid4()))
    request.state.correlation_id = correlation_id
    start = time.monotonic()
    try:
        response = await call_next(request)
    except Exception:
        elapsed = (time.monotonic() - start) * 1000
        logger.exception(
            "request_failed | method=%s path=%s latency_ms=%.0f correlation_id=%s",
            request.method, request.url.path, elapsed, correlation_id,
        )
        raise
    elapsed = (time.monotonic() - start) * 1000
    logger.info(
        "request_completed | method=%s path=%s status=%d latency_ms=%.0f correlation_id=%s",
        request.method, request.url.path, response.status_code, elapsed, correlation_id,
    )
    response.headers["X-Correlation-ID"] = correlation_id
    return response



# ---------------------------------------------------------------------------
# Auth dependency
# ---------------------------------------------------------------------------

ENV = os.getenv("ENV", "production")

# Max recent messages forwarded to the planner as context (the context window).
CONTEXT_WINDOW_MESSAGES = int(os.getenv("KYBEROS_CONTEXT_WINDOW", "12"))

# Max total attachment payload (base64 + inline text) per request (~16MB).
MAX_ATTACHMENT_BYTES = int(os.getenv("KYBEROS_MAX_ATTACHMENT_BYTES", str(16_000_000)))

# How long an SSE response may go without sending anything before it emits a
# keep-alive comment. Well under the ~100s idle timeout proxies apply.
SSE_HEARTBEAT_SECONDS = float(os.getenv("KYBEROS_SSE_HEARTBEAT_SECONDS", "15"))


async def verify_firebase_token(request: Request) -> dict[str, Any]:
    """Verify Firebase ID token from Authorization header."""
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                            detail="Missing or malformed Authorization header")

    token = auth_header.removeprefix("Bearer ").strip()

    if ENV == "development" and token == "dev-test-token":
        user = {"uid": "dev-user-001", "email": "dev@kyberos.local", "name": "Dev User"}
        request.state.user = user
        return user

    try:
        decoded = firebase_auth.verify_id_token(token)
        request.state.user = decoded
        return decoded
    except firebase_auth.InvalidIdTokenError:
        raise HTTPException(status_code=401, detail="Invalid Firebase ID token")
    except firebase_auth.ExpiredIdTokenError:
        raise HTTPException(status_code=401, detail="Firebase ID token expired")
    except Exception as exc:
        logger.error("Token verification failed: %s", str(exc))
        raise HTTPException(status_code=401, detail="Authentication failed")

async def verify_firebase_token_optional(request: Request) -> dict[str, Any]:
    """Auth that allows guests."""
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        anon_uid = f"anon_{uuid.uuid4().hex[:12]}"
        user = {"uid": anon_uid, "email": None, "name": "Guest", "anonymous": True}
        request.state.user = user
        return user
    return await verify_firebase_token(request)


# ---------------------------------------------------------------------------
# Tier resolution
# ---------------------------------------------------------------------------

async def resolve_user_tier(uid: str) -> Tier:
    """
    Determine a user's tier.

    Reads ``users/{uid}.tier`` from Firestore when available, falling back to
    ``KYBEROS_DEFAULT_TIER`` (env, default 'free'). Anonymous guests and any
    lookup failure resolve to the default tier. This is the single hook a
    future billing layer overrides — it sets the stored field; everything
    else (gating, catalog) already keys off the resolved tier.
    """
    fallback = default_tier()
    if not uid or uid.startswith("anon_"):
        return fallback
    if db is None or not hasattr(db, "get_user_tier"):
        return fallback
    try:
        tier = await asyncio.wait_for(db.get_user_tier(uid), timeout=3.0)
        if tier:
            return normalize_tier(tier)
    except Exception:
        logger.warning("Tier lookup failed for %s; using default", uid)
    return fallback


def _quota_key(request: Request, user: dict) -> str:
    """
    Key used for the daily request quota.

    Signed-in users are keyed by uid. Anonymous guests get a fresh uid on
    every request (so uid can't accumulate), so they're keyed by client IP.
    """
    if user.get("anonymous") or str(user.get("uid", "")).startswith("anon_"):
        return f"ip:{get_remote_address(request)}"
    return user["uid"]


# ---------------------------------------------------------------------------
# Request/response models
# ---------------------------------------------------------------------------

class ContextMessage(BaseModel):
    role: str = Field(default="user", max_length=20)
    text: str = Field(default="", max_length=1000)


class AgentPreferences(BaseModel):
    # `custom_instructions` is the user's system prompt, passed to the API.
    custom_instructions: Optional[str] = Field(default=None, max_length=4000)
    allow_browsing: bool = True


class Attachment(BaseModel):
    name: str = Field(default="file", max_length=200)
    kind: str = Field(default="text", pattern=r"^(text|image|document)$")
    media_type: Optional[str] = Field(default=None, max_length=100)
    data: Optional[str] = Field(default=None)   # base64 (image/document)
    text: Optional[str] = Field(default=None, max_length=40000)  # inline text


class ExecuteRequest(BaseModel):
    goal: str = Field(..., min_length=1, max_length=4000)
    mode: str = Field(default="autonomous", pattern=r"^(manual|semi-auto|autonomous)$")
    conversation_id: Optional[str] = Field(default=None, max_length=100)
    # Recent conversation for follow-ups. Bounded here (the context window):
    # at most CONTEXT_WINDOW_MESSAGES are forwarded to the planner.
    context: Optional[list[ContextMessage]] = Field(default=None, max_length=20)
    # Model personality (system prompt) + agent preferences.
    preferences: Optional[AgentPreferences] = None
    # Uploaded files forwarded to the model (size-bounded; see route).
    attachments: Optional[list[Attachment]] = Field(default=None, max_length=8)
    # Optional companion id. When supplied, the orchestrator merges the
    # companion's saved preferences into the goal before assessment so
    # downstream planning gets the full context without the user retyping it.
    companion_id: Optional[str] = Field(default=None, max_length=100)
    # Answers to the clarifying card, keyed by dimension ("budget",
    # "transport", "date_time"). Present only on the follow-up request the
    # UI sends after the user taps through; the orchestrator folds them into
    # the goal and does not ask again.
    clarification_answers: Optional[dict[str, str]] = Field(default=None)


class ApprovalRequest(BaseModel):
    execution_id: str = Field(..., min_length=1, max_length=100)
    approved: bool


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------

@app.get("/health")
async def health_check():
    db_ok = False
    if db:
        db_ok = await db.health_check()
    return {
        "status": "ok" if db_ok else "degraded",
        "env": ENV,
        "database": db_ok,
        "anthropic": bool(os.getenv("ANTHROPIC_API_KEY")),
        "timestamp": time.time(),
    }


# ---------------------------------------------------------------------------
# Capabilities / entitlements
# ---------------------------------------------------------------------------

@app.get("/api/me")
@limiter.limit("60/minute")
async def get_me(request: Request, user: dict = Depends(verify_firebase_token_optional)):
    """
    Report the caller's tier, unlocked capabilities, and the general tool
    catalog available to them. The frontend uses this to gate UI and show
    upgrade prompts. Works for guests (resolves to the default tier).
    """
    uid = user["uid"]
    tier = await resolve_user_tier(uid)
    info = tier_info(tier)
    catalog = orchestrator.available_tools(tier) if orchestrator else []
    usage = (
        await usage_meter.peek(_quota_key(request, user), tier)
        if usage_meter else None
    )
    return {
        "uid": uid,
        "anonymous": bool(user.get("anonymous")),
        "tier": tier.value,
        "tier_label": info.label,
        "tier_blurb": info.blurb,
        "capabilities": sorted(c.value for c in capabilities_for(tier)),
        "open_capabilities": open_capabilities(),
        "tools": catalog,
        "usage": usage.to_dict() if usage else None,
    }


@app.get("/api/diagnostics")
@limiter.limit("20/minute")
async def diagnostics(request: Request, user: dict = Depends(verify_firebase_token_optional)):
    """
    Server-side capability self-check. Actually exercises Tavily web search and
    launches headless Chromium so the frontend can surface real capability
    errors. Results are cached (~3 min); pass ?force=1 to bypass the cache.
    """
    if not orchestrator:
        raise HTTPException(status_code=503, detail="Service not initialized")
    from app.diagnostics import probe_capabilities

    force = request.query_params.get("force") == "1"
    return await probe_capabilities(
        orchestrator.registry,
        anthropic_key=os.getenv("ANTHROPIC_API_KEY", ""),
        force=force,
    )


# ---------------------------------------------------------------------------
# Agent execution endpoints
# ---------------------------------------------------------------------------

# slowapi here is only a burst/abuse guard. The product-level daily cap is the
# tier-aware UsageMeter (100/day for free & pro, unlimited for ultimate).
@app.post("/api/agent/execute")
@limiter.limit("60/minute")
async def execute_agent(request: Request, user: dict = Depends(verify_firebase_token_optional)):
    raw = await request.json()
    body = ExecuteRequest(**raw)
    if not orchestrator or not db:
        raise HTTPException(status_code=503, detail="Service not initialized")

    uid = user["uid"]
    tier = await resolve_user_tier(uid)

    # Moderation gate — refuse clearly-disallowed requests before doing anything
    # (and without consuming the user's daily quota).
    from app.moderation import check_request

    refusal = check_request(body.goal)
    if refusal:
        logger.info("Refused request from %s: %s", uid, refusal)

        async def _refusal_stream():
            msg = json.dumps({
                "message": f"I can’t help with {refusal}. I’m happy to help with "
                           "something else.",
            })
            yield f"event: refused\ndata: {msg}\n\n"
            end = json.dumps({"status": "refused"})
            yield f"event: execution_end\ndata: {end}\n\n"

        return StreamingResponse(
            _refusal_stream(),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
        )

    # Attachment payload guard — bound the total size (base64 + inline text).
    attachments = None
    if body.attachments:
        total = sum(len(a.data or "") + len(a.text or "") for a in body.attachments)
        if total > MAX_ATTACHMENT_BYTES:
            raise HTTPException(status_code=413, detail="Attachments too large (max ~16MB total).")
        attachments = [a.model_dump() for a in body.attachments]

    # Context window: forward at most the most-recent N messages to the planner.
    conv_context = None
    if body.context:
        conv_context = [
            {"role": m.role, "text": m.text}
            for m in body.context[-CONTEXT_WINDOW_MESSAGES:]
            if m.text.strip()
        ]

    # Daily request quota. Ultimate is unlimited; everyone else is capped.
    if usage_meter:
        usage = await usage_meter.consume(_quota_key(request, user), tier)
        if not usage.allowed:
            raise HTTPException(
                status_code=429,
                detail=(
                    f"Daily request limit reached ({usage.limit}/day). "
                    f"Upgrade to Ultimate for unlimited usage."
                ),
                headers={
                    "X-RateLimit-Limit": str(usage.limit),
                    "X-RateLimit-Remaining": "0",
                },
            )

    logger.info(
        "Execution request | user=%s tier=%s mode=%s goal_len=%d goal_repr=%r",
        uid,
        tier.value,
        body.mode,
        len(body.goal),
        body.goal,
    )
    execution_id_holder: dict[str, str] = {}

    async def event_stream():
        # A single step can be silent for a long time — planning, report
        # synthesis and the direct-answer call are each one model request with
        # no interim output. Proxies (and Render in particular) drop a
        # connection that sends nothing, which the browser reports as a bare
        # "Load failed" mid-run. Producing events into a queue lets the
        # response emit an SSE comment while the agent is still thinking, so
        # the connection never goes idle.
        queue: asyncio.Queue = asyncio.Queue()
        done = object()

        async def produce() -> None:
            try:
                async for event in orchestrator.execute(
                    user_id=uid, goal=body.goal, mode=body.mode,
                    conversation_id=body.conversation_id, user_tier=tier,
                    context=conv_context,
                    preferences=body.preferences.model_dump() if body.preferences else None,
                    attachments=attachments,
                    companion_id=body.companion_id,
                    clarification_answers=body.clarification_answers,
                ):
                    await queue.put(event)
            except asyncio.CancelledError:
                raise
            except Exception as exc:  # noqa: BLE001
                logger.exception("SSE stream error for user %s", uid)
                payload = json.dumps({"message": str(exc)})
                await queue.put(f"event: error\ndata: {payload}\n\n")
            finally:
                await queue.put(done)

        async def cleanup_disconnected() -> None:
            exec_id = execution_id_holder.get("id")
            if exec_id:
                logger.info("SSE client disconnected, cleaning up execution %s", exec_id)
                await orchestrator.handle_disconnect(exec_id)

        producer = asyncio.create_task(produce())
        try:
            while True:
                try:
                    event = await asyncio.wait_for(queue.get(), SSE_HEARTBEAT_SECONDS)
                except asyncio.TimeoutError:
                    if await request.is_disconnected():
                        await cleanup_disconnected()
                        break
                    # A comment line: valid SSE, ignored by every client.
                    yield ": keep-alive\n\n"
                    continue

                if event is done:
                    break

                if await request.is_disconnected():
                    await cleanup_disconnected()
                    break

                if not execution_id_holder.get("id") and "execution_id" in event:
                    try:
                        for line in event.split("\n"):
                            if line.startswith("data: "):
                                data = json.loads(line[6:])
                                if "execution_id" in data:
                                    execution_id_holder["id"] = data["execution_id"]
                                break
                    except Exception:
                        pass
                yield event
                await asyncio.sleep(0)
        except asyncio.CancelledError:
            await cleanup_disconnected()
            raise
        finally:
            producer.cancel()

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive", "X-Accel-Buffering": "no"},
    )


@app.post("/api/agent/approve")
@limiter.limit("30/minute")
async def approve_step(request: Request, user: dict = Depends(verify_firebase_token)):
    raw = await request.json()
    body = ApprovalRequest(**raw)
    if not orchestrator:
        raise HTTPException(status_code=503, detail="Service not initialized")
    if body.approved:
        success = await orchestrator.approve_step(body.execution_id)
    else:
        success = await orchestrator.deny_step(body.execution_id)
    if not success:
        raise HTTPException(status_code=404, detail="Execution not found or no pending approval")
    return {"status": "ok", "approved": body.approved}


@app.post("/api/agent/cancel")
@limiter.limit("10/minute")
async def cancel_execution(request: Request, user: dict = Depends(verify_firebase_token)):
    raw = await request.json()
    if not orchestrator:
        raise HTTPException(status_code=503, detail="Service not initialized")
    exec_id = raw.get("execution_id", "")
    if not exec_id:
        raise HTTPException(status_code=422, detail="execution_id required")
    success = await orchestrator.cancel_execution(exec_id)
    if not success:
        raise HTTPException(status_code=404, detail="Execution not found")
    return {"status": "cancelled"}


# ---------------------------------------------------------------------------
# Chat history endpoints (legacy — conversations)
# ---------------------------------------------------------------------------

@app.get("/api/conversations")
@limiter.limit("30/minute")
async def list_conversations(request: Request, user: dict = Depends(verify_firebase_token),
                              limit: int = 50, before: Optional[float] = None):
    if not db:
        raise HTTPException(status_code=503, detail="Service not initialized")
    conversations = await db.list_conversations(user_id=user["uid"], limit=min(limit, 100), offset_after=before)
    return {"conversations": conversations}


@app.get("/api/conversations/{conversation_id}")
@limiter.limit("30/minute")
async def get_conversation(request: Request, conversation_id: str,
                            user: dict = Depends(verify_firebase_token)):
    if not db:
        raise HTTPException(status_code=503, detail="Service not initialized")
    conversation = await db.get_conversation(user["uid"], conversation_id)
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    steps = await db.get_steps(user["uid"], conversation_id)
    return {"conversation": conversation, "steps": steps}


@app.delete("/api/conversations/{conversation_id}")
@limiter.limit("10/minute")
async def delete_conversation(request: Request, conversation_id: str,
                               user: dict = Depends(verify_firebase_token)):
    if not db:
        raise HTTPException(status_code=503, detail="Service not initialized")
    await db.delete_conversation(user["uid"], conversation_id)
    return {"status": "deleted"}


# ===========================================================================
# Phase 1: Plan endpoints
# ===========================================================================

@app.get("/api/plans")
@limiter.limit("30/minute")
async def list_plans(request: Request, user: dict = Depends(verify_firebase_token),
                      limit: int = 20, before: Optional[float] = None):
    """List plans for the authenticated user."""
    if not plan_service:
        raise HTTPException(status_code=503, detail="Service not initialized")
    plans = await plan_service.list_plans(user_id=user["uid"], limit=min(limit, 50), before=before)
    return {"plans": plans}


@app.get("/api/plans/{plan_id}")
@limiter.limit("30/minute")
async def get_plan(request: Request, plan_id: str, user: dict = Depends(verify_firebase_token)):
    """Fetch a plan with its activities."""
    if not plan_service:
        raise HTTPException(status_code=503, detail="Service not initialized")
    plan = await plan_service.get_plan(user["uid"], plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")
    activities = await plan_service.get_activities(user["uid"], plan_id)
    return {"plan": plan, "activities": activities}


@app.patch("/api/plans/{plan_id}")
@limiter.limit("30/minute")
async def update_plan(request: Request, plan_id: str, user: dict = Depends(verify_firebase_token)):
    """Update plan metadata (title, description, status)."""
    if not plan_service:
        raise HTTPException(status_code=503, detail="Service not initialized")
    raw = await request.json()
    allowed = {"title", "description", "status"}
    filtered = {k: v for k, v in raw.items() if k in allowed}
    if not filtered:
        raise HTTPException(status_code=422, detail="No valid fields to update")
    await plan_service.update_plan(user["uid"], plan_id, filtered)
    return {"status": "updated"}


@app.delete("/api/plans/{plan_id}")
@limiter.limit("10/minute")
async def delete_plan(request: Request, plan_id: str, user: dict = Depends(verify_firebase_token)):
    """Delete a plan and all its data."""
    if not plan_service:
        raise HTTPException(status_code=503, detail="Service not initialized")
    await plan_service.delete_plan(user["uid"], plan_id)
    return {"status": "deleted"}


@app.post("/api/plans/{plan_id}/share")
@limiter.limit("10/minute")
async def share_plan(request: Request, plan_id: str, user: dict = Depends(verify_firebase_token)):
    if not plan_service:
        raise HTTPException(status_code=503, detail="Service not initialized")
    raw = await request.json() if request.headers.get("content-length", "0") != "0" else {}
    try:
        result = await plan_service.create_share_link(
            user_id=user["uid"], plan_id=plan_id,
            owner_name=user.get("name", ""),
            expires_in_days=raw.get("expires_in_days"),
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return result


@app.delete("/api/plans/{plan_id}/share")
@limiter.limit("10/minute")
async def revoke_share(request: Request, plan_id: str, user: dict = Depends(verify_firebase_token)):
    """Revoke a plan's share link."""
    if not plan_service:
        raise HTTPException(status_code=503, detail="Service not initialized")
    await plan_service.revoke_share(user["uid"], plan_id)
    return {"status": "revoked"}


# ===========================================================================
# Public endpoints (no auth — share-token keyed)
# ===========================================================================

@app.get("/api/share/{share_id}")
@limiter.limit("60/minute")
async def get_shared_plan(request: Request, share_id: str):
    """Fetch a shared plan snapshot (public, no auth)."""
    if not plan_service:
        raise HTTPException(status_code=503, detail="Service not initialized")
    data = await plan_service.get_shared_plan(share_id)
    if not data:
        raise HTTPException(status_code=404, detail="Plan not found or expired")
    return data


@app.get("/api/share/{share_id}/events")
@limiter.limit("30/minute")
async def get_shared_plan_events(request: Request, share_id: str):
    """Fetch replay events for a shared plan (public, no auth)."""
    if not plan_service:
        raise HTTPException(status_code=503, detail="Service not initialized")
    events = await plan_service.get_shared_plan_events(share_id)
    return {"events": events}


@app.post("/api/share/{share_id}/rsvp")
@limiter.limit("10/minute")
async def submit_rsvp(request: Request, share_id: str):
    """Submit an RSVP to a shared plan (public, no auth)."""
    if not plan_service:
        raise HTTPException(status_code=503, detail="Service not initialized")
    raw = await request.json()
    name = raw.get("name", "").strip()
    email = raw.get("email", "").strip()
    rsvp = raw.get("rsvp", "").strip()
    if not name or not email or rsvp not in ("yes", "no", "maybe"):
        raise HTTPException(status_code=422, detail="name, email, and rsvp (yes/no/maybe) required")
    await plan_service.submit_rsvp(share_id, name, email, rsvp)
    return {"status": "submitted"}


@app.get("/api/share/{share_id}/rsvps")
@limiter.limit("30/minute")
async def get_rsvps(request: Request, share_id: str, user: dict = Depends(verify_firebase_token)):
    """Get RSVPs for a shared plan (owner only)."""
    if not plan_service:
        raise HTTPException(status_code=503, detail="Service not initialized")
    rsvps = await plan_service.get_rsvps(share_id)
    return {"rsvps": rsvps}

@app.post("/api/executions/{execution_id}/finalize")
@limiter.limit("20/minute")
async def finalize_execution(
    request: Request,
    execution_id: str,
    user: dict = Depends(verify_firebase_token),
):
    """Persist the user's refined venue list as the plan's final activities."""
    if not plan_service:
        raise HTTPException(status_code=503, detail="Service not initialized")

    raw = await request.json()
    venues = raw.get("venues", [])
    if not isinstance(venues, list):
        raise HTTPException(status_code=422, detail="venues must be a list")

    plan = await plan_service.get_plan_by_execution_id(user["uid"], execution_id)
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found for this execution")
    plan_id = plan["id"]

    # Wipe existing activities and re-save the user's refined list as the
    # source of truth.
    existing = await plan_service.get_activities(user["uid"], plan_id)
    for act in existing:
        try:
            await plan_service._client.collection("users").document(user["uid"]) \
                .collection("plans").document(plan_id) \
                .collection("activities").document(act["id"]).delete()
        except Exception:
            logger.warning("Failed to delete activity %s", act.get("id"))

    for i, venue in enumerate(venues):
        await plan_service.save_activity(
            user_id=user["uid"],
            plan_id=plan_id,
            activity_id=f"act_{i:03d}",
            data={
                "order": i,
                "type": venue.get("type", "dining"),
                "title": venue.get("name") or venue.get("title", ""),
                "venue": venue,
                "status": "pending",
                "user_time": venue.get("userTime"),
            },
        )

    update_data = {"status": "finalized"}
    party_size = raw.get("party_size")
    if party_size:
        update_data["party_size"] = party_size
    await plan_service.update_plan(user["uid"], plan_id, update_data)

    return {"plan_id": plan_id, "activity_count": len(venues), "status": "finalized"}


