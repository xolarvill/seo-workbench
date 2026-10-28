"""Fixed local Clarity routes; reuses the Workbench background job runner."""
from __future__ import annotations

import asyncio
import json
from datetime import datetime, timedelta, timezone
from typing import Literal

from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field, SecretStr, ValidationError

from seo_workbench import clarity
from seo_workbench_tools.clarity_probe import CHANNELS, prepare, read_evidence, recording_links


class Credential(BaseModel):
    model_config = ConfigDict(extra="forbid")
    token: SecretStr
    project_id: str = Field(min_length=1, max_length=64)
    timezone: str = Field(min_length=1, max_length=100)


class Query(BaseModel):
    model_config = ConfigDict(extra="forbid")
    action: Literal["query", "recordings", "docs"]
    query: str = Field(default="", max_length=2000)
    start: str = Field(default="", max_length=40)
    end: str = Field(default="", max_length=40)
    timezone: str | None = Field(default=None, max_length=100)
    url: str | None = Field(default=None, max_length=2000)
    device: Literal["Mobile", "PC", "Tablet"] | None = None
    channel: str | None = Field(default=None, max_length=32)
    rage_click: bool = False
    dead_click: bool = False
    js_error: bool = False
    count: int = Field(default=10, ge=1, le=50)
    force: bool = False


async def body(request, model):
    try:
        raw = bytearray()
        async for chunk in request.stream():
            raw.extend(chunk)
            if len(raw) > 32768:
                raise HTTPException(413, "Clarity payload exceeds 32 KB")
        return model.model_validate(json.loads(raw))
    except (ValueError, ValidationError):
        # Pydantic error details can contain the submitted token. Never return them.
        raise HTTPException(400, "Invalid Clarity request fields") from None


def register(app, jobs, projects_root, project_resolver, require_local):
    def project(project_id, request):
        require_local(request)
        return project_resolver(project_id, projects_root)

    @app.get("/api/v1/projects/{project_id}/integrations/clarity")
    def status(project_id: str, request: Request):
        return {"integration": clarity.integration_status(project(project_id, request))}

    @app.put("/api/v1/projects/{project_id}/integrations/clarity/credentials")
    async def configure(project_id: str, request: Request):
        target = project(project_id, request)
        value = await body(request, Credential)
        try:
            result = await asyncio.to_thread(clarity.configure, target, value.token.get_secret_value(), value.project_id, value.timezone)
            return {"integration": result}
        except (ValueError, OSError):
            raise HTTPException(400, "Clarity configuration or verification failed; existing credentials were preserved") from None

    @app.post("/api/v1/projects/{project_id}/integrations/clarity/verify")
    async def verify(project_id: str, request: Request):
        target = project(project_id, request)
        try:
            return {"integration": await asyncio.to_thread(clarity.verify_connection, target)}
        except (ValueError, OSError):
            raise HTTPException(400, "Clarity verification failed; inspect connection and provider status") from None

    @app.delete("/api/v1/projects/{project_id}/integrations/clarity/credentials")
    def disconnect(project_id: str, request: Request):
        try:
            return {"integration": clarity.disconnect(project(project_id, request))}
        except (ValueError, OSError):
            raise HTTPException(400, "Clarity connection could not be removed") from None

    @app.post("/api/v1/projects/{project_id}/clarity/jobs")
    async def start(project_id: str, request: Request):
        target = project(project_id, request)
        value = await body(request, Query)
        options = value.model_dump(exclude={"action", "force", "timezone"})
        if value.channel and value.channel not in CHANNELS:
            raise HTTPException(400, "Invalid Clarity channel")
        try:
            prepare(clarity.load(target), value.action, timezone_name=value.timezone, **options)
            command = ["clarity", value.action, "--json"]
            for name in ("query", "start", "end", "timezone", "url", "device", "channel"):
                field = getattr(value, name)
                allowed = name == "query" and value.action in ("query", "docs") or name in ("start", "end") and value.action in ("query", "recordings") or name == "timezone" and value.action == "query" or name in ("url", "device", "channel") and value.action == "recordings"
                if field and allowed:
                    command.extend([f"--{name}", field])
            if value.action == "recordings":
                command.extend(["--count", str(value.count)])
                for name in ("rage_click", "dead_click", "js_error"):
                    if getattr(value, name):
                        command.append("--" + name.replace("_", "-"))
            if value.force:
                command.append("--force")
            return {"job": jobs.start_command(project_id, f"clarity-{value.action}", tuple(command))}
        except ValueError:
            raise HTTPException(400, "Clarity query is invalid or project is not configured") from None
        except RuntimeError:
            raise HTTPException(409, "This project already has a running task") from None

    @app.get("/api/v1/projects/{project_id}/clarity/evidence/{kind}")
    def evidence(project_id: str, kind: str, request: Request):
        try:
            return JSONResponse({"evidence": read_evidence(project(project_id, request), kind)}, headers={"Cache-Control": "no-store"})
        except (ValueError, OSError):
            raise HTTPException(400, "Clarity evidence is unavailable") from None

    @app.get("/api/v1/projects/{project_id}/clarity/recording-links")
    def links(project_id: str, request: Request):
        target = project(project_id, request)
        value = jobs.clarity_links.get(project_id)
        try:
            if not value or value["generation"] != clarity.load(target)["generation"] or datetime.fromisoformat(value["created_at"]) < datetime.now(timezone.utc) - timedelta(minutes=15):
                jobs.clarity_links.pop(project_id, None)
                return JSONResponse({"links": []}, headers={"Cache-Control": "no-store"})
            return JSONResponse({"links": recording_links(value["links"])}, headers={"Cache-Control": "no-store"})
        except (ValueError, KeyError):
            return JSONResponse({"links": []}, headers={"Cache-Control": "no-store"})
