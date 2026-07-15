from __future__ import annotations

import argparse
import os
import shutil
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
LOCAL_BROWSERS = ROOT / ".runtime/playwright"


def browser_executable() -> str:
    configured = os.environ.get("CHROME_PATH", "").strip()
    if configured:
        path = Path(configured).expanduser()
        if path.is_file() and os.access(path, os.X_OK):
            return str(path)
        raise RuntimeError(f"CHROME_PATH does not point to an executable file: {path}")

    os.environ.setdefault("PLAYWRIGHT_BROWSERS_PATH", str(LOCAL_BROWSERS))
    try:
        from playwright.sync_api import sync_playwright

        playwright = sync_playwright().start()
        try:
            path = Path(playwright.chromium.executable_path)
        finally:
            playwright.stop()
        if path.is_file() and os.access(path, os.X_OK):
            return str(path)
    except Exception:
        pass

    candidates = [
        Path("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"),
        Path("/Applications/Chromium.app/Contents/MacOS/Chromium"),
    ]
    for name in ("google-chrome", "google-chrome-stable", "chromium", "chromium-browser"):
        if executable := shutil.which(name):
            candidates.append(Path(executable))
    for path in candidates:
        if path.is_file() and os.access(path, os.X_OK):
            return str(path)
    raise RuntimeError("Chrome or Chromium is required; run ./setup.sh")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Resolve the browser used by SEO Workbench probes.")
    parser.add_argument("--print", action="store_true", dest="print_path")
    args = parser.parse_args(argv)
    try:
        path = browser_executable()
    except RuntimeError as exc:
        parser.exit(1, f"{exc}\n")
    if args.print_path:
        print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
