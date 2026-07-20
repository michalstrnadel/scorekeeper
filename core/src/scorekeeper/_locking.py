"""Small cross-platform exclusive file lock helper."""

from __future__ import annotations

import contextlib
import os
from collections.abc import Iterator
from pathlib import Path

if os.name == "nt":
    import msvcrt
else:
    import fcntl

_HELD_LOCKS: set[Path] = set()


@contextlib.contextmanager
def exclusive_file_lock(path: Path, blocking: bool = True) -> Iterator[None]:
    """Exclusive process/file lock with POSIX and Windows backends.

    ``blocking=False`` raises ``BlockingIOError`` when another writer already
    holds the lock. The in-process registry mirrors that behavior for separate
    Store instances in one Python process, where Windows byte-range locks are
    otherwise less useful for the unit-test shape.
    """
    resolved = path.resolve()
    if resolved in _HELD_LOCKS:
        raise BlockingIOError(str(path))

    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a+b") as handle:
        _lock(handle, blocking)
        _HELD_LOCKS.add(resolved)
        try:
            yield
        finally:
            _HELD_LOCKS.discard(resolved)
            _unlock(handle)


def _lock(handle, blocking: bool) -> None:
    if os.name == "nt":
        handle.seek(0)
        mode = msvcrt.LK_LOCK if blocking else msvcrt.LK_NBLCK
        try:
            msvcrt.locking(handle.fileno(), mode, 1)
        except OSError as exc:
            if not blocking:
                raise BlockingIOError(str(exc)) from exc
            raise
    else:
        lock_ex = fcntl.LOCK_EX  # type: ignore[attr-defined]
        lock_nb = fcntl.LOCK_NB  # type: ignore[attr-defined]
        fcntl.flock(  # type: ignore[attr-defined]
            handle, lock_ex | (0 if blocking else lock_nb)
        )


def _unlock(handle) -> None:
    if os.name == "nt":
        handle.seek(0)
        msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
    else:
        lock_un = fcntl.LOCK_UN  # type: ignore[attr-defined]
        fcntl.flock(handle, lock_un)  # type: ignore[attr-defined]
