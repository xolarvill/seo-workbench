import json
from datetime import date
from pathlib import Path

from seo_workbench import state
from seo_workbench.cli import main
from seo_workbench.report_archive import list_report_archive, scaffold_weekly_report, set_report_star


def _write(project_dir: Path, relative: str, content: str) -> None:
    path = state.safe_project_path(project_dir, relative)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


WEEK_34 = """# Store 周报 · 2026 Week 34（08-17 → 08-23）

## 速览

- [x] 完成事项 A
- [ ] 待办事项 B（未完成）
- [ ] 确认遗留到下周的事项 C

## 实质工作

- 要点

## 遗留工作

- [ ] **任务 D**：本周无法完成；后续：2026-09-11 再评估
- [ ] **任务 E**：等待外部确认；后续：2026/09/01 跟进
"""


def test_list_empty_archive(tmp_path: Path) -> None:
    project_dir = tmp_path / "project"
    state.init_state("shopify", "Store", "https://example.com", project_dir=project_dir)

    payload = list_report_archive(project_dir)

    assert payload["weekly"] == []
    assert payload["sub_reports"] == []
    assert payload["categories"] == {}
    assert payload["latest_week"] is None


def test_list_parses_weekly_and_subreports(tmp_path: Path) -> None:
    project_dir = tmp_path / "project"
    state.init_state("shopify", "Store", "https://example.com", project_dir=project_dir)
    _write(project_dir, "reports/2026_week_34_work_done.md", WEEK_34)
    _write(project_dir, "reports/20260817_tech_theme-fix-v2-handoff.md", "# Tech handoff\n")
    _write(project_dir, "reports/20260817_decision_statistical-seo-reassessment.md", "# Decision\n")
    _write(project_dir, "reports/unrelated-note.md", "# Note\n")

    payload = list_report_archive(project_dir)

    assert payload["latest_week"] == {"year": 2026, "week": 34}
    weekly = payload["weekly"]
    assert len(weekly) == 1
    item = weekly[0]
    assert item["path"] == "reports/2026_week_34_work_done.md"
    assert item["checked"] == 1
    assert item["total"] == 3
    assert item["carry_over"] == 2
    assert item["inherited_from"] == []
    assert item["start"] == "08-17"
    assert item["end"] == "08-23"
    assert [follow["date"] for follow in item["follow_ups"]] == ["2026-09-11", "2026/09/01"]

    sub = payload["sub_reports"]
    assert {report["category"] for report in sub} == {"tech", "decision"}
    assert payload["categories"]["tech"][0]["topic"] == "theme-fix-v2-handoff"
    assert "unrelated-note.md" not in [report["path"] for report in sub]


def test_scaffold_creates_next_week_with_carry_over(tmp_path: Path) -> None:
    project_dir = tmp_path / "project"
    state.init_state("shopify", "Store", "https://example.com", project_dir=project_dir)
    _write(project_dir, "reports/2026_week_34_work_done.md", WEEK_34)

    result = scaffold_weekly_report(project_dir)

    assert result["ok"] is True
    assert result["path"] == "reports/2026_week_35_work_done.md"
    assert result["year"] == 2026
    assert result["week"] == 35
    assert result["carried_over"] == 2
    assert result["from_previous"] == "reports/2026_week_34_work_done.md"

    path = state.safe_project_path(project_dir, result["path"])
    text = path.read_text(encoding="utf-8")
    assert "# Store 周报 · 2026 Week 35（08-24 → 08-30）" in text
    assert "## 速览" in text
    assert "- [ ] 任务 D：本周无法完成；后续：2026-09-11 再评估（承接自 Week 34）" in text
    assert "- [ ] 任务 E：等待外部确认；后续：2026/09/01 跟进（承接自 Week 34）" in text
    assert text.index("同时记录两类任务") < text.index("任务 D")
    assert "## 实质工作" in text
    assert "## 遗留工作" in text
    assert "## 其他" in text

    summary = list_report_archive(project_dir)["weekly"][0]
    assert summary["inherited_from"] == [34]


def test_scaffold_refuses_overwrite_and_honors_force(tmp_path: Path) -> None:
    project_dir = tmp_path / "project"
    state.init_state("shopify", "Store", "https://example.com", project_dir=project_dir)
    _write(project_dir, "reports/2026_week_35_work_done.md", "# existing\n")

    try:
        scaffold_weekly_report(project_dir, week=35, year=2026)
    except FileExistsError as exc:
        assert "already exists" in str(exc)
    else:
        raise AssertionError("expected FileExistsError")

    result = scaffold_weekly_report(project_dir, week=35, year=2026, force=True)
    text = state.safe_project_path(project_dir, result["path"]).read_text(encoding="utf-8")
    assert "# Store 周报 · 2026 Week 35（08-24 → 08-30）" in text


