"""Walk a CNeuroMod videogame dataset and line up every game repetition.

The source of truth is each run's raw `func/*_events.tsv`: one `gym-retro_game`
row per repetition, in acquisition order, with the task clock `onset` and the
`stim_file` the row points to. Everything else (the .bk2, `_summary.json`,
`_variables.json`) is looked up from that row.
"""

from __future__ import annotations

import csv
import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterator

from .bk2 import Bk2Info, is_available, read_bk2

GAME_TRIAL = "gym-retro_game"

# Native console frame rates, as in videogames_utils.events.emit.TASK_FRAME_RATES
# (read from the emulator cores with retro's get_screen_rate()).
NATIVE_FPS = {
    "mario": 60.099826520671,
    "mario3": 60.099826520671,
    "mariostars": 60.098811862348,
    "shinobi": 59.922743404312,
}

_ENTITY = re.compile(r"([a-zA-Z0-9]+)-([a-zA-Z0-9]+)")


def entities(filename: str) -> dict[str, str]:
    stem = Path(filename).name.split(".")[0]
    return {k: v for k, v in _ENTITY.findall(stem)}


@dataclass
class Repetition:
    dataset: str
    sub: str
    ses: str
    run: str
    index_in_run: int  # position among the run's game rows, from 0
    row: int  # line of the events.tsv (0 = first data row)
    onset: float
    level: str
    stim_file: str  # as written in events.tsv
    duration: float | None  # task-logged play time (shinobi only)
    duration_bk2: float | None  # task-logged replay length, frames/60 (shinobi only)
    events_file: Path
    bk2: Bk2Info | None = None
    bk2_state: str = "ok"  # ok | blank | missing-flag | unavailable | not-found
    summary: dict | None = None
    others_between: int = 0  # non-game rows since the previous game row

    @property
    def key(self) -> str:
        return Path(self.stim_file).name.replace(".bk2", "") if self.stim_file else ""

    @property
    def gamelog_stem(self) -> Path | None:
        return self.bk2.path.with_suffix("") if self.bk2 else None

    def variables_path(self) -> Path | None:
        stem = self.gamelog_stem
        return Path(f"{stem}_variables.json") if stem else None


@dataclass
class Run:
    dataset: str
    sub: str
    ses: str
    run: str
    events_file: Path
    repetitions: list[Repetition] = field(default_factory=list)

    @property
    def label(self) -> str:
        return f"sub-{self.sub}_ses-{self.ses}_run-{self.run}"


def _float(value: str | None) -> float | None:
    try:
        return float(value) if value not in (None, "", "n/a") else None
    except ValueError:
        return None


def _resolve_bk2(root: Path, stim_file: str) -> tuple[Path | None, str]:
    s = stim_file.strip()
    if not s or s == "n/a":
        return None, "blank"
    if "missing" in s.lower():
        return None, "missing-flag"
    path = root / s
    if not path.is_symlink() and not path.exists():
        return None, "not-found"
    if not is_available(path):
        return None, "unavailable"
    return path, "ok"


def load_runs(root: str | Path, task: str | None = None) -> Iterator[Run]:
    root = Path(root)
    pattern = "sub-*/ses-*/func/*_events.tsv"
    for events_file in sorted(root.glob(pattern)):
        if "_desc-" in events_file.name:
            continue
        ent = entities(events_file.name)
        if task and ent.get("task") != task:
            continue
        if not events_file.exists():  # annexed and not fetched
            continue
        run = Run(
            dataset=ent.get("task", task or "?"),
            sub=ent["sub"],
            ses=ent["ses"],
            run=ent.get("run", "?"),
            events_file=events_file,
        )
        with events_file.open(newline="") as fh:
            rows = list(csv.DictReader(fh, delimiter="\t"))
        others = 0
        for i, r in enumerate(rows):
            if r.get("trial_type") != GAME_TRIAL:
                others += 1
                continue
            stim = r.get("stim_file") or ""
            rep = Repetition(
                dataset=run.dataset,
                sub=run.sub,
                ses=run.ses,
                run=run.run,
                index_in_run=len(run.repetitions),
                row=i,
                onset=float(r["onset"]),
                level=r.get("level", ""),
                stim_file=stim,
                duration=_float(r.get("duration")),
                duration_bk2=_float(r.get("duration_bk2")),
                events_file=events_file,
                others_between=others,
            )
            others = 0
            path, rep.bk2_state = _resolve_bk2(root, stim)
            if path is not None:
                rep.bk2 = read_bk2(path)
                summary = path.with_name(path.stem + "_summary.json")
                if summary.exists():
                    rep.summary = json.loads(summary.read_text())
            run.repetitions.append(rep)
        yield run


def all_bk2_files(root: str | Path, sub: str, ses: str) -> list[Path]:
    root = Path(root)
    return sorted(
        p for p in (root / f"sub-{sub}" / f"ses-{ses}").glob("*/*.bk2") if p.exists()
    )
