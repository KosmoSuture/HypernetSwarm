"""
Hypernet Swarm — Standalone FastAPI Server

Lightweight web server for the swarm dashboard and API.
Replaces the need for ``hypernet.server`` when running the swarm as
a standalone package.

Exports:
    create_swarm_app  — build a FastAPI application
    attach_swarm      — wire a live Swarm + WebMessenger into the app

Endpoints:
    GET  /                    — redirect to dashboard
    GET  /swarm/dashboard     — serve the static HTML dashboard
    GET  /swarm/status        — full swarm status JSON
    GET  /swarm/health        — subsystem health check
    GET  /swarm/trust         — per-worker trust status
    GET  /swarm/providers     — available LLM providers with key/model info
    POST /swarm/start         — start the swarm loop
    POST /swarm/stop          — stop the swarm loop
    GET  /swarm/config        — current config (secrets masked)
    POST /swarm/config        — update config values
    POST /swarm/workers       — add a worker dynamically
    DELETE /swarm/workers/{n} — remove a worker
"""

from __future__ import annotations

import json
import logging
import threading
import traceback
from pathlib import Path
from typing import Any, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from .swarm import Swarm
    from .messenger import WebMessenger

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Provider catalogue — static metadata used by /swarm/providers
# ---------------------------------------------------------------------------

_PROVIDER_CATALOGUE: list[dict[str, Any]] = [
    {
        "name": "anthropic",
        "key_field": "anthropic_api_key",
        "models": [
            "claude-opus-4-6",
            "claude-sonnet-4-6",
            "claude-haiku-4-5-20251001",
        ],
    },
    {
        "name": "openai",
        "key_field": "openai_api_key",
        "models": [
            "gpt-4o",
            "gpt-4o-mini",
        ],
    },
    {
        "name": "gemini",
        "key_field": "gemini_api_key",
        "models": [
            "gemini/gemini-2.5-flash",
            "gemini/gemini-2.5-pro",
            "gemini/gemini-2.0-flash",
        ],
    },
    {
        "name": "groq",
        "key_field": "groq_api_key",
        "models": [
            "groq/llama-3.3-70b-versatile",
            "groq/llama-3.1-8b-instant",
            "groq/mixtral-8x7b-32768",
        ],
    },
    {
        "name": "cerebras",
        "key_field": "cerebras_api_key",
        "models": [
            "cerebras/llama-3.3-70b",
            "cerebras/llama-3.1-8b",
        ],
    },
    {
        "name": "ollama",
        "key_field": None,
        "always_configured": True,
        "models": [
            "ollama/llama3",
            "ollama/mistral",
            "ollama/codellama",
        ],
    },
    {
        "name": "mistral",
        "key_field": "mistral_api_key",
        "models": [
            "mistral/mistral-large-latest",
        ],
    },
    {
        "name": "together",
        "key_field": "together_api_key",
        "models": [
            "together/meta-llama/Llama-3.3-70B-Instruct-Turbo",
        ],
    },
    {
        "name": "deepseek",
        "key_field": "deepseek_api_key",
        "models": [
            "deepseek/deepseek-chat",
        ],
    },
    {
        "name": "cohere",
        "key_field": "cohere_api_key",
        "models": [
            "cohere/command-r-plus",
        ],
    },
    {
        "name": "huggingface",
        "key_field": "huggingface_api_key",
        "models": [
            "huggingface/meta-llama/Llama-3.3-70B-Instruct",
        ],
    },
    {
        "name": "openrouter",
        "key_field": "openrouter_api_key",
        "models": [
            "openrouter/google/gemini-2.5-flash",
        ],
    },
    {
        "name": "lmstudio",
        "key_field": None,
        "always_configured": True,
        "models": [
            "local/auto",
        ],
    },
]

# Maps provider key_field → friendly name (used when masking config)
_KEY_FIELDS = {entry["key_field"]: entry["name"] for entry in _PROVIDER_CATALOGUE if entry.get("key_field")}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _key_count(value: Any) -> int:
    """Return how many API keys a config value represents."""
    if isinstance(value, list):
        return len(value)
    if isinstance(value, str) and value:
        return 1
    return 0


def _mask(value: Any) -> Any:
    """Replace secret strings with '***', preserving structure."""
    if isinstance(value, list):
        return ["***" if v else "" for v in value]
    if isinstance(value, str) and value:
        return "***"
    return ""


