import json
from pathlib import Path

from seo_workbench import state
from seo_workbench import content_publish
from seo_workbench.cli import main
from seo_workbench.content_publish import build_publish_payload, publish_item, strip_leading_h1


def test_build_publish_payload_creates_scheduled_article_input() -> None:
    report = build_publish_payload(
        {
            "id": "rec1",
            "status": "approved",
            "title": "Small Desk Setup",
            "slug": "small-desk-setup",
            "meta_description": "Desk guide",
            "scheduled_at": "2026-08-01T17:00:00Z",
            "draft_html": "<h1>Small Desk Setup</h1><p>Body.</p><h2>FAQ</h2><h3>Q?</h3><p>A.</p>",
        },
        project_url="https://www.hexcal.com",
        blog_id="100",
    )

    article = report["article"]
    assert report["operation"] == "create"
    assert report["mutation"] == "articleCreate"
    assert article["blogId"] == "gid://shopify/Blog/100"
    assert article["author"] == {"name": "Store"}
    assert article["isPublished"] is True
    assert article["handle"] == "small-desk-setup"
    assert article["publishDate"] == "2026-08-01T17:00:00Z"
    assert "<h1>" not in article["body"]
    assert "FAQPage" in article["body"]
    assert report["warnings"] == []


def test_build_publish_payload_updates_existing_article() -> None:
    report = build_publish_payload(
        {
            "id": "rec2",
            "status": "approved",
            "title": "Refresh",
            "shopify_article_id": "123",
            "meta_description": "Refreshed meta.",
            "draft_html": "<p>Updated.</p>",
        },
        project_url="https://www.hexcal.com",
        blog_id="100",
    )

    assert report["operation"] == "update"
    assert report["mutation"] == "articleUpdate"
    assert report["variables"]["id"] == "gid://shopify/Article/123"
    assert "id" not in report["article"]
    assert "isPublished" not in report["article"]
    assert report["article"]["summary"] == "Refreshed meta."
    assert report["article"]["metafields"] == [
        {
            "key": "description_tag",
            "value": "Refreshed meta.",
            "type": "single_line_text_field",
            "namespace": "global",
        }
    ]


def test_build_publish_payload_preserves_existing_blog_path() -> None:
    report = build_publish_payload(
        {
            "id": "rec_news",
            "status": "approved",
            "title": "News refresh",
            "slug": "news-refresh",
            "shopify_article_id": "456",
            "live_url": "https://www.hexcal.com/blogs/news/news-refresh",
            "draft_html": "<p>Updated.</p>",
        },
        project_url="https://www.hexcal.com",
        blog_id="200",
    )

    assert report["live_url"] == "https://www.hexcal.com/blogs/news/news-refresh"
    assert '"url":"https://www.hexcal.com/blogs/news/news-refresh"' in report["article"]["body"]


def test_strip_leading_h1_only_removes_first_heading() -> None:
    assert strip_leading_h1("<h1>Title</h1><h2>Keep</h2>") == "<h2>Keep</h2>"


