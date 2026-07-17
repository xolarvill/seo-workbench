from __future__ import annotations

import asyncio
import hashlib
import json
import os
import re
import secrets
import signal
import sys
import threading
import webbrowser
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, AsyncIterator
from urllib.parse import urlencode, urlparse

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse, StreamingResponse
from pydantic import BaseModel, Field
from watchfiles import Change, awatch

from seo_workbench import state
from seo_workbench.locks import project_lock
from seo_workbench.workflow import DEFAULT_WORKFLOW, load_workflow, next_contract
from seo_workbench_tools.files import atomic_write_text


UI_PROTOCOL_VERSION = "1"
COOKIE_NAME = "seo_workbench_session"
DEFAULT_PORT = 8765
DEFAULT_RUNTIME_DIR = state.ROOT / ".runtime" / "ui"
DEFAULT_FRONTEND_DIR = state.ROOT / "ui" / "dist"
MARKDOWN_ROOTS = {"context", "strategy", "content", "audits"}
MARKDOWN_SUFFIXES = {".md", ".markdown"}
MAX_MARKDOWN_BYTES = 2 * 1024 * 1024
WATCHED_SUFFIXES = {".json", ".md", ".markdown", ".html", ".png", ".webp"}


class FileUpdate(BaseModel):
    content: str = Field(max_length=MAX_MARKDOWN_BYTES)
    base_revision: str | None = None


class ActionRequest(BaseModel):
    action: str


class WorkflowActionRequest(BaseModel):
    action: str
    step_id: str | None = None


ACTION_COMMANDS: dict[str, tuple[str, ...]] = {
    "evidence": ("evidence", "--json"),
    "technology": ("technology", "--json"),
    "performance": ("performance", "--json"),
    "crux": ("crux", "--json"),
    "gsc": ("gsc", "collect", "--json"),
    "audit-diff": ("audit-diff", "--json"),
}
MAX_JOB_OUTPUT = 64 * 1024
SENSITIVE_OUTPUT = re.compile(r'(?i)("?(?:token|api[_-]?key|authorization|client_secret)"?\s*[:=]\s*)[^\s,}]+')


def _safe_job_output(value: str) -> str:
    redacted = SENSITIVE_OUTPUT.sub(r"\1[REDACTED]", value).encode("utf-8")
    bounded = redacted[-MAX_JOB_OUTPUT:]
    while bounded and bounded[0] & 0xC0 == 0x80:
        bounded = bounded[1:]
    return bounded.decode("utf-8", errors="replace")


class EventHub:
    def __init__(self) -> None:
        self._subscribers: set[asyncio.Queue[dict[str, Any]]] = set()

    def subscribe(self) -> asyncio.Queue[dict[str, Any]]:
        queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue(maxsize=100)
        self._subscribers.add(queue)
        return queue

    def unsubscribe(self, queue: asyncio.Queue[dict[str, Any]]) -> None:
        self._subscribers.discard(queue)

    def publish(self, event: dict[str, Any]) -> None:
        for queue in tuple(self._subscribers):
            if queue.full():
                try:
                    queue.get_nowait()
                except asyncio.QueueEmpty:
                    pass
            queue.put_nowait(event)


