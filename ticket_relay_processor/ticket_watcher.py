"""Polling ticket watcher for discovering new ticket files."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Iterable, Set

from utils import is_file_stable

LOGGER = logging.getLogger(__name__)


class TicketWatcher:
    """Monitor a directory and return newly discovered ticket files."""

    def __init__(self, directory: Path, file_pattern: str = "*") -> None:
        """Create a watcher for a directory and optional glob pattern."""

        self.directory = directory
        self.file_pattern = file_pattern
        self._seen_files: Set[Path] = set()

    def ensure_directory(self) -> None:
        """Create the watch directory when it does not already exist."""

        self.directory.mkdir(parents=True, exist_ok=True)

    def poll(self) -> list[Path]:
        """Return stable files not previously emitted by this watcher."""

        self.ensure_directory()
        new_files: list[Path] = []

        for path in self._iter_candidate_files():
            resolved = path.resolve()
            if resolved in self._seen_files:
                continue
            if not is_file_stable(resolved):
                LOGGER.debug("Skipping unstable file: %s", resolved)
                continue
            self._seen_files.add(resolved)
            new_files.append(resolved)

        return sorted(new_files)

    def mark_unprocessed(self, path: Path) -> None:
        """Allow a file to be discovered again after an unsuccessful attempt."""

        self._seen_files.discard(path.resolve())

    def _iter_candidate_files(self) -> Iterable[Path]:
        """Yield regular files from the watched directory."""

        try:
            yield from (
                path
                for path in self.directory.glob(self.file_pattern)
                if path.is_file() and not path.name.startswith(".")
            )
        except OSError as exc:
            LOGGER.error("Unable to scan ticket directory %s: %s", self.directory, exc)