def test_publish_dry_run_cli_writes_audit_without_shopify_token(tmp_path: Path, capsys) -> None:
    project_dir = tmp_path / "project"
    state.init_state("shopify", "Hexcal", "https://www.hexcal.com", project_dir=project_dir)
    (project_dir / "content/blog-pipeline.jsonl").write_text(
        json.dumps(
            {
                "id": "rec3",
                "status": "review",
                "title": "Draft",
                "slug": "draft",
                "draft_html": "<p>Body.</p>",
            },
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )

    assert main(["--project-dir", str(project_dir), "content", "publish-dry-run", "rec3", "--blog-id", "100", "--json"]) == 0
    payload = json.loads(capsys.readouterr().out)
    report_path = Path(payload["path"])

    assert payload["ok"] is True
    assert payload["dry_run"] is True
    assert payload["article"]["author"] == {"name": "Hexcal"}
    assert any(warning["code"] == "status.not_approved" for warning in payload["warnings"])
    assert report_path.exists()
    assert "token" not in report_path.read_text(encoding="utf-8").lower()


def test_publish_item_blocks_warnings_before_credentials(tmp_path: Path) -> None:
    project_dir = tmp_path / "project"
    state.init_state("shopify", "Hexcal", "https://www.hexcal.com", project_dir=project_dir)
    (project_dir / "content/blog-pipeline.jsonl").write_text(
        json.dumps({"id": "rec4", "status": "review", "title": "Draft", "slug": "draft", "draft_html": "<p>Body.</p>"})
        + "\n",
        encoding="utf-8",
    )

    report, path = publish_item(project_dir, "rec4", blog_id="100")

    assert report["collection_status"] == "blocked"
    assert any(warning["code"] == "status.not_approved" for warning in report["warnings"])
    assert path.name == "rec4-blocked.json"


def test_publish_rechecks_qc_and_blocks_unverified_product_specs(tmp_path: Path) -> None:
    project_dir = tmp_path / "project"
    state.init_state("shopify", "Hexcal", "https://example.com", project_dir=project_dir)
    (project_dir / "content/blog-pipeline.jsonl").write_text(
        json.dumps(
            {
                "id": "rec-qc",
                "status": "approved",
                "title": "Ready",
                "slug": "ready",
                "scheduled_at": "2026-08-01T17:00:00Z",
                "draft_html": "<p>Hexcal supports 999 lb.</p>",
            }
        )
        + "\n",
        encoding="utf-8",
    )

    report, path = publish_item(project_dir, "rec-qc", blog_id="100")

    assert report["collection_status"] == "blocked"
    assert report["quality"]["warnings"]
    assert any(warning["code"] == "qc.spec_provenance" for warning in report["warnings"])
    assert path.name == "rec-qc-blocked.json"


def test_publish_requires_shopify_schedule_confirmation(tmp_path: Path, monkeypatch) -> None:
    project_dir = tmp_path / "project"
    state.init_state("shopify", "Store", "https://example.com", project_dir=project_dir)
    (project_dir / ".runtime/integrations").mkdir(parents=True)
    (project_dir / ".runtime/integrations/shopify.json").write_text(
        json.dumps({"shop_domain": "example.myshopify.com", "access_token": "token", "scopes": ["write_content"]}),
        encoding="utf-8",
    )
    (project_dir / "content/blog-pipeline.jsonl").write_text(
        json.dumps(
            {
                "id": "rec-schedule",
                "status": "approved",
                "title": "Ready",
                "slug": "ready",
                "scheduled_at": "2026-08-10T17:00:00Z",
                "draft_html": "<p>Body.</p>",
            }
        )
        + "\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(
        content_publish,
        "_shopify_graphql",
        lambda *_args, **_kwargs: {
            "data": {"articleCreate": {"article": {"id": "gid://shopify/Article/123", "publishedAt": None}, "userErrors": []}}
        },
    )

    report, _path = publish_item(project_dir, "rec-schedule", blog_id="100")

    assert report["collection_status"] == "error"
    assert report["shopify"]["schedule_error"] == "Shopify did not confirm publishedAt"


def test_publish_item_never_allows_warning_bypass(tmp_path: Path) -> None:
    project_dir = tmp_path / "project"
    state.init_state("shopify", "Hexcal", "https://www.hexcal.com", project_dir=project_dir)
    (project_dir / "content/blog-pipeline.jsonl").write_text(
        json.dumps({"id": "rec4b", "status": "review", "title": "Draft", "slug": "draft", "draft_html": "<p>Body.</p>"})
        + "\n",
        encoding="utf-8",
    )

    report, _path = publish_item(project_dir, "rec4b", blog_id="100", allow_warnings=True)

    assert report["collection_status"] == "blocked"
    assert any(warning["code"] == "hitl.allow_warnings_disabled" for warning in report["warnings"])


def test_publish_cli_rejects_allow_warnings(tmp_path: Path, capsys) -> None:
    project_dir = tmp_path / "project"
    state.init_state("shopify", "Hexcal", "https://www.hexcal.com", project_dir=project_dir)

    assert (
        main(
            [
                "--project-dir",
                str(project_dir),
                "content",
                "publish",
                "rec4c",
                "--blog-id",
                "100",
                "--confirm",
                "--allow-warnings",
                "--json",
            ]
        )
        == 1
    )
    assert json.loads(capsys.readouterr().out)["error"] == "content publish cannot bypass warnings"


def test_publish_item_writes_shopify_and_updates_local_state(tmp_path: Path, monkeypatch) -> None:
    project_dir = tmp_path / "project"
    state.init_state("shopify", "Hexcal", "https://www.hexcal.com", project_dir=project_dir)
    (project_dir / ".runtime/integrations").mkdir(parents=True)
    (project_dir / ".runtime/integrations/shopify.json").write_text(
        json.dumps(
            {
                "shop_domain": "example-store.myshopify.com",
                "access_token": "shpat_secret",
                "scopes": ["write_content"],
            }
        ),
        encoding="utf-8",
    )
    (project_dir / "content/blog-pipeline.jsonl").write_text(
        json.dumps(
            {
                "id": "rec5",
                "status": "approved",
                "title": "Ready",
                "slug": "ready",
                "scheduled_at": "2026-08-01T17:00:00Z",
                "draft_html": "<p>Body.</p>",
            }
        )
        + "\n",
        encoding="utf-8",
    )
    data = state.load_state(project_dir)
    data["contentQueue"] = [{"id": "rec5", "status": "approved", "title": "Ready", "slug": "ready"}]
    state.save_state(data, project_dir)
    calls = []

    class Response:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def read(self, _limit):
            return json.dumps(
                {
                    "data": {
                        "articleCreate": {
                            "article": {
                                "id": "gid://shopify/Article/123",
                                "title": "Ready",
                                "handle": "ready",
                                "isPublished": False,
                                "publishedAt": "2026-08-01T17:00:00Z",
                            },
                            "userErrors": [],
                        }
                    }
                }
            ).encode()

    def fake_urlopen(request, timeout):
        calls.append((request, timeout))
        return Response()

    monkeypatch.setattr(content_publish, "urlopen", fake_urlopen)

    report, path = publish_item(project_dir, "rec5", blog_id="100", timeout=5)

    assert report["collection_status"] == "complete"
    assert path.name == "rec5-publish.json"
    assert calls[0][0].full_url == "https://example-store.myshopify.com/admin/api/2026-07/graphql.json"
    saved_record = json.loads((project_dir / "content/blog-pipeline.jsonl").read_text(encoding="utf-8"))
    assert saved_record["shopify_article_id"] == "123"
    assert saved_record["status"] == "scheduled"
    queue_item = state.load_state(project_dir)["contentQueue"][0]
    assert queue_item["status"] == "scheduled"
    assert queue_item["shopify_article_id"] == "123"
    assert "shpat_secret" not in path.read_text(encoding="utf-8")
