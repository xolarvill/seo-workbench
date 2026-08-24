import json
import subprocess
from pathlib import Path

import pytest

from seo_workbench import state
from seo_workbench.cli import main
from seo_workbench.feishu_sync import import_hexcal_from_feishu_gateway
from seo_workbench.hexcal_blog_import import KEYWORD_FIELDS, PIPELINE_FIELDS


FEISHU_CONFIG = Path(__file__).resolve().parents[1] / "templates/hexcal-feishu-profile.json"


def test_import_hexcal_from_feishu_gateway_reuses_existing_importer(tmp_path: Path) -> None:
    project_dir = tmp_path / "project"
    state.init_state("shopify", "Hexcal", "https://www.hexcal.com", project_dir=project_dir)
    calls = []

    def runner(cmd, **kwargs):
        calls.append((cmd, kwargs))
        if len(calls) == 1:
            rows = [{"_record_id": "kw1", KEYWORD_FIELDS["keyword"]: "desk setup", KEYWORD_FIELDS["source"]: "gsc"}]
        else:
            rows = [{"_record_id": "rec1", PIPELINE_FIELDS["status"]: "approved", PIPELINE_FIELDS["title"]: "Blog draft"}]
        return subprocess.CompletedProcess(cmd, 0, stdout=json.dumps(rows), stderr="")

    report = import_hexcal_from_feishu_gateway(
        project_dir,
        profile="hexcal-seo",
        config_path=FEISHU_CONFIG,
        runner=runner,
    )

    assert report["keywords_imported"] == 1
    assert report["pipeline_imported"] == 1
    assert len(calls) == 2
    assert calls[0][0][:3] == ["lark-cli", "--profile", "hexcal-seo"]
    assert calls[0][0].count("--field-id") == len(KEYWORD_FIELDS)
    assert calls[1][0].count("--field-id") == len(PIPELINE_FIELDS)
    assert state.load_state(project_dir)["contentQueue"][0]["status"] == "approved"
    assert (project_dir / ".runtime/feishu/keywords.json").is_file()
    assert (project_dir / "strategy/keyword-pool.jsonl").is_file()


def test_content_import_feishu_rejects_conflicting_flags(tmp_path: Path) -> None:
    project_dir = tmp_path / "project"
    state.init_state("shopify", "Hexcal", "https://www.hexcal.com", project_dir=project_dir)

    assert main(["--project-dir", str(project_dir), "content", "import-feishu", "--profile", "hexcal-seo", "--keywords-only", "--pipeline-only", "--json"]) == 1


def test_import_feishu_rejects_non_hexcal_projects(tmp_path: Path) -> None:
    project_dir = tmp_path / "project"
    state.init_state("shopify", "Store", "https://example.com", project_dir=project_dir)

    with pytest.raises(ValueError, match="Hexcal project adapter"):
        import_hexcal_from_feishu_gateway(project_dir, profile="hexcal-seo", config_path=FEISHU_CONFIG)
