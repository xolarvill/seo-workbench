import json
from datetime import datetime, timezone
from pathlib import Path

from seo_workbench import state
from seo_workbench.cli import main
from seo_workbench.content_clusters import export_cluster_brief, import_clusters


def test_export_cluster_brief_reads_pending_keywords_and_existing_topics(tmp_path: Path) -> None:
    project_dir = tmp_path / "project"
    state.init_state("shopify", "Hexcal", "https://www.hexcal.com", project_dir=project_dir)
    (project_dir / "strategy/keyword-pool.jsonl").write_text(
        "\n".join(
            [
                json.dumps({"keyword": "desk setup", "priority_score": 80}),
                json.dumps({"keyword": "old topic", "priority_score": 90, "cluster_ref": "old"}),
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    (project_dir / "content/blog-pipeline.jsonl").write_text(json.dumps({"id": "old", "cluster_name": "Existing Topic", "status": "approved"}) + "\n", encoding="utf-8")

    report, path = export_cluster_brief(project_dir, max_keywords=10, now=datetime(2026, 7, 29, tzinfo=timezone.utc))
    payload = json.loads(path.read_text(encoding="utf-8"))

    assert report["keyword_count"] == 1
    assert payload["keywords"][0]["keyword"] == "desk setup"
    assert payload["already_planned_or_published_topics"] == ["Existing Topic"]


def test_import_clusters_writes_pipeline_queue_and_keyword_backlinks(tmp_path: Path) -> None:
    project_dir = tmp_path / "project"
    state.init_state("shopify", "Hexcal", "https://www.hexcal.com", project_dir=project_dir)
    (project_dir / "strategy/keyword-pool.jsonl").write_text(
        json.dumps({"keyword": "desk setup", "source": "ads"}) + "\n",
        encoding="utf-8",
    )
    clusters = tmp_path / "clusters.json"
    clusters.write_text(
        json.dumps(
            {
                "clusters": [
                    {
                        "cluster_name": "Desk Setup Guide",
                        "representative_kw": "desk setup",
                        "member_keywords": ["desk setup"],
                        "intent": "informational",
                        "business_fit": 4,
                        "rationale": "Good fit.",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    report, path = import_clusters(project_dir, clusters, now=datetime(2026, 7, 29, tzinfo=timezone.utc))

    assert report["cluster_count"] == 1
    assert report["backlinked_keywords"] == 1
    assert path.name.endswith("-content-cluster-import.json")
    record = json.loads((project_dir / "content/blog-pipeline.jsonl").read_text(encoding="utf-8").splitlines()[0])
    assert record["status"] == "planned"
    assert record["id"] == "desk-setup-guide"
    item = state.load_state(project_dir)["contentQueue"][0]
    assert item["status"] == "planned"
    keyword = json.loads((project_dir / "strategy/keyword-pool.jsonl").read_text(encoding="utf-8").splitlines()[0])
    assert keyword["cluster_ref"] == "desk-setup-guide"


def test_content_cluster_commands_output_json(tmp_path: Path, capsys) -> None:
    project_dir = tmp_path / "project"
    state.init_state("shopify", "Hexcal", "https://www.hexcal.com", project_dir=project_dir)
    (project_dir / "strategy/keyword-pool.jsonl").write_text(json.dumps({"keyword": "desk setup"}) + "\n", encoding="utf-8")

    assert main(["--project-dir", str(project_dir), "content", "cluster-brief", "--json"]) == 0
    brief = json.loads(capsys.readouterr().out)
    assert brief["ok"] is True

    clusters = tmp_path / "clusters.json"
    clusters.write_text(json.dumps({"clusters": [{"cluster_name": "Desk Setup", "member_keywords": ["desk setup"]}]}), encoding="utf-8")
    assert main(["--project-dir", str(project_dir), "content", "import-clusters", "--from-file", str(clusters), "--json"]) == 0
    imported = json.loads(capsys.readouterr().out)
    assert imported["ok"] is True
    assert imported["schema_version"] == "content-cluster-import-v1"
