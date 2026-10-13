"""Integrity checks over the game repetitions of a dataset.

Every check needs only what is public: the raw events.tsv, the .bk2 replays, and the
`_summary.json` / `_variables.json` files next to them. No emulator, no ROM.
"""

from __future__ import annotations

import hashlib
import json
import statistics
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable

from .bk2 import read_bk2
from .dataset import Repetition, Run, all_bk2_files, entities

TASK_CLOCK_FPS = 60.0  # `duration_bk2` is frames / 60 (task_stimuli)
CLOCK_TOLERANCE_S = 10.0  # zip timestamps have a 2 s resolution


@dataclass
class Finding:
    check: str
    severity: str  # error | warning
    where: str
    message: str
    evidence: dict = field(default_factory=dict)
    fix: str = ""


# --------------------------------------------------------------------------- refs

def check_references(run: Run) -> Iterable[Finding]:
    """events.tsv rows whose `stim_file` is blank instead of flagged (shinobi #31)."""
    for rep in run.repetitions:
        if rep.bk2_state == "blank":
            yield Finding(
                "blank-stim-file", "warning", f"{run.events_file.name} row {rep.row}",
                "gym-retro_game row has an empty stim_file instead of the 'Missing file' flag",
                {"onset": rep.onset, "level": rep.level},
                "write 'Missing file' (or n/a) like the other rows without a replay",
            )
        elif rep.bk2_state == "not-found":
            yield Finding(
                "stim-file-not-found", "error", f"{run.events_file.name} row {rep.row}",
                f"stim_file points to a file that is not in the dataset: {rep.stim_file}",
            )


def _content_key(path: Path) -> str:
    """git-annex key of an annexed file (it embeds the checksum), else the sha256."""
    if path.is_symlink():
        return path.resolve().name
    return hashlib.sha256(path.read_bytes()).hexdigest()


def check_unreferenced_replays(runs: list[Run], root: Path) -> Iterable[Finding]:
    """Replays that no events.tsv row points to, and replays stored twice.

    The pattern found in shinobi: when the first replay of a run was not saved, its
    row says 'Missing File', its `duration_bk2` repeats the length of the previous
    run's last replay, and a byte-identical copy of that replay sits under the new
    run's name. Anyone globbing gamelogs/ by run would pick up the wrong gameplay.
    """
    reps = [r for run in runs for r in run.repetitions]
    row_of = {r.bk2.path.name: r for r in reps if r.bk2}
    by_key: dict[str, list[Path]] = {}
    for path in sorted(root.glob("sub-*/ses-*/*/*.bk2")):
        if path.exists():
            by_key.setdefault(_content_key(path), []).append(path)

    for paths in by_key.values():
        used = [p for p in paths if p.name in row_of]
        unused = [p for p in paths if p.name not in row_of]
        if len(used) > 1:
            yield Finding(
                "duplicate-replay", "error", used[-1].stem,
                f"byte-identical to {used[0].name}, and both are referenced by events rows",
                {"files": [p.name for p in used],
                 "rows": [f"{row_of[p.name].events_file.name}:{row_of[p.name].row}"
                          for p in used]},
                "only one of these rows can own this gameplay",
            )
        for path in unused:
            info = read_bk2(path)
            evidence = {"frames": info.frames, "written_at": info.written_at.isoformat()}
            if used:
                orig = row_of[used[0].name]
                ent = entities(path.name)
                stale = [r for r in reps if r.sub == orig.sub and r.ses == orig.ses
                         and r.run == ent.get("run") and r.bk2 is None
                         and r.duration_bk2 is not None
                         and round(r.duration_bk2 * TASK_CLOCK_FPS) == info.frames]
                evidence.update(copy_of=used[0].name,
                                copy_of_row=f"{orig.events_file.name}:{orig.row}")
                if stale:
                    evidence.update(missing_row=f"{stale[0].events_file.name}:{stale[0].row}",
                                    missing_row_play_time_s=stale[0].duration,
                                    missing_row_logged_s=stale[0].duration_bk2)
                yield Finding(
                    "copy-under-other-run", "error", path.stem,
                    f"not referenced by any row, and byte-identical to {used[0].name}"
                    + (f"; row {stale[0].row} of {stale[0].events_file.name} says "
                       "'Missing File' and logs this copy's length, not its own"
                       if stale else ""),
                    evidence,
                    "delete the copy (or move it out of gamelogs/); the repetition it is "
                    "named after has no replay",
                )
            else:
                yield Finding(
                    "unreferenced-replay", "warning", path.stem,
                    "replay is in gamelogs/ but no events.tsv row points to it", evidence,
                )


# ------------------------------------------------------------------------- length

def check_length(run: Run, root: Path) -> Iterable[Finding]:
    """Replay length vs the length the task logged for that row (`duration_bk2`).

    When they disagree, look for the replay of the same session that does match:
    that is the file the row should point to (shinobi #44).
    """
    session_bk2 = None
    for rep in run.repetitions:
        if rep.bk2 is None or rep.duration_bk2 is None:
            continue
        expected = round(rep.duration_bk2 * TASK_CLOCK_FPS)
        if abs(rep.bk2.frames - expected) <= 1:
            continue
        if session_bk2 is None:
            session_bk2 = [read_bk2(p) for p in all_bk2_files(root, run.sub, run.ses)]
        matches = [b.path.name for b in session_bk2 if abs(b.frames - expected) <= 1]
        yield Finding(
            "length-mismatch", "error", rep.key,
            f"replay has {rep.bk2.frames} frames but the task logged {expected} "
            f"({rep.duration_bk2:.2f} s) for this row",
            {"row": rep.row, "onset": round(rep.onset, 3), "bk2_frames": rep.bk2.frames,
             "logged_frames": expected, "matching_files_in_session": matches},
            f"this row's replay is probably {matches[0]}" if len(matches) == 1 else "",
        )


