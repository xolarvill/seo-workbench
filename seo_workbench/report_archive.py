from __future__ import annotations

import re
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from seo_workbench import state
from seo_workbench_tools.files import atomic_write_text

WEEKLY_PATTERN = re.compile(r"^(?P<year>\d{4})_week_(?P<week>\d{2})_work_done\.md$")
SUBREPORT_PATTERN = re.compile(r"^(?P<date>\d{8})_(?P<category>[a-z]+)_(?P<topic>.+)\.md$")
REPORT_CATEGORIES = ("tech", "content", "ops", "decision", "outcome")
WEEKLY_TEMPLATE = state.ROOT / "templates" / "weekly_work_done.md"
RANGE_PATTERN = re.compile(r"（(?P<start>\d{2}-\d{2}) → (?P<end>\d{2}-\d{2})）")
FOLLOW_UP_PATTERN = re.compile(r"\d{4}[-/]\d{1,2}[-/]\d{1,2}")
CHECKBOX = re.compile(r"^- \[(?P<checked>[ xX])\] ")


RANGE_PATTERN = re.compile(r"（(?P<start>\d{2}-\d{2}) → (?P<end>\d{2}-\d{2})）")
FOLLOW_UP_PATTERN = re.compile(r"\d{4}[-/]\d{1,2}[-/]\d{1,2}")
CHECKBOX = re.compile(r"^- \[(?P<checked>[ xX])\] ")
INHERITED_PATTERN = re.compile(r"（承接自 Week (\d+)）")
TASK_BOLD = re.compile(r"\*\*(.+?)\*\*")


def list_report_archive(
    project_dir: Path,
    *,
    query: str = "",
    category: str = "",
    year: int | None = None,
    month: int | None = None,
) -> dict[str, Any]:
    """Index weekly work archives and sub-reports under reports/.

    The index is a read-time projection of the Markdown archive: weekly
    files get checkbox counts, inherited/carry-over and follow-up dates
    parsed defensively, and sub-reports are grouped by category. The
    progress block aggregates follow-up due dates across weeks and
    carries-over tracks (same task carried across two or more weeks).
    Parsing failures degrade to the filename only; absent files stay
    absent (never synthesized). Sub-reports can be filtered by query,
    category, year, and month.
    """
    reports_dir = state.safe_project_path(project_dir, "reports")
    starred_paths = _load_report_stars(project_dir)
    weekly: list[dict[str, Any]] = []
    sub_reports: list[dict[str, Any]] = []
    if reports_dir.is_dir() and not reports_dir.is_symlink():
        for path in sorted(reports_dir.iterdir()):
            if path.is_dir() or path.is_symlink() or path.suffix.lower() != ".md":
                continue
            match = WEEKLY_PATTERN.match(path.name)
            if match:
                weekly.append(
                    _weekly_summary(
                        path,
                        int(match.group("year")),
                        int(match.group("week")),
                        starred=path.relative_to(project_dir).as_posix() in starred_paths,
                    )
                )
                continue
            match = SUBREPORT_PATTERN.match(path.name)
            if match:
                sub_reports.append(
                    _subreport_summary(
                        path,
                        match.group("date"),
                        match.group("category"),
                        match.group("topic"),
                        starred=path.relative_to(project_dir).as_posix() in starred_paths,
                    )
                )
    weekly.sort(key=lambda item: (item["year"], item["week"]), reverse=True)
    sub_reports.sort(key=lambda item: item["date"], reverse=True)
    sub_reports = _filter_sub_reports(sub_reports, query=query, category=category, year=year, month=month)
    categories: dict[str, list[dict[str, Any]]] = {}
    for report in sub_reports:
        categories.setdefault(report["category"], []).append(report)
    return {
        "reports_dir": "reports",
        "weekly": weekly,
        "sub_reports": sub_reports,
        "categories": categories,
        "latest_week": {"year": weekly[0]["year"], "week": weekly[0]["week"]} if weekly else None,
        "filters": {"query": query or "", "category": category or "", "year": year, "month": month},
        "progress": _build_progress(weekly),
    }


def set_report_star(project_dir: Path, relative_path: str, starred: bool) -> dict[str, Any]:
    """Persist a star for an existing project report file."""
    path = _report_path(project_dir, relative_path)
    canonical = path.relative_to(project_dir).as_posix()

    def mutation(data: dict[str, Any]) -> dict[str, Any]:
        stars = data.get("reportStars")
        if not isinstance(stars, dict):
            stars = {}
        if starred:
            stars[canonical] = True
            data["reportStars"] = stars
        else:
            stars.pop(canonical, None)
            if stars:
                data["reportStars"] = stars
            else:
                data.pop("reportStars", None)
        return {"path": canonical, "starred": starred}

    return state.mutate_state(project_dir, mutation)


