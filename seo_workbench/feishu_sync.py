from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

from seo_workbench import state
from seo_workbench.feishu_gateway import list_records
from seo_workbench.hexcal_blog_import import KEYWORD_FIELDS, PIPELINE_FIELDS, import_hexcal_blog
from seo_workbench_tools.files import atomic_write_text


HEXCAL_BLOG_KEYWORDS_TABLE = "blog_keywords"
HEXCAL_BLOG_PIPELINE_TABLE = "blog_pipeline"


def import_hexcal_from_feishu_gateway(
    project_dir: Path,
    *,
    profile: str,
    config_path: Path | None = None,
    include_keywords: bool = True,
    include_pipeline: bool = True,
    limit: int | None = None,
    runner: Any = subprocess.run,
) -> dict[str, Any]:
    project_name = str((state.load_state(project_dir).get("project") or {}).get("name") or "").strip().casefold()
    if project_name != "hexcal":
        raise ValueError("Feishu BLOG import is available only for the Hexcal project adapter")
    tmp = state.safe_project_path(project_dir, ".runtime/feishu")
    tmp.mkdir(parents=True, exist_ok=True)
    keywords_path = (
        _fetch_table(tmp, "keywords", profile, config_path, HEXCAL_BLOG_KEYWORDS_TABLE, list(KEYWORD_FIELDS), limit, runner)
        if include_keywords
        else None
    )
    pipeline_path = (
        _fetch_table(tmp, "pipeline", profile, config_path, HEXCAL_BLOG_PIPELINE_TABLE, list(PIPELINE_FIELDS), limit, runner)
        if include_pipeline
        else None
    )
    imported = import_hexcal_blog(project_dir, keywords_path=keywords_path, pipeline_path=pipeline_path)
    return {
        "collection_status": "ok",
        "source": "feishu-gateway",
        "profile": profile,
        "keywords_path": str(keywords_path or ""),
        "pipeline_path": str(pipeline_path or ""),
        **imported,
    }


def _fetch_table(
    output_dir: Path,
    name: str,
    profile: str,
    config_path: Path | None,
    table: str,
    field_ids: list[str],
    limit: int | None,
    runner: Any,
) -> Path:
    path = output_dir / f"{name}.json"
    rows = list_records(
        profile=profile,
        config_path=config_path,
        base="dcdb",
        table=table,
        field_ids=field_ids,
        limit=limit,
        runner=runner,
    )
    atomic_write_text(path, json.dumps(rows, ensure_ascii=False, indent=2) + "\n", mode=0o600)
    return path
