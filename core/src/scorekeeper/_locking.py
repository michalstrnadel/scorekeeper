"""Small cross-platform exclusive file lock helper."""

from __future__ import annotations

import contextlib
import sys
import threading
from collections.abc import Iterator
from pathlib import Path

if sys.platform == "win32":
    import msvcrt
else:
    import fcntl

# In-process serialization mirroring flock semantics for separate Store
# instances in one Python process (where Windows byte-range locks are less
# useful for the unit-test shape): blocking acquisition WAITS, exactly like
# flock across processes; only blocking=False raises. One threading.Lock per
# resolved path, guarded by a registry lock for thread safety.
_REGISTRY_GUARD = threading.Lock()
_PATH_LOCKS: dict[Path, threading.Lock] = {}


def _path_lock(resolved: Path) -> threading.Lock:
    with _REGISTRY_GUARD:
        lock = _PATH_LOCKS.get(resolved)
        if lock is None:
            lock = _PATH_LOCKS[resolved] = threading.Lock()
        return lock


@contextlib.contextmanager
def exclusive_file_lock(path: Path, blocking: bool = True) -> Iterator[None]:
    """Exclusive process/file lock with POSIX and Windows backends.

    ``blocking=True`` waits for the current holder (in-process or
    cross-process), matching ``flock``; ``blocking=False`` raises
    ``BlockingIOError`` when another writer already holds the lock.
    """
    resolved = path.resolve()
    plock = _path_lock(resolved)
    if not plock.acquire(blocking=blocking):
        raise BlockingIOError(str(path))
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a+b") as handle:
            _lock(handle, blocking)
            try:
                yield
            finally:
                _unlock(handle)
    finally:
        plock.release()


def _lock(handle, blocking: bool) -> None:
    if sys.platform == "win32":
        handle.seek(0)
        mode = msvcrt.LK_LOCK if blocking else msvcrt.LK_NBLCK
        try:
            msvcrt.locking(handle.fileno(), mode, 1)
        except OSError as exc:
            if not blocking:
                raise BlockingIOError(str(exc)) from exc
            raise
    else:
        fcntl.flock(handle, fcntl.LOCK_EX | (0 if blocking else fcntl.LOCK_NB))


def _unlock(handle) -> None:
    if sys.platform == "win32":
        handle.seek(0)
        msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
    else:
        fcntl.flock(handle, fcntl.LOCK_UN)
