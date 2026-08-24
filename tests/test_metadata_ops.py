import json
from pathlib import Path

from seo_workbench import state
from seo_workbench import metadata_ops
from seo_workbench.cli import main
from seo_workbench.metadata_ops import (
    build_article_summary_payload,
    build_collection_seo_payload,
    build_product_seo_payload,
    update_article_summary,
    update_collection_seo,
    update_product_seo,
)


def test_build_payload_uses_global_metafields() -> None:
    report = build_product_seo_payload("under-desk-cable-management-tray", "Title", "Description")

    assert report["resource"] == "product"
    assert report["mutation"] == "productUpdate"
    assert report["seo"] == {"title": "Title", "description": "Description"}
    assert report["variables"]["metafields"] == [
        {"namespace": "global", "key": "title_tag", "value": "Title", "type": "single_line_text_field"},
        {"namespace": "global", "key": "description_tag", "value": "Description", "type": "single_line_text_field"},
    ]
    assert report["warnings"] == []


def test_build_payload_warns_on_length_and_html() -> None:
    report = build_product_seo_payload("h", "x" * 71, "<b>desc</b>")

    codes = {warning["code"] for warning in report["warnings"]}
    assert codes == {"seo_title.too_long", "html.in_seo_text"}


def test_update_blocks_warnings_before_credentials(tmp_path: Path) -> None:
    project_dir = tmp_path / "project"
    state.init_state("shopify", "Hexcal", "https://www.hexcal.com", project_dir=project_dir)

    report, path = update_product_seo(project_dir, "h", "", "desc")

    assert report["collection_status"] == "blocked"
    assert any(warning["code"] == "seo_title.missing" for warning in report["warnings"])
    assert path.name == "h-blocked.json"


def test_update_dry_run_writes_audit_without_shopify_token(tmp_path: Path, capsys) -> None:
    project_dir = tmp_path / "project"
    state.init_state("shopify", "Hexcal", "https://www.hexcal.com", project_dir=project_dir)

    assert (
        main(
            [
                "--project-dir",
                str(project_dir),
                "metadata",
                "update",
                "under-desk-cable-management-tray",
                "--seo-title",
                "Title",
                "--seo-description",
                "Description",
                "--dry-run",
                "--json",
            ]
        )
        == 0
    )
    payload = json.loads(capsys.readouterr().out)
    assert payload["ok"] is True
    assert payload["dry_run"] is True
    assert Path(payload["path"]).exists()


def test_update_requires_confirm(tmp_path: Path, capsys) -> None:
    project_dir = tmp_path / "project"
    state.init_state("shopify", "Hexcal", "https://www.hexcal.com", project_dir=project_dir)

    assert (
        main(
            [
                "--project-dir",
                str(project_dir),
                "metadata",
                "update",
                "under-desk-cable-management-tray",
                "--seo-title",
                "Title",
                "--seo-description",
                "Description",
                "--json",
            ]
        )
        == 1
    )
    assert "requires --confirm" in capsys.readouterr().out


def test_update_writes_shopify_and_verifies_readback(tmp_path: Path, monkeypatch) -> None:
    project_dir = tmp_path / "project"
    state.init_state("shopify", "Hexcal", "https://www.hexcal.com", project_dir=project_dir)
    (project_dir / ".runtime/integrations").mkdir(parents=True)
    (project_dir / ".runtime/integrations/shopify.json").write_text(
        json.dumps(
            {
                "shop_domain": "example-store.myshopify.com",
                "access_token": "shpat_secret",
                "scopes": ["write_products"],
            }
        ),
        encoding="utf-8",
    )
    calls = []

    class Response:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def read(self, _limit):
            query = json.loads(calls[-1][0].data)["query"]
            if "productUpdate" in query:
                return json.dumps(
                    {"data": {"productUpdate": {"product": {"id": "gid://shopify/Product/1"}, "userErrors": []}}}
                ).encode()
            if "ProductSeoVerify" in query:
                return json.dumps(
                    {
                        "data": {
                            "product": {
                                "id": "gid://shopify/Product/1",
                                "seo": {"title": "Title", "description": "Description"},
                                "metafields": {
                                    "edges": [
                                        {"node": {"namespace": "global", "key": "title_tag", "value": "Title"}},
                                        {"node": {"namespace": "global", "key": "description_tag", "value": "Description"}},
                                    ]
                                },
                            }
                        }
                    }
                ).encode()
            return json.dumps(
                {"data": {"products": {"edges": [{"node": {"id": "gid://shopify/Product/1"}}]}}}
            ).encode()

    def fake_urlopen(request, timeout):
        calls.append((request, timeout))
        return Response()

    monkeypatch.setattr(metadata_ops, "urlopen", fake_urlopen)

    report, path = update_product_seo(project_dir, "under-desk-cable-management-tray", "Title", "Description", timeout=5)

    assert report["collection_status"] == "complete"
    assert report["verified"]["title_matches"] is True
    assert report["verified"]["description_matches"] is True
    assert path.name == "under-desk-cable-management-tray-update.json"
    assert "shpat_secret" not in path.read_text(encoding="utf-8")
    assert calls[0][0].full_url == "https://example-store.myshopify.com/admin/api/2026-07/graphql.json"


def test_build_collection_payload_uses_seo_input_and_body() -> None:
    report = build_collection_seo_payload("desks", "Title", "Description", "<p>Body.</p>")

    assert report["resource"] == "collection"
    assert report["mutation"] == "collectionUpdate"
    assert report["variables"]["seo"] == {"title": "Title", "description": "Description"}
    assert report["variables"]["body"] == "<p>Body.</p>"
    assert report["warnings"] == []


