from datetime import date
from pathlib import Path

from seo_workbench import state
from seo_workbench.cli import main
from seo_workbench import cli as cli_module, statistics_pipeline


def _project(path: Path) -> Path:
    state.init_state("shopify", "Example", "https://example.com", project_dir=path)
    return path


def test_statistics_pipeline_uses_gsc_finalized_end_date(tmp_path: Path, monkeypatch, capsys) -> None:
    project = _project(tmp_path / "project")
    observed: dict[str, object] = {}

    def gsc(_project, _output, **kwargs):
        observed["gsc_today"] = kwargs.get("today")
        return {
            "collection_status": "ok",
            "manifest": {"path": "gsc.json"},
            "windows": {
                "previous": {"page": {"request": {"startDate": "2026-06-18", "endDate": "2026-07-15"}}},
                "current": {"page": {"request": {"startDate": "2026-07-16", "endDate": "2026-08-12"}}},
            },
        }

    def ga4(_project, _output, **kwargs):
        observed["ga4_end"] = kwargs["end_date"]
        return {"collection_status": "ok", "manifest": {"path": "ga4.json"}}

    def shopify(_project, **kwargs):
        observed["shopify_end"] = kwargs["end_date"]
        return {"collection_status": "ok", "manifest": {"path": "shopify.json"}}

    monkeypatch.setattr(statistics_pipeline.gsc_probe, "collect_performance", gsc)
    monkeypatch.setattr(statistics_pipeline.ga4_probe, "collect", ga4)
    monkeypatch.setattr(statistics_pipeline.shopify_orders_probe, "collect_orders", shopify)
    monkeypatch.setattr(
        statistics_pipeline,
        "collect_business_signals",
        lambda _project: (
            {
                "collection_status": "ok",
                "windows": {
                    "previous": {"request": {"startDate": "2026-06-18", "endDate": "2026-07-15"}},
                    "current": {"request": {"startDate": "2026-07-16", "endDate": "2026-08-12"}},
                },
            },
            tmp_path / "business.json",
        ),
    )
    monkeypatch.setattr(
        statistics_pipeline,
        "ingest_daily_history",
        lambda _project: {"sources": {"gsc": {"stored_rows": 1}, "business": {"stored_rows": 1}}},
    )
    monkeypatch.setattr(
        statistics_pipeline,
        "analyze_content_portfolio",
        lambda _project: (
            {"comparability": {"comparable": True}, "source": {"business_comparable": True}, "count": 1},
            tmp_path / "portfolio.json",
        ),
    )

    report, path = statistics_pipeline.collect_statistics(project, today=date(2026, 8, 15))

    assert report["collection_status"] == "ok"
    assert report["common_finalized_end_date"] == "2026-08-12"
    assert observed == {
        "gsc_today": date(2026, 8, 15),
        "ga4_end": date(2026, 8, 12),
        "shopify_end": date(2026, 8, 12),
    }
    assert path.stat().st_mode & 0o777 == 0o600

    monkeypatch.setattr(
        statistics_pipeline,
        "analyze_content_portfolio",
        lambda _project: (
            {"comparability": {"comparable": False}, "source": {"business_comparable": False}, "count": 1},
            tmp_path / "portfolio-partial.json",
        ),
    )
    partial, _ = statistics_pipeline.collect_statistics(project, today=date(2026, 8, 15))
    assert partial["collection_status"] == "partial"
    assert len(partial["warnings"]) == 2

    monkeypatch.setattr(cli_module, "collect_statistics", lambda *_args, **_kwargs: (report, path))
    assert main(["--project-dir", str(project), "statistics", "collect", "--json"]) == 0
    assert '"ok": true' in capsys.readouterr().out


def test_statistics_pipeline_records_failure_without_refreshing_portfolio(tmp_path: Path, monkeypatch) -> None:
    project = _project(tmp_path / "project")
    monkeypatch.setattr(
        statistics_pipeline.gsc_probe,
        "collect_performance",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError("GSC unavailable")),
    )
    monkeypatch.setattr(
        statistics_pipeline,
        "analyze_content_portfolio",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("must not refresh")),
    )

    report, path = statistics_pipeline.collect_statistics(project)

    assert report["collection_status"] == "failed"
    assert report["errors"] == ["GSC unavailable"]
    assert path.is_file()
