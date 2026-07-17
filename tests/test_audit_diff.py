import json
import shutil
from pathlib import Path

from seo_workbench import state
from seo_workbench.audit_diff import (
    compare_performance,
    compare_raw,
    compare_technology,
    create_diff,
    snapshot_pair,
    snapshots,
)


def raw_snapshot(generated_at: str, title: str, status: int, missing_alt: int, errors: int) -> dict:
    return {
        "schema_version": "1.0",
        "collector_version": "0.6.0",
        "generated_at": generated_at,
        "seed_url": "https://example.com/",
        "pages": [
            {
                "url": "https://example.com/",
                "final_url": "https://example.com/",
                "status": status,
                "title": title,
                "meta_description": "Description",
                "canonical": "https://example.com/",
                "robots_meta": "index,follow",
                "h1": ["Example"],
                "word_count": 100,
                "robots_meta_audit": {"indexable": True},
                "canonical_audit": {"issues": []},
                "schema_audit": {"schema_types_found": ["Organization"]},
                "image_stats": {"missing_alt": missing_alt, "missing_dimensions": 0},
                "link_summary": {"anchor_count": 10, "internal_count": 8},
            }
        ],
        "errors": [{"error": "old"}] * errors,
    }


def performance_snapshot(score: float, lcp: float, browser: str = "Chrome 149", runs: int = 5) -> dict:
    metrics = {
        "first-contentful-paint": {"median": 800},
        "largest-contentful-paint": {"median": lcp},
        "speed-index": {"median": 1000},
        "total-blocking-time": {"median": 0},
        "cumulative-layout-shift": {"median": 0},
        "interactive": {"median": 900},
    }
    return {
        "schema_version": "1.0",
        "runner_version": "0.1.0",
        "generated_at": "2026-07-15T00:00:00Z",
        "url": "https://example.com/",
        "requested_url": "https://example.com/",
        "final_url": "https://example.com/",
        "lighthouse_version": "13.4.0",
        "form_factor": "mobile",
        "runs_succeeded": runs,
        "runs_requested": runs,
        "aggregate": {
            "performance_score": {"median": score},
            "metrics": metrics,
            "high_variance": False,
        },
        "environment": {"browser_version": browser, "benchmark_index": 2000},
    }


def test_performance_diff_rejects_different_final_navigation_targets() -> None:
    baseline = performance_snapshot(90, 1000)
    current = performance_snapshot(80, 1500)
    current["final_url"] = "https://example.com/mobile/"
    changes, warnings, comparable = compare_performance(baseline, current)
    assert comparable is False
    assert any("final_url differs" in warning for warning in warnings)
    assert all(item["classification"] == "change" for item in changes)


def write_snapshot(path: Path, data: dict) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data), encoding="utf-8")
    return path


def test_raw_diff_classifies_status_and_image_changes() -> None:
    baseline = raw_snapshot("2026-07-15T00:00:00Z", "Old", 200, 2, 1)
    current = raw_snapshot("2026-07-16T00:00:00Z", "New", 500, 0, 0)
    changes, warnings, comparable = compare_raw(baseline, current)
    classifications = {(item["field"], item["classification"]) for item in changes}
    assert comparable is True
    assert warnings == []
    assert ("status", "regression") in classifications
    assert ("image_stats.missing_alt", "improvement") in classifications
    assert ("error_count", "improvement") in classifications


def test_technology_diff_tracks_presence_and_version() -> None:
    baseline = {
        "schema_version": "1.0",
        "detector_version": "0.1.0",
        "provider": "wappalyzer",
        "provider_version": "1",
        "pages": [{"url": "https://example.com", "technologies": [{"name": "React", "version": "18"}]}],
    }
    current = {
        "schema_version": "1.0",
        "detector_version": "0.1.0",
        "provider": "wappalyzer",
        "provider_version": "1",
        "pages": [
            {
                "url": "https://example.com",
                "technologies": [{"name": "React", "version": "19"}, {"name": "Vite", "version": "7"}],
            }
        ],
    }
    changes, warnings, comparable = compare_technology(baseline, current)
    assert comparable is True
    assert warnings == []
    assert {(item["field"], item["key"]) for item in changes} == {
        ("version", "https://example.com::React"),
        ("presence", "https://example.com::Vite"),
    }