def test_collection_blocks_missing_body() -> None:
    project_dir = tmp_path_ish()
    report, path = update_collection_seo(project_dir, "desks", "Title", "Description", "", dry_run=False)
    assert report["collection_status"] == "blocked"
    assert any(warning["code"] == "body.missing" for warning in report["warnings"])
    assert path.name == "desks-blocked.json"


def test_collection_update_writes_and_verifies_readback(tmp_path: Path, monkeypatch) -> None:
    project_dir = tmp_path / "project"
    state.init_state("shopify", "Hexcal", "https://www.hexcal.com", project_dir=project_dir)
    (project_dir / ".runtime/integrations").mkdir(parents=True)
    (project_dir / ".runtime/integrations/shopify.json").write_text(
        json.dumps(
            {
                "shop_domain": "example-store.myshopify.com",
                "access_token": "shpat_secret",
                "scopes": ["write_products", "write_content"],
            }
        ),
        encoding="utf-8",
    )
    calls = []

    class Response:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def read(self, _limit):
            query = json.loads(calls[-1][0].data)["query"]
            if "collectionUpdate" in query:
                return json.dumps(
                    {"data": {"collectionUpdate": {"collection": {"id": "gid://shopify/Collection/1"}, "userErrors": []}}}
                ).encode()
            if "CollectionSeoVerify" in query:
                return json.dumps(
                    {
                        "data": {
                            "collection": {
                                "id": "gid://shopify/Collection/1",
                                "seo": {"title": "Title", "description": "Description"},
                                "descriptionHtml": "<p>Body.</p>",
                            }
                        }
                    }
                ).encode()
            return json.dumps(
                {"data": {"collections": {"edges": [{"node": {"id": "gid://shopify/Collection/1"}}]}}}
            ).encode()

    def fake_urlopen(request, timeout):
        calls.append((request, timeout))
        return Response()

    monkeypatch.setattr(metadata_ops, "urlopen", fake_urlopen)

    report, path = update_collection_seo(project_dir, "desks", "Title", "Description", "<p>Body.</p>", timeout=5)

    assert report["collection_status"] == "complete"
    assert report["verified"]["title_matches"] is True
    assert report["verified"]["body_matches"] is True
    assert path.name == "desks-update.json"
    assert "shpat_secret" not in path.read_text(encoding="utf-8")


def tmp_path_ish() -> Path:
    import tempfile

    project_dir = Path(tempfile.mkdtemp()) / "project"
    state.init_state("shopify", "Hexcal", "https://www.hexcal.com", project_dir=project_dir)
    return project_dir


def test_build_article_payload_uses_summary_and_metafield() -> None:
    report = build_article_summary_payload("how-to-set-up-a-home-office", "A summary.")

    assert report["resource"] == "article"
    assert report["mutation"] == "articleUpdate"
    assert report["summary"] == "A summary."
    assert report["variables"]["metafields"] == [
        {"namespace": "global", "key": "description_tag", "value": "A summary.", "type": "single_line_text_field"}
    ]
    assert report["warnings"] == []


def test_article_blocks_html_and_overlong_summary() -> None:
    report = build_article_summary_payload("h", "<b>x</b>" + "y" * 160)
    codes = {warning["code"] for warning in report["warnings"]}
    assert codes == {"summary.too_long", "html.in_summary"}


def test_article_update_writes_and_verifies_readback(tmp_path: Path, monkeypatch) -> None:
    project_dir = tmp_path / "project"
    state.init_state("shopify", "Hexcal", "https://www.hexcal.com", project_dir=project_dir)
    (project_dir / ".runtime/integrations").mkdir(parents=True)
    (project_dir / ".runtime/integrations/shopify.json").write_text(
        json.dumps(
            {
                "shop_domain": "example-store.myshopify.com",
                "access_token": "shpat_secret",
                "scopes": ["write_products", "write_content"],
            }
        ),
        encoding="utf-8",
    )
    calls = []

    class Response:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def read(self, _limit):
            query = json.loads(calls[-1][0].data)["query"]
            if "articleUpdate" in query:
                return json.dumps(
                    {"data": {"articleUpdate": {"article": {"id": "gid://shopify/Article/1"}, "userErrors": []}}}
                ).encode()
            if "ArticleSummaryVerify" in query:
                return json.dumps(
                    {
                        "data": {
                            "article": {
                                "id": "gid://shopify/Article/1",
                                "summary": "A summary.",
                                "metafields": {
                                    "edges": [{"node": {"namespace": "global", "key": "description_tag", "value": "A summary."}}]
                                },
                            }
                        }
                    }
                ).encode()
            return json.dumps(
                {"data": {"articles": {"edges": [{"node": {"id": "gid://shopify/Article/1"}}]}}}
            ).encode()

    def fake_urlopen(request, timeout):
        calls.append((request, timeout))
        return Response()

    monkeypatch.setattr(metadata_ops, "urlopen", fake_urlopen)

    report, path = update_article_summary(project_dir, "how-to-set-up-a-home-office", "A summary.", timeout=5)

    assert report["collection_status"] == "complete"
    assert report["verified"]["summary_matches"] is True
    assert report["verified"]["metafield_matches"] is True
    assert path.name == "how-to-set-up-a-home-office-update.json"
    assert "shpat_secret" not in path.read_text(encoding="utf-8")
