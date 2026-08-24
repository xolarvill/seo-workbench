from datetime import datetime, timezone
from pathlib import Path

from seo_workbench import state
from seo_workbench.cli import main
from seo_workbench.measurement_regimes import comparison_breaks, list_regimes, record_regime


def _project(path: Path) -> Path:
    state.init_state("shopify", "Example", "https://example.com", project_dir=path)
    return path


def test_measurement_regime_breaks_only_crossing_comparisons(tmp_path: Path, capsys) -> None:
    project = _project(tmp_path / "project")
    record = record_regime(
        project,
        source="ga4",
        effective_at="2026-08-01",
        description="Changed key event definition",
        metrics=["key_events"],
        now=datetime(2026, 8, 2, tzinfo=timezone.utc),
    )

    assert comparison_breaks(
        project, start_date="2026-07-01", end_date="2026-08-20", sources={"ga4", "shopify"}
    ) == [record]
    assert comparison_breaks(
        project, start_date="2026-08-01", end_date="2026-08-20", sources={"ga4"}
    ) == []
    assert list_regimes(project)["count"] == 1

    assert main(["--project-dir", str(project), "statistics", "regime", "list", "--json"]) == 0
    assert '"count": 1' in capsys.readouterr().out