def _safe_json(obj: Any) -> Any:
    """Make an object JSON-serialisable by converting unknowns to strings."""
    if isinstance(obj, dict):
        return {k: _safe_json(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_safe_json(v) for v in obj]
    if isinstance(obj, (str, int, float, bool, type(None))):
        return obj
    return str(obj)


# ---------------------------------------------------------------------------
# Route registration
# ---------------------------------------------------------------------------

def _register_routes(app: "FastAPI") -> None:  # noqa: F821 — FastAPI resolved at call-time
    """Attach all swarm endpoints to *app*."""

    from fastapi import Request
    from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse

    # -- GET / → redirect to dashboard ---------------------------------

    @app.get("/", include_in_schema=False)
    def root():
        return RedirectResponse(url="/swarm/dashboard")

    # -- GET /swarm/dashboard ------------------------------------------

    @app.get("/swarm/dashboard", include_in_schema=False)
    def dashboard():
        html_path = Path(__file__).parent / "static" / "swarm.html"
        if html_path.exists():
            return HTMLResponse(html_path.read_text(encoding="utf-8"))
        return HTMLResponse("<h1>Dashboard not found</h1>", status_code=404)

    # -- GET /swarm/status ---------------------------------------------

    @app.get("/swarm/status")
    def swarm_status():
        try:
            swarm: Optional[Swarm] = getattr(app.state, "swarm", None)
            if swarm is None:
                return JSONResponse({"status": "not_running", "message": "Swarm not started"})

            if not getattr(swarm, "_running", False):
                return JSONResponse({
                    "status": "stopped",
                    "worker_count": len(swarm.workers),
                    "workers": [
                        {"name": n, "model": getattr(w, "model", "unknown")}
                        for n, w in swarm.workers.items()
                    ],
                })

            workers_info = []
            for name, worker in swarm.workers.items():
                stats = swarm._worker_stats.get(name, {})
                current = swarm._worker_current_task.get(name)
                workers_info.append({
                    "name": name,
                    "model": getattr(worker, "model", "unknown"),
                    "provider": getattr(worker, "provider_name", "unknown"),
                    "mock": getattr(worker, "mock", True),
                    "current_task": current,
                    "tasks_completed": stats.get("tasks_completed", 0),
                    "tasks_failed": stats.get("tasks_failed", 0),
                    "personal_tasks": stats.get("personal_tasks", 0),
                    "tokens_used": stats.get("tokens_used", 0),
                    "total_duration_s": round(stats.get("total_duration_seconds", 0), 1),
                })

            return JSONResponse(_safe_json({
                "status": "running",
                "session_start": swarm._session_start,
                "tick_count": swarm._tick_count,
                "tasks_completed": swarm._tasks_completed,
                "tasks_failed": swarm._tasks_failed,
                "personal_tasks_completed": swarm._personal_tasks_completed,
                "worker_count": len(swarm.workers),
                "workers": workers_info,
                "boot_status": {},
                "recent_tasks": (
                    swarm._task_history[-20:]
                    if hasattr(swarm, "_task_history")
                    else []
                ),
                "report": (
                    swarm.status_report()
                    if hasattr(swarm, "status_report")
                    else ""
                ),
                "reputation": (
                    swarm.reputation.stats()
                    if hasattr(swarm, "reputation")
                    else {}
                ),
                "limits": (
                    swarm.limits.summary()
                    if hasattr(swarm, "limits")
                    else {}
                ),
                "coordinator": (
                    swarm.coordinator.stats()
                    if hasattr(swarm, "coordinator")
                    else {}
                ),
                "reboot_pending": getattr(swarm, "_reboot_requested", False),
            }))
        except Exception:
            log.exception("Error in /swarm/status")
            return JSONResponse(
                {"error": "Internal error retrieving swarm status", "detail": traceback.format_exc()},
                status_code=500,
            )

    # -- GET /swarm/health ---------------------------------------------

    @app.get("/swarm/health")
    def swarm_health():
        try:
            swarm: Optional[Swarm] = getattr(app.state, "swarm", None)
            if swarm is None:
                return JSONResponse({"status": "not_running", "message": "Swarm not started"})

            if hasattr(swarm, "health_check"):
                return JSONResponse(_safe_json(swarm.health_check()))

            # Fallback: basic status when health_check isn't available
            return JSONResponse({
                "status": "running" if getattr(swarm, "_running", False) else "stopped",
                "worker_count": len(swarm.workers),
                "tick_count": getattr(swarm, "_tick_count", 0),
            })
        except Exception:
            log.exception("Error in /swarm/health")
            return JSONResponse(
                {"error": "Internal error during health check", "detail": traceback.format_exc()},
                status_code=500,
            )

    # -- GET /swarm/trust ----------------------------------------------

    @app.get("/swarm/trust")
    def swarm_trust():
        try:
            swarm: Optional[Swarm] = getattr(app.state, "swarm", None)
            if swarm is None:
                return JSONResponse({"status": "not_running", "message": "Swarm not started"})

            trust_chain = getattr(swarm, "trust_chain", None)
            worker_entries = []

            for name in swarm.workers:
                if trust_chain is not None and hasattr(trust_chain, "check"):
                    try:
                        result = trust_chain.check(name)
                        level = getattr(result, "trust_level", "green") if result else "green"
                        issues = getattr(result, "issues", []) if result else []
                    except Exception:
                        level = "unknown"
                        issues = ["trust check raised an exception"]
                else:
                    level = "green"
                    issues = []

                worker_entries.append({
                    "name": name,
                    "trust_level": str(level),
                    "trust_issues": list(issues),
                })

            green_count = sum(1 for w in worker_entries if w["trust_level"] == "green")
            total = len(worker_entries)

            if green_count == total:
                overall = "trusted"
            elif green_count > 0:
                overall = "degraded"
            else:
                overall = "untrusted"

            return JSONResponse({
                "status": overall,
                "total_workers": total,
                "green": green_count,
                "workers": worker_entries,
            })
        except Exception:
            log.exception("Error in /swarm/trust")
            return JSONResponse(
                {"error": "Internal error checking trust", "detail": traceback.format_exc()},
                status_code=500,
            )

    # -- POST /swarm/start ---------------------------------------------

    @app.post("/swarm/start")
    def swarm_start():
        try:
            swarm: Optional[Swarm] = getattr(app.state, "swarm", None)
            if swarm is None:
                return JSONResponse(
                    {"error": "No swarm instance attached — call attach_swarm() first"},
                    status_code=400,
                )

            if getattr(swarm, "_running", False):
                return JSONResponse({"status": "already_running", "message": "Swarm is already running"})

            # Run the swarm in a background thread so the HTTP response returns
            thread = threading.Thread(target=swarm.run, name="swarm-loop", daemon=True)
            thread.start()

            return JSONResponse({"status": "starting", "message": "Swarm loop started in background thread"})
        except Exception:
            log.exception("Error in /swarm/start")
            return JSONResponse(
                {"error": "Failed to start swarm", "detail": traceback.format_exc()},
                status_code=500,
            )

    # -- POST /swarm/stop ----------------------------------------------

    @app.post("/swarm/stop")
    def swarm_stop():
        try:
            swarm: Optional[Swarm] = getattr(app.state, "swarm", None)
            if swarm is None:
                return JSONResponse(
                    {"error": "No swarm instance attached"},
                    status_code=400,
                )

            if not getattr(swarm, "_running", False):
                return JSONResponse({"status": "already_stopped", "message": "Swarm is not running"})

            swarm._running = False
            return JSONResponse({"status": "stopping", "message": "Swarm stop signal sent"})
        except Exception:
            log.exception("Error in /swarm/stop")
            return JSONResponse(
                {"error": "Failed to stop swarm", "detail": traceback.format_exc()},
                status_code=500,
            )

    # -- GET /swarm/config ---------------------------------------------

    @app.get("/swarm/config")
    def swarm_config_get():
        try:
            swarm: Optional[Swarm] = getattr(app.state, "swarm", None)
            if swarm is None:
                return JSONResponse(
                    {"error": "No swarm instance attached"},
                    status_code=400,
                )

            api_keys = getattr(swarm, "_api_keys", {})

            # Mask secrets but show which keys are configured
            masked_keys: dict[str, Any] = {}
            for key_field, provider_name in _KEY_FIELDS.items():
                val = api_keys.get(key_field, "")
                masked_keys[key_field] = _mask(val)

            # Collect non-secret config values
            config: dict[str, Any] = {
                "mock_mode": getattr(swarm, "_mock_mode", False),
                "worker_count": len(swarm.workers),
                "workers": [
                    {"name": n, "model": getattr(w, "model", "unknown")}
                    for n, w in swarm.workers.items()
                ],
                "personal_time_ratio": getattr(swarm, "personal_time_ratio", 0.25),
                "status_interval_seconds": getattr(swarm, "status_interval", 7200),
                "hard_max_sessions": getattr(swarm, "hard_max_sessions", 4),
                "soft_max_sessions": getattr(swarm, "soft_max_sessions", 2),
                "idle_shutdown_seconds": getattr(swarm, "idle_shutdown_seconds", 1800),
                "spawn_cooldown_seconds": getattr(swarm, "spawn_cooldown_seconds", 120),
                "api_keys": masked_keys,
            }

            # Include router config if present
            router = getattr(swarm, "router", None)
            if router is not None:
                config["model_routing"] = {
                    "default_model": getattr(router, "default_model", ""),
                    "local_model": getattr(router, "local_model", None),
                    "fallback_model": getattr(router, "fallback_model", None),
                    "rules": getattr(router, "rules", []),
                }

            # Budget config
            budget = getattr(swarm, "budget_tracker", None)
            if budget is not None and hasattr(budget, "config"):
                bc = budget.config
                config["budget"] = {
                    "daily_limit_usd": getattr(bc, "daily_limit_usd", 0),
                    "session_limit_usd": getattr(bc, "session_limit_usd", 0),
                }

            return JSONResponse(_safe_json(config))
        except Exception:
            log.exception("Error in GET /swarm/config")
            return JSONResponse(
                {"error": "Internal error reading config", "detail": traceback.format_exc()},
                status_code=500,
            )

    # -- POST /swarm/config --------------------------------------------

    @app.post("/swarm/config")
    async def swarm_config_post(request: Request):
        try:
            swarm: Optional[Swarm] = getattr(app.state, "swarm", None)
            if swarm is None:
                return JSONResponse(
                    {"error": "No swarm instance attached"},
                    status_code=400,
                )

            body = await request.json()
            updated_fields: list[str] = []

            # Update API keys (only non-masked values)
            new_keys = body.get("api_keys", {})
            if new_keys and isinstance(new_keys, dict):
                for k, v in new_keys.items():
                    if isinstance(v, str) and v not in ("", "***"):
                        swarm._api_keys[k] = v
                        updated_fields.append(k)
                    elif isinstance(v, list):
                        cleaned = [item for item in v if item not in ("", "***")]
                        if cleaned:
                            swarm._api_keys[k] = cleaned
                            updated_fields.append(k)

            # Update simple scalar config values
            scalar_mappings = {
                "personal_time_ratio": ("personal_time_ratio", float),
                "hard_max_sessions": ("hard_max_sessions", int),
                "soft_max_sessions": ("soft_max_sessions", int),
                "idle_shutdown_seconds": ("idle_shutdown_seconds", int),
                "spawn_cooldown_seconds": ("spawn_cooldown_seconds", int),
            }
            for json_key, (attr, cast) in scalar_mappings.items():
                if json_key in body:
                    try:
                        setattr(swarm, attr, cast(body[json_key]))
                        updated_fields.append(json_key)
                    except (ValueError, TypeError):
                        pass

            # Update model routing
            routing = body.get("model_routing")
            if routing and isinstance(routing, dict):
                router = getattr(swarm, "router", None)
                if router is not None:
                    if "default_model" in routing:
                        router.default_model = routing["default_model"]
                    if "local_model" in routing:
                        router.local_model = routing["local_model"]
                    if "fallback_model" in routing:
                        router.fallback_model = routing["fallback_model"]
                    if "rules" in routing and isinstance(routing["rules"], list):
                        router.rules = routing["rules"]
                    updated_fields.append("model_routing")

            # Persist to config file if we know where it is
            config_path = getattr(app.state, "config_path", None)
            saved_to_disk = False
            if config_path and updated_fields:
                try:
                    p = Path(config_path)
                    existing = {}
                    if p.exists():
                        existing = json.loads(p.read_text(encoding="utf-8"))
                    # Merge API keys
                    for k in list(new_keys.keys()):
                        val = swarm._api_keys.get(k)
                        if val:
                            existing[k] = val
                    # Merge scalars
                    for json_key in scalar_mappings:
                        if json_key in body:
                            existing[json_key] = body[json_key]
                    if routing:
                        existing["model_routing"] = routing
                    p.write_text(json.dumps(existing, indent=2), encoding="utf-8")
                    saved_to_disk = True
                except Exception as e:
                    log.warning("Could not persist config to %s: %s", config_path, e)

            return JSONResponse({
                "status": "updated",
                "updated_fields": updated_fields,
                "saved_to_disk": saved_to_disk,
            })
        except json.JSONDecodeError:
            return JSONResponse({"error": "Invalid JSON body"}, status_code=400)
        except Exception:
            log.exception("Error in POST /swarm/config")
            return JSONResponse(
                {"error": "Internal error updating config", "detail": traceback.format_exc()},
                status_code=500,
            )

    # -- GET /swarm/providers ------------------------------------------

    @app.get("/swarm/providers")
    def swarm_providers():
        try:
            swarm: Optional[Swarm] = getattr(app.state, "swarm", None)
            api_keys = getattr(swarm, "_api_keys", {}) if swarm else {}

            providers = []
            for entry in _PROVIDER_CATALOGUE:
                key_field = entry.get("key_field")
                always = entry.get("always_configured", False)

                if always:
                    configured = True
                    kc = 0
                elif key_field:
                    val = api_keys.get(key_field, "")
                    configured = bool(val)
                    kc = _key_count(val)
                else:
                    configured = False
                    kc = 0

                providers.append({
                    "name": entry["name"],
                    "configured": configured,
                    "key_count": kc,
                    "models": list(entry["models"]),
                })

            return JSONResponse({"providers": providers})
        except Exception:
            log.exception("Error in /swarm/providers")
            return JSONResponse(
                {"error": "Internal error listing providers", "detail": traceback.format_exc()},
                status_code=500,
            )

    # -- POST /swarm/workers -------------------------------------------

    @app.post("/swarm/workers")
    async def swarm_workers_add(request: Request):
        try:
            swarm: Optional[Swarm] = getattr(app.state, "swarm", None)
            if swarm is None:
                return JSONResponse(
                    {"error": "No swarm instance attached"},
                    status_code=400,
                )

            body = await request.json()
            model = body.get("model", "").strip()
            if not model:
                return JSONResponse({"error": "Missing required field: model"}, status_code=400)

            # Auto-generate name if not provided
            name = body.get("name", "").strip()
            if not name:
                # Derive a name from the model, e.g. "gemini-2.5-flash-1"
                base = model.split("/")[-1].split("-")[0].capitalize()
                counter = 1
                while f"{base}-{counter}" in swarm.workers:
                    counter += 1
                name = f"{base}-{counter}"

            if name in swarm.workers:
                return JSONResponse(
                    {"error": f"Worker '{name}' already exists"},
                    status_code=409,
                )

            # Build the worker — import here to avoid circular deps at module level
            from .identity import InstanceProfile, IdentityManager
            from .worker import Worker

            # Try to load an existing profile via the identity manager
            identity_mgr = getattr(swarm, "identity_mgr", None)
            profile = None
            if identity_mgr is not None and hasattr(identity_mgr, "load_instance"):
                profile = identity_mgr.load_instance(name)

            # Fall back to a minimal profile if nothing on disk
            if profile is None:
                profile = InstanceProfile(
                    name=name,
                    model=model,
                    orientation="general-purpose worker",
                    capabilities=["text"],
                    tags=["dynamic"],
                    address=f"2.1.{name.lower()}",
                )

            api_keys = getattr(swarm, "_api_keys", {})
            mock = getattr(swarm, "_mock_mode", False)
            tool_executor = getattr(swarm, "_tool_executor", None)

            worker = Worker(
                identity=profile,
                identity_manager=identity_mgr,
                api_keys=api_keys,
                mock=mock,
                tool_executor=tool_executor,
            )
            # Override model if the caller requested a specific one
            worker.model = model

            swarm.workers[name] = worker

            # Initialise stats entry
            swarm._worker_stats[name] = {
                "tasks_completed": 0,
                "tasks_failed": 0,
                "personal_tasks": 0,
                "tokens_used": 0,
                "total_duration_seconds": 0.0,
                "last_task_title": None,
            }

            # Register with coordinator if present
            coordinator = getattr(swarm, "coordinator", None)
            if coordinator is not None and hasattr(coordinator, "register"):
                try:
                    from .coordinator import CapabilityProfile
                    cap = CapabilityProfile(
                        instance_name=name,
                        strengths=list(profile.capabilities),
                        tags=list(profile.tags),
                    )
                    coordinator.register(cap)
                except Exception:
                    pass  # Non-critical

            log.info("Worker '%s' (model=%s) added via API", name, model)
            return JSONResponse({
                "status": "created",
                "worker": {
                    "name": name,
                    "model": model,
                    "mock": mock,
                },
            }, status_code=201)

        except json.JSONDecodeError:
            return JSONResponse({"error": "Invalid JSON body"}, status_code=400)
        except Exception:
            log.exception("Error in POST /swarm/workers")
            return JSONResponse(
                {"error": "Internal error adding worker", "detail": traceback.format_exc()},
                status_code=500,
            )

    # -- DELETE /swarm/workers/{name} ----------------------------------

    @app.delete("/swarm/workers/{name}")
    def swarm_workers_remove(name: str):
        try:
            swarm: Optional[Swarm] = getattr(app.state, "swarm", None)
            if swarm is None:
                return JSONResponse(
                    {"error": "No swarm instance attached"},
                    status_code=400,
                )

            if name not in swarm.workers:
                return JSONResponse(
                    {"error": f"Worker '{name}' not found"},
                    status_code=404,
                )

            # Remove from workers dict
            del swarm.workers[name]

            # Clean up associated state — use getattr for safety
            for attr in (
                "_worker_stats", "_worker_current_task", "_personal_time_tracker",
                "_worker_last_active", "_worker_consecutive_failures",
                "_worker_completions", "_suspended_workers",
            ):
                d = getattr(swarm, attr, None)
                if isinstance(d, dict):
                    d.pop(name, None)
            booted = getattr(swarm, "_booted_workers", None)
            if isinstance(booted, set):
                booted.discard(name)

            # Unregister from coordinator
            coordinator = getattr(swarm, "coordinator", None)
            if coordinator is not None and hasattr(coordinator, "unregister"):
                try:
                    coordinator.unregister(name)
                except Exception:
                    pass

            log.info("Worker '%s' removed via API", name)
            return JSONResponse({"status": "removed", "worker": name})

        except Exception:
            log.exception("Error in DELETE /swarm/workers/%s", name)
            return JSONResponse(
                {"error": "Internal error removing worker", "detail": traceback.format_exc()},
                status_code=500,
            )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def create_swarm_app(data_dir: str = "data") -> "FastAPI":  # noqa: F821
    """Create a FastAPI application with all swarm endpoints registered.

    Raises ``ImportError`` if FastAPI is not installed.
    """
    try:
        from fastapi import FastAPI
        from fastapi.middleware.cors import CORSMiddleware
    except ImportError:
        raise ImportError(
            "FastAPI is required for the swarm server.  "
            "Install it with:  pip install fastapi uvicorn"
        )

    app = FastAPI(
        title="Hypernet Swarm",
        version="0.2.0",
        docs_url=None,
        redoc_url=None,
    )

    # CORS — allow dashboard access from any local origin during development
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.state.data_dir = data_dir
    app.state.swarm = None
    app.state.web_messenger = None
    app.state.config_path = None

    _register_routes(app)
    return app


def attach_swarm(
    app: "FastAPI",  # noqa: F821
    swarm: "Swarm",
    web_messenger: "Optional[WebMessenger]" = None,
    config_path: "Optional[str]" = None,
) -> None:
    """Wire a live :class:`Swarm` into an existing FastAPI *app*.

    Parameters
    ----------
    app:
        The FastAPI application (created via :func:`create_swarm_app` or any
        FastAPI instance that already has the routes registered).
    swarm:
        A fully-constructed ``Swarm`` object.
    web_messenger:
        Optional ``WebMessenger`` for push notifications to the dashboard.
    config_path:
        Optional filesystem path to the swarm config JSON file so that
        ``POST /swarm/config`` can persist changes.
    """
    app.state.swarm = swarm
    app.state.web_messenger = web_messenger
    app.state.config_path = config_path
    log.info(
        "Swarm attached to server — %d workers, config_path=%s",
        len(swarm.workers),
        config_path,
    )