class JobManager:
    def __init__(self, hub: EventHub) -> None:
        self.hub = hub
        self.jobs: dict[str, dict[str, Any]] = {}
        self._tasks: dict[str, asyncio.Task[None]] = {}
        self._running_projects: set[str] = set()
        self._processes: dict[str, asyncio.subprocess.Process] = {}

    def list(self, project_id: str) -> list[dict[str, Any]]:
        return sorted(
            (job.copy() for job in self.jobs.values() if job["project_id"] == project_id),
            key=lambda job: job["created_at"],
            reverse=True,
        )[:20]

    def start(self, project_id: str, action: str) -> dict[str, Any]:
        if action not in ACTION_COMMANDS:
            raise ValueError(f"unsupported UI action: {action}")
        if project_id in self._running_projects:
            raise RuntimeError("this project already has a running task")
        job_id = secrets.token_hex(8)
        job = {
            "id": job_id,
            "project_id": project_id,
            "action": action,
            "status": "queued",
            "created_at": _timestamp(),
            "started_at": None,
            "finished_at": None,
            "exit_code": None,
            "output": "",
        }
        self.jobs[job_id] = job
        self._running_projects.add(project_id)
        self._tasks[job_id] = asyncio.create_task(self._run(job_id))
        return job.copy()

    async def _run(self, job_id: str) -> None:
        job = self.jobs[job_id]
        try:
            job.update(status="running", started_at=_timestamp())
            self._publish("job.started", job)
            command = [sys.executable, "-m", "seo_workbench", "--project", job["project_id"], *ACTION_COMMANDS[job["action"]]]
            process = await asyncio.create_subprocess_exec(
                *command,
                cwd=str(state.ROOT),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,
                env={**os.environ, "PYTHONUNBUFFERED": "1"},
                start_new_session=os.name == "posix",
            )
            self._processes[job_id] = process
            output, _ = await process.communicate()
            job["exit_code"] = process.returncode
            decoded = output.decode("utf-8", errors="replace")
            job["output"] = _safe_job_output(decoded)
            job["status"] = "succeeded" if process.returncode == 0 else "failed"
        except asyncio.CancelledError:
            process = self._processes.get(job_id)
            if process and process.returncode is None:
                if os.name == "posix":
                    os.killpg(process.pid, signal.SIGTERM)
                else:
                    process.terminate()
                try:
                    await asyncio.wait_for(process.wait(), timeout=5)
                except TimeoutError:
                    if os.name == "posix":
                        os.killpg(process.pid, signal.SIGKILL)
                    else:
                        process.kill()
                    await process.wait()
            job["status"] = "cancelled"
            raise
        except OSError as exc:
            job.update(status="failed", output=str(exc), exit_code=None)
        finally:
            job["finished_at"] = _timestamp()
            self._running_projects.discard(job["project_id"])
            self._processes.pop(job_id, None)
            self._publish("job.finished", job)
            self._tasks.pop(job_id, None)

    def _publish(self, event_type: str, job: dict[str, Any]) -> None:
        self.hub.publish({"type": event_type, "project_id": job["project_id"], "job": job.copy(), "at": _timestamp()})

    async def shutdown(self) -> None:
        tasks = list(self._tasks.values())
        for task in tasks:
            if not task.done():
                task.cancel()
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)


def _timestamp() -> str:
    return datetime.now(timezone.utc).isoformat()


