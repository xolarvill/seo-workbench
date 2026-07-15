from __future__ import annotations

import tempfile
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator


@contextmanager
def atomic_output_path(path: Path, mode: int = 0o644) -> Iterator[Path]:
    """Yield a same-directory temporary path and atomically replace the target."""
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
            delete=False,
        ) as handle:
            temporary = Path(handle.name)
        yield temporary
        temporary.chmod(mode)
        temporary.replace(path)
        temporary = None
    finally:
        if temporary and temporary.exists():
            temporary.unlink()


def atomic_write_text(path: Path, content: str, mode: int = 0o644) -> None:
    with atomic_output_path(path, mode=mode) as temporary:
        temporary.write_text(content, encoding="utf-8")