def scaffold_weekly_report(
    project_dir: Path,
    *,
    week: int | None = None,
    year: int | None = None,
    carry_over: bool = True,
    force: bool = False,
) -> dict[str, Any]:
    """Create a weekly work archive from the unified template.

    Without an explicit week the target is the next ISO week after the
    latest existing archive (or the current ISO week when none exists).
    With carry_over, unfinished items from the previous week's
    `遗留工作` section are moved into the new archive's `速览` list,
    unchecked. Existing target files are never overwritten unless force.
    """
    if week is not None and not 1 <= week <= 53:
        raise ValueError("week must be between 1 and 53")
    target_year, target_week = _target_iso_week(project_dir, week=week, year=year)
    target_path = state.safe_project_path(project_dir, f"reports/{target_year}_week_{target_week:02d}_work_done.md")
    if target_path.is_file() and not force:
        raise FileExistsError(f"weekly report already exists: reports/{target_path.name}")

    carried: list[str] = []
    previous: tuple[int, int, Path] | None = None
    if carry_over:
        previous = _previous_weekly(project_dir, before_year=target_year, before_week=target_week)
        if previous is not None:
            carried = _carry_over_items(previous[2])

    content = _render_weekly(
        project_dir,
        year=target_year,
        week=target_week,
        carried=carried,
        inherited_from=previous[1] if previous is not None else None,
    )
    target_path.parent.mkdir(parents=True, exist_ok=True)
    atomic_write_text(target_path, content)
    return {
        "ok": True,
        "path": f"reports/{target_path.name}",
        "year": target_year,
        "week": target_week,
        "carried_over": len(carried),
        "from_previous": f"reports/{previous[2].name}" if previous is not None else None,
    }


def _weekly_summary(path: Path, year: int, week: int, *, starred: bool = False) -> dict[str, Any]:
    text = _read_text(path)
    stat = path.stat()
    checked = 0
    total = 0
    carry_over = 0
    follow_ups: list[dict[str, str]] = []
    inherited: list[int] = []
    section = ""
    for line in text.splitlines():
        heading = re.match(r"^##\s+(\S+)", line)
        if heading:
            section = heading.group(1)
            continue
        if _is_carry_over_section(section) and line.startswith("- ") and not line.startswith("> "):
            follow_up = FOLLOW_UP_PATTERN.search(line)
            if follow_up:
                follow_ups.append({"date": follow_up.group(0), "text": re.sub(r"^\[[ xX]\]\s*", "", line[2:]).strip()})
        checkbox = CHECKBOX.match(line)
        if checkbox:
            if _is_carry_over_section(section):
                carry_over += 1
            else:
                total += 1
                if checkbox.group("checked").lower() == "x":
                    checked += 1
                inherited_match = INHERITED_PATTERN.search(line)
                if inherited_match:
                    inherited.append(int(inherited_match.group(1)))
            continue
    start, end = _week_range(year, week)
    heading_range = RANGE_PATTERN.search(text)
    return {
        "path": f"reports/{path.name}",
        "year": year,
        "week": week,
        "name": path.name,
        "start": heading_range.group("start") if heading_range else start,
        "end": heading_range.group("end") if heading_range else end,
        "modified_at": datetime.fromtimestamp(stat.st_mtime, timezone.utc).isoformat(),
        "size": stat.st_size,
        "checked": checked,
        "total": total,
        "carry_over": carry_over,
        "inherited_from": sorted(set(inherited)),
        "follow_ups": follow_ups,
        "starred": starred,
    }


def _subreport_summary(path: Path, report_date: str, category: str, topic: str, *, starred: bool = False) -> dict[str, Any]:
    stat = path.stat()
    return {
        "path": f"reports/{path.name}",
        "date": report_date,
        "category": category,
        "topic": topic,
        "modified_at": datetime.fromtimestamp(stat.st_mtime, timezone.utc).isoformat(),
        "size": stat.st_size,
        "starred": starred,
    }


def _load_report_stars(project_dir: Path) -> set[str]:
    try:
        data = state.load_state(project_dir)
    except (OSError, ValueError, json.JSONDecodeError):
        return set()
    stars = data.get("reportStars")
    if not isinstance(stars, dict):
        return set()
    return {path for path, value in stars.items() if isinstance(path, str) and value is True}