# -------------------------------------------------------------------------- clock

def clock_residuals(run: Run) -> list[tuple[Repetition, float]]:
    """zip write time - (onset + replay length): constant within a run.

    The last repetition of a run is left out: its .bk2 is written later, when the
    next run starts or the session ends (122 of 126 shinobi runs), so its
    timestamp says nothing about where it sits in the run.
    """
    out = []
    for rep in run.repetitions[:-1]:
        if rep.bk2 is None:
            continue
        end = rep.onset + rep.bk2.frames / TASK_CLOCK_FPS
        out.append((rep, rep.bk2.written_at.timestamp() - end))
    return out


def check_clock(run: Run) -> Iterable[Finding]:
    res = clock_residuals(run)
    if len(res) < 3:  # with two points there is no telling which one is off
        return
    ref = statistics.median(r for _, r in res)
    for rep, r in res:
        if abs(r - ref) > CLOCK_TOLERANCE_S:
            yield Finding(
                "clock-mismatch", "error", rep.key,
                f"replay was written {r - ref:+.0f} s away from where this row's onset "
                f"puts its end (run median offset)",
                {"row": rep.row, "onset": round(rep.onset, 3),
                 "written_at": rep.bk2.written_at.isoformat(), "offset_s": round(r - ref, 1)},
                "the file is attached to the wrong row, or the row's onset is wrong",
            )


# ------------------------------------------------------------------------ outcome

def shinobi_rule(variables: dict) -> str:
    """Same rule as videogames_utils.events.outcome.shinobi_outcome."""
    lives = variables["lives"]
    lost = any(lives[i] < lives[i - 1] for i in range(1, len(lives)))
    return "failed" if lost else "cleared"


def check_shinobi_outcome(run: Run, level_end_x: dict[str, float]) -> Iterable[Finding]:
    """Outcome labels that the replay contradicts (shinobi #45 and new cases)."""
    for rep in run.repetitions:
        if rep.bk2 is None or rep.summary is None:
            continue
        vpath = rep.variables_path()
        if not vpath or not vpath.exists():
            continue
        v = json.loads(vpath.read_text())
        label = rep.summary.get("Outcome")
        rule = shinobi_rule(v)
        health, lives, x = v["health"], v["lives"], v["X_screen_total"]
        sections = v["section"]
        where = rep.key
        if label != rule:
            yield Finding(
                "outcome-disagrees-with-rule", "error", where,
                f"summary says '{label}' but outcome.py's rule gives '{rule}' for this replay",
                {"lives_first": lives[0], "lives_min": min(lives), "lives_last": lives[-1],
                 "frames": len(lives)},
                "regenerate the summary from the committed code (videogames_utils #5)",
            )
        if label != "cleared":
            continue
        if health[-1] == 0:
            first_zero = health.index(0)
            yield Finding(
                "death-labelled-cleared", "error", where,
                f"health reaches 0 at frame {first_zero} and the replay ends "
                f"{len(health) - first_zero} frames later, before a life is taken off",
                {"health_zero_frame": first_zero, "frames": len(health),
                 "status_last": v["status"][-1], "X_screen_total_last": x[-1]},
                "treat health == 0 as a death in shinobi_outcome (failed/killed)",
            )
        elif rep.level.startswith("4") and sections[-1] == sections[0] \
                and x[-1] < 0.95 * level_end_x.get("4", float("inf")):
            yield Finding(
                "stopped-mid-level-labelled-cleared", "error", where,
                f"no death and no section change, but the replay stops at "
                f"X_screen_total {x[-1]} (level end ~{level_end_x['4']:.0f})",
                {"frames": len(x), "health_last": health[-1], "status_last": v["status"][-1],
                 "X_screen_total_last": x[-1]},
                "label as incomplete/interrupted (shinobi #45)",
            )


def shinobi_level_end_x(runs: list[Run]) -> dict[str, float]:
    """Median final X_screen_total of level-4 repetitions that advanced a section."""
    finals = []
    for run in runs:
        for rep in run.repetitions:
            vpath = rep.variables_path()
            if rep.level.startswith("4") and vpath and vpath.exists():
                v = json.loads(vpath.read_text())
                if v["section"][-1] > v["section"][0]:
                    finals.append(v["X_screen_total"][-1])
    return {"4": statistics.median(finals)} if finals else {}


# ------------------------------------------------------------------------ summary

def summary_schema(runs: list[Run]) -> dict[tuple[str, ...], int]:
    """Distinct `_summary.json` key sets in a dataset (videogames_utils #6)."""
    keys: dict[tuple[str, ...], int] = {}
    for run in runs:
        for rep in run.repetitions:
            if rep.summary is not None:
                k = tuple(rep.summary)
                keys[k] = keys.get(k, 0) + 1
    return keys


def run_all(runs: list[Run], root: Path, task: str) -> list[Finding]:
    findings: list[Finding] = []
    end_x = shinobi_level_end_x(runs) if task == "shinobi" else {}
    for run in runs:
        findings += check_references(run)
        findings += check_length(run, root)
        findings += check_clock(run)
        if task == "shinobi":
            findings += check_shinobi_outcome(run, end_x)
    findings += check_unreferenced_replays(runs, root)
    return findings
