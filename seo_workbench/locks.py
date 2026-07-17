from __future__ import annotations

import hashlib
import os
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from filelock import FileLock


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_LOCK_ROOT = ROOT / ".runtime" / "locks"


def _secure_directory(path: Path) -> None:
    if path.is_symlink():
        raise ValueError(f"lock directory cannot be a symlink: {path}")
    path.mkdir(parents=True, exist_ok=True)
    path.chmod(0o700)


def lock_path(project_dir: Path, lock_root: Path = DEFAULT_LOCK_ROOT) -> Path:
    _secure_directory(lock_root)
    identity = str(project_dir.resolve(strict=False)).encode("utf-8")
    digest = hashlib.sha256(identity).hexdigest()[:20]
    return lock_root / f"project-{digest}.lock"


@contextmanager
def project_lock(project_dir: Path, timeout: float = 30, lock_root: Path = DEFAULT_LOCK_ROOT) -> Iterator[None]:
    path = lock_path(project_dir, lock_root)
    lock = FileLock(path, timeout=timeout)
    with lock:
        if path.exists():
            os.chmod(path, 0o600)
        yield