def report_starred(project_dir: Path, relative_path: str) -> bool | None:
    try:
        path = _report_path(project_dir, relative_path)
    except (OSError, ValueError):
        return None
    canonical = path.relative_to(project_dir).as_posix()
    return canonical in _load_report_stars(project_dir)


def _report_path(project_dir: Path, relative_path: str) -> Path:
    relative = Path(relative_path)
    allowed = relative.parts[:1] == ("reports",) or relative.parts[:2] == ("content", "reports")
    if relative.is_absolute() or not allowed or relative.suffix.lower() not in {".md", ".markdown"} or any(part.startswith(".") for part in relative.parts):
        raise ValueError("report path must be a visible Markdown file under reports/ or content/reports/")
    path = state.safe_project_path(project_dir, relative)
    if not path.is_file() or path.is_symlink():
        raise ValueError(f"report file not found: {relative.as_posix()}")
    return path


def _filter_sub_reports(
    sub_reports: list[dict[str, Any]],
    *,
    query: str,
    category: str,
    year: int | None,
    month: int | None,
) -> list[dict[str, Any]]:
    needle = query.strip().lower()
    if not needle and not category and year is None and month is None:
        return sub_reports
    filtered: list[dict[str, Any]] = []
    for report in sub_reports:
        if category and report["category"] != category:
            continue
        if year is not None and not report["date"].startswith(str(year)):
            continue
        if month is not None and int(report["date"][4:6]) != month:
            continue
        if needle and needle not in f"{report['topic']} {report['category']} {report['path']}".lower():
            continue
        filtered.append(report)
    return filtered


def _build_progress(weekly: list[dict[str, Any]]) -> dict[str, Any]:
    """Aggregate follow-up due dates and carried-over tracks across weeks.

    follow_ups are sorted by due date with a state projection (overdue /
    upcoming within 7 days / future). carried_over_tracks group the same
    task name appearing in two or more weekly archives' 遗留工作 sections
    (normalized task name matching; wording changes split tracks).
    """
    follow_ups: list[dict[str, Any]] = []
    tracks: dict[str, list[dict[str, Any]]] = {}
    today = date.today()
    for item in weekly:
        for follow_up in item.get("follow_ups", []):
            entry = {
                **follow_up,
                "year": item["year"],
                "week": item["week"],
                "path": item["path"],
                "state": _follow_up_state(follow_up["date"], today),
            }
            follow_ups.append(entry)
            task = _task_name(follow_up["text"])
            if task:
                tracks.setdefault(task, []).append({"year": item["year"], "week": item["week"], "path": item["path"]})
    follow_ups.sort(key=lambda entry: _parse_follow_date(entry["date"]))
    carried_over_tracks = [
        {"task": task, "entries": sorted(entries, key=lambda entry: (entry["year"], entry["week"])), "spans": len(entries)}
        for task, entries in tracks.items()
        if len(entries) >= 2
    ]
    carried_over_tracks.sort(key=lambda track: (track["entries"][-1]["year"], track["entries"][-1]["week"]), reverse=True)
    return {
        "follow_ups": follow_ups,
        "overdue": sum(1 for entry in follow_ups if entry["state"] == "overdue"),
        "upcoming": sum(1 for entry in follow_ups if entry["state"] == "upcoming"),
        "carried_over_tracks": carried_over_tracks,
    }


def _follow_up_state(raw: str, today: date) -> str:
    try:
        day = date.fromisoformat(raw.replace("/", "-"))
    except ValueError:
        return "unknown"
    diff = (day - today).days
    if diff < 0:
        return "overdue"
    if diff <= 7:
        return "upcoming"
    return "future"


def _parse_follow_date(raw: str) -> date:
    try:
        return date.fromisoformat(raw.replace("/", "-"))
    except ValueError:
        return date.max


def _task_name(text: str) -> str:
    bold = TASK_BOLD.search(text)
    if bold:
        return _normalize(bold.group(1))
    prefix = re.split(r"[：:]", text, maxsplit=1)[0]
    return _normalize(prefix)


def _normalize(value: str) -> str:
    return re.sub(r"\s+", "", value).strip().lower()


def _read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return ""


def _is_carry_over_section(section: str) -> bool:
    return section in {"遗留工作", "遗留", "遗留项"} or "遗留" in section