def _revision(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def _secure_runtime_dir(path: Path) -> None:
    if path.is_symlink():
        raise ValueError(f"UI runtime directory cannot be a symlink: {path}")
    path.mkdir(parents=True, exist_ok=True)
    path.chmod(0o700)


def _project(project_id: str, projects_root: Path) -> Path:
    try:
        project_dir = state.project_dir_from_id(project_id, projects_root)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if not state.state_path(project_dir).is_file():
        raise HTTPException(status_code=404, detail=f"project not found: {project_id}")
    return project_dir


def _markdown_path(project_dir: Path, relative_path: str) -> Path:
    relative = Path(relative_path)
    if not relative.parts or relative.parts[0] not in MARKDOWN_ROOTS:
        raise HTTPException(status_code=400, detail="Markdown path is outside an editable project area")
    if any(part.startswith(".") for part in relative.parts):
        raise HTTPException(status_code=400, detail="hidden project paths are not editable")
    if relative.suffix.lower() not in MARKDOWN_SUFFIXES:
        raise HTTPException(status_code=400, detail="only Markdown files are editable")
    try:
        return state.safe_project_path(project_dir, relative)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


def _markdown_files(project_dir: Path) -> list[dict[str, Any]]:
    files: list[dict[str, Any]] = []
    for root_name in sorted(MARKDOWN_ROOTS):
        root = state.safe_project_path(project_dir, root_name)
        if not root.is_dir() or root.is_symlink():
            continue
        for directory, names, filenames in os.walk(root, followlinks=False):
            names[:] = sorted(name for name in names if not name.startswith(".") and not (Path(directory) / name).is_symlink())
            for filename in sorted(filenames):
                path = Path(directory) / filename
                if filename.startswith(".") or path.is_symlink() or path.suffix.lower() not in MARKDOWN_SUFFIXES:
                    continue
                stat = path.stat()
                files.append(
                    {
                        "path": path.relative_to(project_dir).as_posix(),
                        "name": path.name,
                        "size": stat.st_size,
                        "modified_at": datetime.fromtimestamp(stat.st_mtime, timezone.utc).isoformat(),
                    }
                )
    return sorted(files, key=lambda item: item["path"])


def _load_optional_json(project_dir: Path, relative_path: str) -> dict[str, Any] | None:
    try:
        path = state.safe_project_path(project_dir, relative_path)
    except ValueError:
        return None
    if not path.is_file() or path.is_symlink():
        return None
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return value if isinstance(value, dict) else None


def _evidence_summary(project_dir: Path, runtime_dir: Path) -> dict[str, Any]:
    raw = _load_optional_json(project_dir, "audits/raw/latest.json")
    technology = _load_optional_json(project_dir, "audits/technology/latest.json")
    performance = _load_optional_json(project_dir, "audits/performance/latest.json")
    crux = _load_optional_json(project_dir, "audits/crux/latest.json")
    gsc = _load_optional_json(project_dir, "audits/gsc/latest.json")
    diff = _load_optional_json(project_dir, "audits/diffs/latest.json")

    def status(report: dict[str, Any] | None, missing: str = "missing") -> str:
        return str(report.get("collection_status", "ready")) if report else missing

    crux_key = bool(os.environ.get("SEO_WORKBENCH_CRUX_API_KEY")) or (runtime_dir.parent / "google/crux-api-key").is_file()
    binding = project_dir / ".runtime/integrations/google.json"
    aggregate = performance.get("aggregate", {}) if performance else {}
    metrics = aggregate.get("metrics", {}) if isinstance(aggregate, dict) else {}
    architecture = technology.get("architecture_analysis", {}) if technology else {}

    return {
        "items": [
            {"id": "raw", "label": "Raw", "status": status(raw)},
            {"id": "technology", "label": "Technology", "status": status(technology)},
            {"id": "performance", "label": "Lighthouse", "status": status(performance)},
            {"id": "crux", "label": "CrUX", "status": status(crux, "needs_key" if not crux_key else "missing")},
            {"id": "gsc", "label": "GSC", "status": status(gsc, "not_bound" if not binding.is_file() else "missing")},
            {"id": "diff", "label": "Diff", "status": status(diff)},
        ],
        "performance": {
            "score": (aggregate.get("performance_score") or {}).get("median") if isinstance(aggregate, dict) else None,
            "high_variance": aggregate.get("high_variance") if isinstance(aggregate, dict) else None,
            "metrics": {
                "lcp": (metrics.get("largest-contentful-paint") or {}).get("median"),
                "tbt": (metrics.get("total-blocking-time") or {}).get("median"),
                "cls": (metrics.get("cumulative-layout-shift") or {}).get("median"),
            },
        },
        "technology": architecture,
        "diff": (diff or {}).get("summary", {}),
    }


def _workspace(project_id: str, project_dir: Path, runtime_dir: Path) -> dict[str, Any]:
    data = state.load_state(project_dir)
    phase, step = state.current_step(data)
    contract = next_contract(load_workflow(DEFAULT_WORKFLOW), phase, step, project_dir) if step else None
    files = _markdown_files(project_dir)
    recent = sorted(files, key=lambda item: item["modified_at"], reverse=True)[:8]
    return {
        "project_id": project_id,
        "project": data.get("project", {}),
        "phase": phase,
        "step": step,
        "next": contract,
        "phase_order": data.get("phaseOrder", []),
        "phases": data.get("phases", {}),
        "evidence": _evidence_summary(project_dir, runtime_dir),
        "recent_files": recent,
    }


async def _watch_projects(projects_root: Path, hub: EventHub, stop_event: asyncio.Event) -> None:
    if not projects_root.is_dir() or projects_root.is_symlink():
        return
    async for changes in awatch(projects_root, recursive=True, stop_event=stop_event):
        for change, raw_path in changes:
            path = Path(raw_path)
            if path.suffix.lower() not in WATCHED_SUFFIXES or path.name.startswith("."):
                continue
            try:
                relative = path.resolve(strict=False).relative_to(projects_root.resolve(strict=False))
            except ValueError:
                continue
            if len(relative.parts) < 2:
                continue
            hub.publish(
                {
                    "type": "file.changed",
                    "project_id": relative.parts[0],
                    "path": Path(*relative.parts[1:]).as_posix(),
                    "change": Change(change).name.lower(),
                    "at": _timestamp(),
                }
            )


def create_app(
    *,
    token: str | None = None,
    projects_root: Path = state.PROJECTS_ROOT,
    runtime_dir: Path = DEFAULT_RUNTIME_DIR,
    frontend_dir: Path | None = DEFAULT_FRONTEND_DIR,
    watch_files: bool = True,
) -> FastAPI:
    session_token = token or secrets.token_urlsafe(32)
    hub = EventHub()
    jobs = JobManager(hub)
    stop_event = asyncio.Event()

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        task: asyncio.Task[None] | None = None
        if watch_files:
            task = asyncio.create_task(_watch_projects(projects_root, hub, stop_event))
        try:
            yield
        finally:
            stop_event.set()
            await jobs.shutdown()
            if task:
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass

    app = FastAPI(title="SEO Workbench UI", version=UI_PROTOCOL_VERSION, lifespan=lifespan)
    app.state.session_token = session_token
    app.state.event_hub = hub
    app.state.job_manager = jobs

    @app.middleware("http")
    async def local_session(request: Request, call_next):
        hostname = request.url.hostname or ""
        if hostname not in {"127.0.0.1", "localhost", "testserver"}:
            return JSONResponse({"detail": "SEO Workbench UI only accepts local requests"}, status_code=403)
        if request.url.path == "/api/v1/health":
            return await call_next(request)
        supplied = request.query_params.get("token")
        if request.method == "GET" and request.url.path == "/" and supplied == session_token:
            remaining = [(key, value) for key, value in request.query_params.multi_items() if key != "token"]
            target = f"/?{urlencode(remaining)}" if remaining else "/"
            response = RedirectResponse(target, status_code=303)
            response.set_cookie(COOKIE_NAME, session_token, httponly=True, samesite="strict", secure=False)
            return response
        if request.cookies.get(COOKIE_NAME) != session_token:
            if request.url.path.startswith("/api/"):
                return JSONResponse({"detail": "local UI session required"}, status_code=401)
            return HTMLResponse("Open this workbench with ./seo ui.", status_code=401)
        if request.method not in {"GET", "HEAD", "OPTIONS"}:
            origin = request.headers.get("origin")
            if origin and (urlparse(origin).hostname or "") not in {"127.0.0.1", "localhost", "testserver"}:
                return JSONResponse({"detail": "cross-origin mutations are blocked"}, status_code=403)
        return await call_next(request)

    @app.get("/api/v1/health")
    def health() -> dict[str, Any]:
        return {"ok": True, "protocol_version": UI_PROTOCOL_VERSION, "projects_root": str(projects_root)}

    @app.get("/api/v1/projects")
    def projects() -> dict[str, Any]:
        found = state.discover_projects(projects_root)
        return {"ok": True, "count": len(found), "projects": found}

    @app.get("/api/v1/projects/{project_id}/workspace")
    def workspace(project_id: str) -> dict[str, Any]:
        project_dir = _project(project_id, projects_root)
        return {"ok": True, "workspace": _workspace(project_id, project_dir, runtime_dir)}

    @app.get("/api/v1/projects/{project_id}/files")
    def files(project_id: str) -> dict[str, Any]:
        project_dir = _project(project_id, projects_root)
        items = _markdown_files(project_dir)
        return {"ok": True, "count": len(items), "files": items}

    @app.get("/api/v1/projects/{project_id}/files/{relative_path:path}")
    def read_file(project_id: str, relative_path: str) -> dict[str, Any]:
        project_dir = _project(project_id, projects_root)
        path = _markdown_path(project_dir, relative_path)
        if not path.is_file() or path.is_symlink():
            raise HTTPException(status_code=404, detail="Markdown file not found")
        content = path.read_bytes()
        if len(content) > MAX_MARKDOWN_BYTES:
            raise HTTPException(status_code=413, detail="Markdown file is too large for the editor")
        return {
            "ok": True,
            "file": {
                "path": relative_path,
                "content": content.decode("utf-8"),
                "revision": _revision(content),
                "modified_at": datetime.fromtimestamp(path.stat().st_mtime, timezone.utc).isoformat(),
            },
        }

    @app.put("/api/v1/projects/{project_id}/files/{relative_path:path}")
    def write_file(project_id: str, relative_path: str, update: FileUpdate) -> dict[str, Any]:
        project_dir = _project(project_id, projects_root)
        path = _markdown_path(project_dir, relative_path)
        saved = update.content.encode("utf-8")
        if len(saved) > MAX_MARKDOWN_BYTES:
            raise HTTPException(status_code=413, detail="Markdown file is too large for the editor")
        lock_root = runtime_dir.parent / "locks"
        with project_lock(project_dir, lock_root=lock_root):
            current = path.read_bytes() if path.is_file() and not path.is_symlink() else None
            current_revision = _revision(current) if current is not None else None
            if current_revision != update.base_revision:
                raise HTTPException(
                    status_code=409,
                    detail={"code": "revision_conflict", "current_revision": current_revision},
                )
            atomic_write_text(path, update.content)
        hub.publish(
            {
                "type": "file.saved",
                "project_id": project_id,
                "path": relative_path,
                "revision": _revision(saved),
                "at": _timestamp(),
            }
        )
        return {
            "ok": True,
            "file": {"path": relative_path, "revision": _revision(saved), "modified_at": _timestamp()},
        }

    @app.get("/api/v1/projects/{project_id}/jobs")
    def list_jobs(project_id: str) -> dict[str, Any]:
        _project(project_id, projects_root)
        items = jobs.list(project_id)
        return {"ok": True, "count": len(items), "jobs": items}

    @app.post("/api/v1/projects/{project_id}/actions", status_code=202)
    async def start_action(project_id: str, request: ActionRequest) -> dict[str, Any]:
        _project(project_id, projects_root)
        try:
            job = jobs.start(project_id, request.action)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except RuntimeError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        return {"ok": True, "job": job}

    @app.post("/api/v1/projects/{project_id}/workflow")
    def update_workflow(project_id: str, request: WorkflowActionRequest) -> dict[str, Any]:
        project_dir = _project(project_id, projects_root)
        if request.action not in {"start", "done", "skip", "reset"}:
            raise HTTPException(status_code=400, detail=f"unsupported workflow action: {request.action}")
        try:
            phase, step_id = state.mutate_state(
                project_dir,
                lambda data: state.update_step(data, request.action, request.step_id),
            )
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        hub.publish({"type": "workflow.updated", "project_id": project_id, "phase": phase, "step_id": step_id, "at": _timestamp()})
        return {"ok": True, "action": request.action, "phase": phase, "step_id": step_id}

    @app.get("/api/v1/events")
    async def events(request: Request) -> StreamingResponse:
        queue = hub.subscribe()

        async def stream() -> AsyncIterator[str]:
            try:
                yield f"event: connected\ndata: {json.dumps({'type': 'connected', 'at': _timestamp()})}\n\n"
                while not await request.is_disconnected():
                    try:
                        event = await asyncio.wait_for(queue.get(), timeout=15)
                    except TimeoutError:
                        yield ": keepalive\n\n"
                        continue
                    yield f"event: {event.get('type', 'message')}\ndata: {json.dumps(event, ensure_ascii=False)}\n\n"
            finally:
                hub.unsubscribe(queue)

        return StreamingResponse(stream(), media_type="text/event-stream", headers={"Cache-Control": "no-cache"})

    if frontend_dir and (frontend_dir / "index.html").is_file():
        if hasattr(app, "frontend"):
            app.frontend("/", directory=str(frontend_dir), fallback="index.html")
        else:
            from fastapi.staticfiles import StaticFiles

            app.mount("/", StaticFiles(directory=frontend_dir, html=True), name="ui")
    else:
        @app.get("/", response_class=HTMLResponse)
        def missing_frontend() -> str:
            return "<main><h1>SEO Workbench UI</h1><p>Frontend assets are not built yet.</p></main>"

    return app


def _write_session(runtime_dir: Path, port: int, token_path: Path) -> Path:
    _secure_runtime_dir(runtime_dir)
    session_path = runtime_dir / "session.json"
    payload = {
        "protocol_version": UI_PROTOCOL_VERSION,
        "pid": os.getpid(),
        "base_url": f"http://127.0.0.1:{port}",
        "token_path": str(token_path),
        "started_at": _timestamp(),
    }
    atomic_write_text(session_path, json.dumps(payload, indent=2) + "\n", mode=0o600)
    return session_path


def run_ui(*, port: int = DEFAULT_PORT, open_browser: bool = True, initial_project: str | None = None) -> int:
    if not 1 <= port <= 65535:
        raise ValueError("UI port must be between 1 and 65535")
    import uvicorn

    _secure_runtime_dir(DEFAULT_RUNTIME_DIR)
    token = secrets.token_urlsafe(32)
    token_path = DEFAULT_RUNTIME_DIR / "token"
    atomic_write_text(token_path, token + "\n", mode=0o600)
    session_path = _write_session(DEFAULT_RUNTIME_DIR, port, token_path)
    app = create_app(token=token)
    url = f"http://127.0.0.1:{port}/?token={token}"
    if initial_project:
        url += f"&project={initial_project}"
    print(f"SEO Workbench UI: http://127.0.0.1:{port}")
    if open_browser:
        timer = threading.Timer(0.8, webbrowser.open, args=(url,))
        timer.daemon = True
        timer.start()
    try:
        # Access logs are disabled because the one-time bootstrap token is carried
        # in the initial local URL before middleware replaces it with a cookie.
        uvicorn.run(app, host="127.0.0.1", port=port, log_level="info", access_log=False)
    finally:
        try:
            current = json.loads(session_path.read_text(encoding="utf-8")) if session_path.is_file() else {}
        except (OSError, json.JSONDecodeError):
            current = {}
        if current.get("pid") == os.getpid():
            session_path.unlink(missing_ok=True)
            token_path.unlink(missing_ok=True)
    return 0
