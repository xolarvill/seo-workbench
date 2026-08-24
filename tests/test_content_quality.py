import json
from pathlib import Path

from seo_workbench import state
from seo_workbench.cli import main
from seo_workbench.content_quality import (
    accurate_word_count,
    extract_faq,
    scrub_ai_signatures,
    spec_provenance_warnings,
)


def test_scrubber_removes_ai_watermarks_dashes_and_cliches() -> None:
    clean, stats = scrub_ai_signatures("<p>In today's world​, teams seamlessly use trays — fast.</p>")

    assert "today" not in clean.lower()
    assert "smoothly" in clean
    assert "—" not in clean
    assert stats["watermarks"] == 1
    assert stats["em_dashes"] == 1
    assert stats["cliches"] >= 2


def test_extract_faq_stops_at_next_h2() -> None:
    html = "<h2>FAQ</h2><h3>Q?</h3><p>A.</p><h2>Other</h2><h3>Not FAQ?</h3><p>No.</p>"

    assert extract_faq(html) == [{"question": "Q?", "answer": "A."}]
    assert accurate_word_count("<p>Hello <strong>world</strong>.</p>") == 2


def test_spec_provenance_flags_hexcal_number_tokens_without_specs() -> None:
    warnings = spec_provenance_warnings(
        "<p>Hexcal supports 1,440W output.</p>",
        set(),
        have_specs=False,
        brand_terms=("hexcal",),
    )

    assert warnings == ["1440w"]


def test_content_qc_cli_writes_audit_report(tmp_path: Path, capsys) -> None:
    project_dir = tmp_path / "project"
    state.init_state("shopify", "Hexcal", "https://www.hexcal.com", project_dir=project_dir)
    (project_dir / "content/blog-pipeline.jsonl").write_text(
        json.dumps(
            {
                "id": "rec1",
                "status": "review",
                "title": "Small Desk Setup",
                "target_keyword": "small desk setup",
                "draft_html": (
                    "<h1>Small desk setup</h1>"
                    "<p>In today's world​, Hexcal supports 1,440W output.</p>"
                    "<h2>FAQ</h2><h3>What fits?</h3><p>A compact desk.</p>"
                ),
            },
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )

    assert main(["--project-dir", str(project_dir), "content", "qc", "rec1", "--json"]) == 0
    payload = json.loads(capsys.readouterr().out)
    report_path = Path(payload["path"])

    assert payload["ok"] is True
    assert payload["schemas"]["faq_qa_count"] == 1
    assert any(warning["code"] == "spec_provenance" for warning in payload["warnings"])
    assert report_path.exists()


def test_content_qc_uses_project_product_specs_whitelist(tmp_path: Path, capsys) -> None:
    project_dir = tmp_path / "project"
    state.init_state("shopify", "Hexcal", "https://www.hexcal.com", project_dir=project_dir)
    (project_dir / "context/product-specs.md").write_text("Hexcal Studio output: 1,440W\n", encoding="utf-8")
    (project_dir / "content/blog-pipeline.jsonl").write_text(
        json.dumps({"id": "rec1", "status": "review", "title": "Specs", "draft_html": "<p>Hexcal supports 1,440W output.</p>"})
        + "\n",
        encoding="utf-8",
    )

    assert main(["--project-dir", str(project_dir), "content", "qc", "rec1", "--json"]) == 0
    payload = json.loads(capsys.readouterr().out)

    assert not any(warning["code"] == "spec_provenance" for warning in payload["warnings"])
