from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from seo_workbench_tools.evidence_bundle import DEFAULT_OUTPUT_DIR, collect, write_bundle


DEFAULT_STATE = Path("projects/default/state.json")


def page_urls_from_state(state: dict[str, Any]) -> list[str]:
    urls = []
    for item in state.get("contentQueue", []):
        url = item.get("url") or item.get("publishedUrl") or item.get("published_url")
        if url and item.get("status") in {"published", "draft"}:
            urls.append(url)
    return urls


def collect_from_state(
    state_path: Path,
    timeout: float,
    sample_limit: int,
    output_dir: Path,
    rendered: bool = False,
    technology: bool = False,
    performance: bool = False,
    performance_runs: int = 5,
    performance_form_factor: str = "mobile",
) -> Path:
    state = json.loads(state_path.read_text(encoding="utf-8"))
    url = state.get("project", {}).get("url")
    if not url:
        raise ValueError(f"missing project.url in {state_path}")
    bundle = collect(
        url,
        page_urls_from_state(state),
        timeout,
        sample_limit,
        rendered=rendered,
        rendered_output_dir=output_dir.parent / "rendered",
        project_type=state.get("project", {}).get("type", ""),
        technology=technology,
        technology_output_dir=output_dir.parent / "technology",
        performance=performance,
        performance_output_dir=output_dir.parent / "performance",
        performance_runs=performance_runs,
        performance_form_factor=performance_form_factor,
    )
    bundle["state_path"] = str(state_path)
    return write_bundle(bundle, output_dir)


def _self_test() -> None:
    state = {
        "contentQueue": [
            {"status": "published", "url": "https://example.com/a"},
            {"status": "planned", "url": "https://example.com/b"},
            {"status": "draft", "publishedUrl": "https://example.com/c"},
        ]
    }
    assert page_urls_from_state(state) == ["https://example.com/a", "https://example.com/c"]


def main(argv: list[str] | None = None) -> int:
    argp = argparse.ArgumentParser(description="Collect evidence using projects/default/state.json.")
    argp.add_argument("--state", type=Path, default=DEFAULT_STATE)
    argp.add_argument("--timeout", type=float, default=15)
    argp.add_argument("--sample-limit", type=int, default=50)
    argp.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    argp.add_argument("--rendered", action="store_true")
    argp.add_argument("--technology", action="store_true")
    argp.add_argument("--performance", action="store_true")
    argp.add_argument("--performance-runs", type=int, default=5)
    argp.add_argument("--performance-form-factor", choices=["mobile", "desktop"], default="mobile")
    argp.add_argument("--self-test", action="store_true")
    args = argp.parse_args(argv)

    if args.self_test:
        _self_test()
        return 0

    try:
        path = collect_from_state(
            args.state,
            args.timeout,
            args.sample_limit,
            args.output_dir,
            rendered=args.rendered,
            technology=args.technology,
            performance=args.performance,
            performance_runs=args.performance_runs,
            performance_form_factor=args.performance_form_factor,
        )
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        raise SystemExit(str(exc)) from exc
    print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
