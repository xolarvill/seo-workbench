import json
from pathlib import Path

from seo_workbench import state
from seo_workbench.cli import main
from seo_workbench.content_briefs import export_revision_brief, export_writing_brief


def test_export_writing_brief_uses_pipeline_context_and_links(tmp_path: Path) -> None:
    project_dir = tmp_path / "project"
    state.init_state("shopify", "Hexcal", "https://example.com", project_dir=project_dir)
    (project_dir / "content/blog-pipeline.jsonl").write_text(
        "\n".join(
            [
                json.dumps(
                    {
                        "id": "rec1",
                        "status": "ready_to_write",
                        "cluster_name": "Desk Setup",
                        "representative_keyword": "desk setup",
                        "long_tail_keywords": ["minimal desk setup", "small desk setup"],
                        "intent": "informational",
                        "product_anchor": ["studio"],
                        "cluster_rationale": "Users need setup guidance.",
                        "feature_image_refs": ["recFeature"],
                        "inline_image_refs": ["recInline"],
                    }
                ),
                json.dumps({"id": "rec2", "title": "Cable Guide", "live_url": "https://example.com/blogs/articles/cable-guide"}),
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    (project_dir / "strategy/briefs").mkdir(parents=True, exist_ok=True)
    (project_dir / "context").mkdir(parents=True, exist_ok=True)
    (project_dir / "context/brand-voice.md").write_text("Brand", encoding="utf-8")
    (project_dir / "context/blog-style-guide.md").write_text("Blog", encoding="utf-8")
    (project_dir / "context/product-specs.md").write_text("Specs", encoding="utf-8")
    (project_dir / "strategy/briefs/rec1-serp.json").write_text(
        json.dumps(
            {
                "competitors": [
                    {
                        "title": "Competitor Angle",
                        "url": "https://competitor.example/post",
                        "snippet": "A competing SERP result.",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    report, path = export_writing_brief(project_dir, "rec1")

    text = path.read_text(encoding="utf-8")
    assert report["collection_status"] == "ok"
    assert report["product_link_candidates"] == 3
    assert report["serp_competitors"] == 1
    assert "Desk Setup" in text
    assert "Target keyword: desk setup" in text
    assert "Representative: desk setup" in text
    assert "Long tail: minimal desk setup, small desk setup" in text
    assert "content serp-competitors rec1" in text
    assert "[Competitor Angle](https://competitor.example/post)" in text
    assert "content asset-candidates rec1" in text
    assert "context/brand-voice.md" in text
    assert "context/blog-style-guide.md" in text
    assert "context/product-specs.md" in text
    assert "[Hexcal Studio](https://example.com/products/hexcal-studio)" in text
    assert "[Cable Guide](https://example.com/blogs/articles/cable-guide)" in text
    assert "Feature image record IDs: recFeature" in text
    assert '<img data-rid="rec..." alt="...">' in text


def test_content_brief_cli_outputs_json(tmp_path: Path, capsys) -> None:
    project_dir = tmp_path / "project"
    state.init_state("shopify", "Store", "https://example.com", project_dir=project_dir)
    (project_dir / "content/blog-pipeline.jsonl").write_text(json.dumps({"id": "rec1", "title": "Brief"}) + "\n", encoding="utf-8")

    assert main(["--project-dir", str(project_dir), "content", "brief", "rec1", "--json"]) == 0
    payload = json.loads(capsys.readouterr().out)

    assert payload["ok"] is True
    assert Path(payload["path"]).name == "rec1.md"


def test_export_revision_brief_includes_edit_notes_and_current_draft(tmp_path: Path) -> None:
    project_dir = tmp_path / "project"
    state.init_state("shopify", "Store", "https://example.com", project_dir=project_dir)
    (project_dir / "content/blog-pipeline.jsonl").write_text(
        "\n".join(
            [
                json.dumps(
                    {
                        "id": "rec1",
                        "status": "revision_requested",
                        "title": "Needs Revision",
                        "edit_notes": "Tighten intro and swap weak claim.",
                        "draft_html": "<p>Old draft</p>",
                    }
                ),
                json.dumps({"id": "rec2", "title": "Live", "live_url": "https://example.com/blogs/articles/live"}),
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    (project_dir / "context").mkdir(parents=True, exist_ok=True)
    (project_dir / "context/brand-voice.md").write_text("Brand", encoding="utf-8")
    (project_dir / "context/blog-style-guide.md").write_text("Blog", encoding="utf-8")

    report, path = export_revision_brief(project_dir, "rec1")

    text = path.read_text(encoding="utf-8")
    assert report["collection_status"] == "ok"
    assert path.name == "rec1-revision.md"
    assert "Tighten intro" in text
    assert "<p>Old draft</p>" in text
    assert "context/brand-voice.md" in text
    assert "context/blog-style-guide.md" in text
    assert "[Live](https://example.com/blogs/articles/live)" in text


def test_content_revise_brief_cli_outputs_json(tmp_path: Path, capsys) -> None:
    project_dir = tmp_path / "project"
    state.init_state("shopify", "Store", "https://example.com", project_dir=project_dir)
    (project_dir / "content/blog-pipeline.jsonl").write_text(
        json.dumps({"id": "rec1", "status": "revision_requested", "edit_notes": "Fix it"}) + "\n",
        encoding="utf-8",
    )

    assert main(["--project-dir", str(project_dir), "content", "revise-brief", "rec1", "--json"]) == 0
    payload = json.loads(capsys.readouterr().out)

    assert payload["ok"] is True
    assert Path(payload["path"]).name == "rec1-revision.md"