def _week_range(year: int, week: int) -> tuple[str, str]:
    monday = date.fromisocalendar(year, week, 1)
    return monday.strftime("%m-%d"), (monday + timedelta(days=6)).strftime("%m-%d")


def _target_iso_week(project_dir: Path, *, week: int | None, year: int | None) -> tuple[int, int]:
    if week is not None:
        year = year or date.today().year
        monday = date.fromisocalendar(year, week, 1)
        return monday.isocalendar().year, monday.isocalendar().week
    latest = _latest_weekly(project_dir)
    if latest is not None:
        target_year, target_week = latest
        if target_week == 53:
            return target_year + 1, 1
        return target_year, target_week + 1
    today = date.today().isocalendar()
    return today.year, today.week


def _latest_weekly(project_dir: Path) -> tuple[int, int] | None:
    reports_dir = state.safe_project_path(project_dir, "reports")
    found: list[tuple[int, int]] = []
    if reports_dir.is_dir() and not reports_dir.is_symlink():
        for path in reports_dir.iterdir():
            match = WEEKLY_PATTERN.match(path.name) if path.is_file() else None
            if match:
                found.append((int(match.group("year")), int(match.group("week"))))
    return max(found) if found else None


def _previous_weekly(project_dir: Path, *, before_year: int, before_week: int) -> tuple[int, int, Path] | None:
    reports_dir = state.safe_project_path(project_dir, "reports")
    if not reports_dir.is_dir() or reports_dir.is_symlink():
        return None
    candidates = [
        (int(match.group("year")), int(match.group("week")), path)
        for path in reports_dir.iterdir()
        if path.is_file() and (match := WEEKLY_PATTERN.match(path.name))
    ]
    previous = sorted(
        ((y, w) for y, w, _ in candidates if (y, w) < (before_year, before_week)),
        reverse=True,
    )
    if not previous:
        return None
    y, w = previous[0]
    return y, w, next(path for py, pw, path in candidates if (py, pw) == (y, w))


def _carry_over_items(previous_path: Path) -> list[str]:
    items: list[str] = []
    section = ""
    for line in _read_text(previous_path).splitlines():
        heading = re.match(r"^##\s+(\S+)", line)
        if heading:
            section = heading.group(1)
            continue
        if not _is_carry_over_section(section):
            continue
        if not CHECKBOX.match(line):
            continue
        item = line[line.index("]") + 1 :].strip().replace("**", "")
        if item and not item.startswith(">"):
            items.append(item)
    return items


def _render_weekly(project_dir: Path, *, year: int, week: int, carried: list[str], inherited_from: int | None = None) -> str:
    template = WEEKLY_TEMPLATE.read_text(encoding="utf-8") if WEEKLY_TEMPLATE.is_file() else _default_template()
    project_name = str((state.load_state(project_dir).get("project") or {}).get("name") or "")
    start, end = _week_range(year, week)
    content = (
        template.replace("# <项目名> 周报 · YYYY Week WW（MM-DD → MM-DD）", f"# {project_name} 周报 · {year} Week {week:02d}（{start} → {end}）")
        .replace("YYYY Week WW", f"{year} Week {week:02d}")
        .replace("`reports/YYYYMMDD_<category>_<topic>.md`", "`reports/YYYYMMDD_<category>_<topic>.md`")
    )
    if carried:
        lines = content.splitlines()
        insert_at = None
        for index, line in enumerate(lines):
            if line.startswith("## 速览"):
                insert_at = index + 1
                continue
            if insert_at is not None:
                if line.startswith("> "):
                    insert_at = index + 1
                    break
                if line.startswith("## "):
                    break
        if insert_at is not None:
            marker = f"（承接自 Week {inherited_from}）" if inherited_from is not None else ""
            carried_lines = [f"- [ ] {item}{marker}" for item in carried]
            lines[insert_at:insert_at] = [*carried_lines, ""]
            content = "\n".join(lines)
    return content.rstrip() + "\n"


def _default_template() -> str:
    return (
        "# <项目名> 周报 · YYYY Week WW（MM-DD → MM-DD）\n"
        "\n"
        "## 速览\n"
        "\n"
        "- [ ] 本周待办\n"
        "\n"
        "## 实质工作\n"
        "\n"
        "- 本周工作要点\n"
        "\n"
        "## 遗留工作\n"
        "\n"
        "- [ ] **遗留项**：原因；后续：YYYY-MM-DD 动作\n"
        "\n"
        "## 其他\n"
        "\n"
        "> 数据结论、决策与备注。\n"
    )
