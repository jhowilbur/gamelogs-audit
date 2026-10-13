"""Read what a .bk2 replay says about itself, without an emulator or a ROM.

A .bk2 is a zip archive. `Input Log.txt` holds one `|...|` line per emulated
frame, so the replay length is a line count. The zip entries carry the
wall-clock time the archive was written, which is the end of the repetition.
"""

from __future__ import annotations

import zipfile
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

INPUT_LOG = "Input Log.txt"


@dataclass(frozen=True)
class Bk2Info:
    path: Path
    frames: int
    written_at: datetime  # local time of the acquisition PC, 2 s resolution


def read_bk2(path: str | Path) -> Bk2Info:
    path = Path(path)
    with zipfile.ZipFile(path) as zf:
        entry = zf.getinfo(INPUT_LOG)
        text = zf.read(entry).decode("ascii", errors="replace")
    frames = sum(1 for line in text.splitlines() if line.startswith("|"))
    return Bk2Info(path=path, frames=frames, written_at=datetime(*entry.date_time))


def is_available(path: str | Path) -> bool:
    """False for git-annex symlinks whose content was not fetched (e.g. sub-04)."""
    return Path(path).exists()