def test_scaffold_explicit_week_without_carry_over(tmp_path: Path) -> None:
    project_dir = tmp_path / "project"
    state.init_state("shopify", "Store", "https://example.com", project_dir=project_dir)

    result = scaffold_weekly_report(project_dir, week=1, year=2026, carry_over=False)

    assert result["path"] == "reports/2026_week_01_work_done.md"
    assert result["carried_over"] == 0
    text = state.safe_project_path(project_dir, result["path"]).read_text(encoding="utf-8")
    assert "# Store 周报 · 2026 Week 01（12-29 → 01-04）" in text


def test_reports_cli_list_and_new(tmp_path: Path, capsys) -> None:
    project_dir = tmp_path / "project"
    state.init_state("shopify", "Store", "https://example.com", project_dir=project_dir)
    _write(project_dir, "reports/2026_week_34_work_done.md", WEEK_34)

    assert main(["--project-dir", str(project_dir), "reports", "list", "--json"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["ok"] is True
    assert payload["weekly"][0]["week"] == 34

    assert main(["--project-dir", str(project_dir), "reports", "new", "--json"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["path"] == "reports/2026_week_35_work_done.md"
    assert payload["carried_over"] == 2


def test_list_filters_subreports(tmp_path: Path) -> None:
    project_dir = tmp_path / "project"
    state.init_state("shopify", "Store", "https://example.com", project_dir=project_dir)
    _write(project_dir, "reports/20260817_tech_theme-fix-handoff.md", "# T\n")
    _write(project_dir, "reports/20260817_decision_statistical-seo-reassessment.md", "# D\n")
    _write(project_dir, "reports/20260701_ops_dead-links-triage.md", "# O\n")

    by_category = list_report_archive(project_dir, category="tech")
    assert [report["topic"] for report in by_category["sub_reports"]] == ["theme-fix-handoff"]

    by_query = list_report_archive(project_dir, query="statistical")
    assert [report["topic"] for report in by_query["sub_reports"]] == ["statistical-seo-reassessment"]

    by_year = list_report_archive(project_dir, year=2026)
    assert len(by_year["sub_reports"]) == 3
    by_month = list_report_archive(project_dir, month=7)
    assert [report["topic"] for report in by_month["sub_reports"]] == ["dead-links-triage"]
    none = list_report_archive(project_dir, year=2025)
    assert none["sub_reports"] == []

    combined = list_report_archive(project_dir, query="dead", category="ops", year=2026, month=7)
    assert [report["topic"] for report in combined["sub_reports"]] == ["dead-links-triage"]
    assert combined["filters"] == {"query": "dead", "category": "ops", "year": 2026, "month": 7}


def test_report_stars_persist_and_return_on_archive_items(tmp_path: Path) -> None:
    project_dir = tmp_path / "project"
    state.init_state("shopify", "Store", "https://example.com", project_dir=project_dir)
    _write(project_dir, "reports/2026_week_34_work_done.md", WEEK_34)
    _write(project_dir, "reports/20260817_tech_theme-fix-handoff.md", "# Handoff\n")

    assert list_report_archive(project_dir)["weekly"][0]["starred"] is False
    assert set_report_star(project_dir, "reports/2026_week_34_work_done.md", True) == {
        "path": "reports/2026_week_34_work_done.md",
        "starred": True,
    }
    payload = list_report_archive(project_dir)
    assert payload["weekly"][0]["starred"] is True
    assert payload["sub_reports"][0]["starred"] is False
    assert state.load_state(project_dir)["reportStars"] == {"reports/2026_week_34_work_done.md": True}

    set_report_star(project_dir, "reports/2026_week_34_work_done.md", False)
    assert "reportStars" not in state.load_state(project_dir)


def test_list_builds_progress_with_states_and_carry_tracks(tmp_path: Path) -> None:
    project_dir = tmp_path / "project"
    state.init_state("shopify", "Store", "https://example.com", project_dir=project_dir)
    _write(project_dir, "reports/2026_week_33_work_done.md", """# Store 周报 · 2026 Week 33（08-10 → 08-16）

## 遗留工作

- [ ] **Cable Hub 变更效果评估**：等待后窗口；后续：2026-09-11 再评估
- [ ] **一次性任务**：本周可完成；后续：2026-08-14 跟进
""")
    _write(project_dir, "reports/2026_week_34_work_done.md", """# Store 周报 · 2026 Week 34（08-17 → 08-23）

## 遗留工作

- [ ] **Cable Hub 变更效果评估**：仍等待后窗口；后续：2026-09-11 再评估
""")

    progress = list_report_archive(project_dir)["progress"]

    assert [entry["week"] for entry in progress["follow_ups"]] == [33, 34, 33]
    assert [entry["date"] for entry in progress["follow_ups"]] == ["2026-08-14", "2026-09-11", "2026-09-11"]
    assert {entry["state"] for entry in progress["follow_ups"]} == {"future", "overdue"}
    assert progress["overdue"] == 1
    assert progress["upcoming"] == 0

    tracks = progress["carried_over_tracks"]
    assert len(tracks) == 1
    assert tracks[0]["task"] == "cablehub变更效果评估"
    assert tracks[0]["spans"] == 2
    assert [entry["week"] for entry in tracks[0]["entries"]] == [33, 34]