def test_performance_diff_requires_comparable_environment() -> None:
    baseline = performance_snapshot(92, 1000)
    current = performance_snapshot(86, 1250)
    changes, warnings, comparable = compare_performance(baseline, current)
    assert comparable is True
    assert warnings == []
    assert {item["field"] for item in changes if item["classification"] == "regression"} == {
        "performance_score",
        "largest-contentful-paint",
    }

    incompatible = performance_snapshot(80, 1500, browser="Chrome 150")
    changes, warnings, comparable = compare_performance(baseline, incompatible)
    assert comparable is False
    assert any("browser_version" in warning for warning in warnings)
    assert all(item["classification"] == "change" for item in changes)


def test_create_diff_uses_latest_two_immutable_snapshots(tmp_path: Path) -> None:
    project_dir = tmp_path / "projects/store"
    state.init_state("shopify", "Store", "https://example.com", project_dir=project_dir)
    raw_dir = project_dir / "audits/raw"
    write_snapshot(raw_dir / "evidence-old.json", raw_snapshot("2026-07-15T00:00:00Z", "Old", 200, 1, 0))
    write_snapshot(raw_dir / "evidence-new.json", raw_snapshot("2026-07-16T00:00:00Z", "New", 200, 0, 0))

    report, output_path = create_diff(project_dir, kind="all")
    assert report["collection_status"] == "partial"
    assert report["comparisons"]["raw"]["status"] == "ok"
    assert report["comparisons"]["technology"]["status"] == "no_data"
    assert report["summary"]["improvements"] == 1
    assert output_path.exists()
    assert (project_dir / "audits/diffs/latest.json").exists()


def test_explicit_snapshots_cannot_cross_project_boundary(tmp_path: Path) -> None:
    project_dir = tmp_path / "projects/store"
    state.init_state("shopify", "Store", "https://example.com", project_dir=project_dir)
    outside = write_snapshot(tmp_path / "outside.json", raw_snapshot("2026-07-15T00:00:00Z", "Old", 200, 0, 0))
    inside = write_snapshot(
        project_dir / "audits/raw/evidence-new.json",
        raw_snapshot("2026-07-16T00:00:00Z", "New", 200, 0, 0),
    )
    try:
        snapshot_pair(project_dir, "raw", outside, inside)
    except ValueError as exc:
        assert "inside" in str(exc)
    else:
        raise AssertionError("expected cross-project snapshot to fail")


def test_snapshot_discovery_ignores_external_symlinks(tmp_path: Path) -> None:
    project_dir = tmp_path / "projects/store"
    state.init_state("shopify", "Store", "https://example.com", project_dir=project_dir)
    outside = write_snapshot(tmp_path / "evidence-outside.json", raw_snapshot("2026-07-15T00:00:00Z", "Old", 200, 0, 0))
    (project_dir / "audits/raw/evidence-link.json").symlink_to(outside)
    assert snapshots(project_dir, "raw") == []


def test_explicit_pair_must_use_distinct_files(tmp_path: Path) -> None:
    project_dir = tmp_path / "projects/store"
    state.init_state("shopify", "Store", "https://example.com", project_dir=project_dir)
    snapshot = write_snapshot(
        project_dir / "audits/raw/evidence-one.json",
        raw_snapshot("2026-07-15T00:00:00Z", "Old", 200, 0, 0),
    )
    try:
        snapshot_pair(project_dir, "raw", snapshot, snapshot)
    except ValueError as exc:
        assert "different" in str(exc)
    else:
        raise AssertionError("expected identical snapshots to fail")


def test_explicit_pair_must_share_audit_identity(tmp_path: Path) -> None:
    project_dir = tmp_path / "projects/store"
    state.init_state("shopify", "Store", "https://example.com", project_dir=project_dir)
    baseline_data = raw_snapshot("2026-07-15T00:00:00Z", "Old", 200, 0, 0)
    current_data = raw_snapshot("2026-07-16T00:00:00Z", "New", 200, 0, 0)
    current_data["seed_url"] = "https://other.example/"
    current_data["pages"][0]["url"] = "https://other.example/"
    baseline = write_snapshot(project_dir / "audits/raw/evidence-old.json", baseline_data)
    current = write_snapshot(project_dir / "audits/raw/evidence-new.json", current_data)
    try:
        snapshot_pair(project_dir, "raw", baseline, current)
    except ValueError as exc:
        assert "audit identity" in str(exc)
    else:
        raise AssertionError("expected cross-target snapshots to fail")


def test_diff_output_rejects_symlink_directory(tmp_path: Path) -> None:
    project_dir = tmp_path / "projects/store"
    state.init_state("shopify", "Store", "https://example.com", project_dir=project_dir)
    diff_dir = project_dir / "audits/diffs"
    diff_dir.rmdir()
    outside = tmp_path / "outside"
    outside.mkdir()
    diff_dir.symlink_to(outside, target_is_directory=True)
    try:
        create_diff(project_dir)
    except ValueError as exc:
        assert "symlink" in str(exc)
    else:
        raise AssertionError("expected symlinked diff output to fail")


def test_snapshot_pair_uses_latest_matching_audit_identity(tmp_path: Path) -> None:
    project_dir = tmp_path / "projects/store"
    state.init_state("shopify", "Store", "https://example.com", project_dir=project_dir)
    performance_dir = project_dir / "audits/performance"
    mobile_old = performance_snapshot(90, 1000)
    mobile_old["generated_at"] = "2026-07-15T00:00:00Z"
    desktop = performance_snapshot(95, 800)
    desktop["generated_at"] = "2026-07-16T00:00:00Z"
    desktop["form_factor"] = "desktop"
    mobile_new = performance_snapshot(85, 1300)
    mobile_new["generated_at"] = "2026-07-17T00:00:00Z"
    old_path = write_snapshot(performance_dir / "performance-mobile-old/summary.json", mobile_old)
    write_snapshot(performance_dir / "performance-desktop/summary.json", desktop)
    new_path = write_snapshot(performance_dir / "performance-mobile-new/summary.json", mobile_new)

    assert snapshot_pair(project_dir, "performance") == (old_path, new_path)


def test_page_collection_error_does_not_create_false_content_or_technology_removals() -> None:
    raw_before = raw_snapshot("2026-07-15T00:00:00Z", "Title", 200, 0, 0)
    raw_after = raw_snapshot("2026-07-16T00:00:00Z", "", 0, 0, 1)
    raw_after["pages"][0] = {"url": "https://example.com/", "error": "timeout"}
    raw_changes, _, _ = compare_raw(raw_before, raw_after)
    assert {item["field"] for item in raw_changes} == {"collection_error", "error_count"}

    tech_before = {
        "schema_version": "1.0",
        "detector_version": "0.1.0",
        "provider": "wappalyzer",
        "provider_version": "1",
        "pages": [{"url": "https://example.com/", "technologies": [{"name": "React", "version": "19"}]}],
    }
    tech_after = {
        **tech_before,
        "pages": [{"url": "https://example.com/", "error": "timeout", "technologies": []}],
    }
    tech_changes, _, _ = compare_technology(tech_before, tech_after)
    assert [item["field"] for item in tech_changes] == ["collection_error"]


def test_contract_version_mismatch_is_not_comparable() -> None:
    baseline = performance_snapshot(90, 1000)
    current = performance_snapshot(80, 1500)
    current["runner_version"] = "0.2.0"
    changes, warnings, comparable = compare_performance(baseline, current)
    assert comparable is False
    assert any("runner_version" in warning for warning in warnings)
    assert all(item["classification"] == "change" for item in changes)


def test_audit_parent_symlink_is_rejected_before_snapshot_read(tmp_path: Path) -> None:
    project_dir = tmp_path / "projects/store"
    state.init_state("shopify", "Store", "https://example.com", project_dir=project_dir)
    audits_dir = project_dir / "audits"
    for child in sorted(audits_dir.iterdir(), reverse=True):
        shutil.rmtree(child)
    audits_dir.rmdir()
    outside = tmp_path / "outside-audits"
    (outside / "raw").mkdir(parents=True)
    audits_dir.symlink_to(outside, target_is_directory=True)
    try:
        snapshots(project_dir, "raw")
    except ValueError as exc:
        assert "symlink" in str(exc)
    else:
        raise AssertionError("expected symlinked audits directory to fail")
