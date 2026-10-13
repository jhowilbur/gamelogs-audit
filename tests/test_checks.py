"""Checks on a synthetic dataset built from scratch: zips for .bk2, tsv for events."""

import json
import zipfile
from datetime import datetime, timedelta
from pathlib import Path

import pytest

from gamelogs_audit import framerate
from gamelogs_audit.bk2 import read_bk2
from gamelogs_audit.checks import (
    check_clock, check_length, check_references, check_shinobi_outcome,
    check_unreferenced_replays,
)
from gamelogs_audit.dataset import load_runs

T0 = datetime(2020, 9, 21, 15, 0, 0)
HEADER = "trial_type\tonset\tduration\tduration_bk2\tlevel\tstim_file\n"


def write_bk2(path: Path, frames: int, written_at: datetime) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    log = "[Input]\nP1 B|P1 A|\n" + "|..|\n" * frames + "[/Input]\n"
    with zipfile.ZipFile(path, "w") as zf:
        zf.writestr(zipfile.ZipInfo("Input Log.txt", written_at.timetuple()[:6]), log)


class Session:
    """Builds sub-01/ses-001 with runs of (level, frames) played back to back."""

    def __init__(self, root: Path, fps: float = 60.0, pause: float = 6.0):
        self.root, self.fps, self.pause = root, fps, pause
        self.ses = root / "sub-01" / "ses-001"
        self.clock = T0

    def name(self, run, level, rep):
        return f"sub-01_ses-001_task-shinobi_run-{run}_level-{level}_rep-{rep:02d}.bk2"

    def run(self, run: str, plays, attach=None, missing=()):
        """plays: [(level, frames)]. attach: {i: file name} overrides the row's file."""
        rows, onset = [HEADER], 0.0
        for i, (level, frames) in enumerate(plays):
            name = self.name(run, level, i + 1)
            length = frames / self.fps
            end = self.clock + timedelta(seconds=onset + length)
            if i not in missing:
                write_bk2(self.ses / "gamelogs" / name, frames, end)
            stim = "Missing File" if i in missing else \
                f"sub-01/ses-001/gamelogs/{(attach or {}).get(i, name)}"
            rows.append(f"gym-retro_game\t{onset}\t{length}\t{frames / 60}\t{level}-0\t{stim}\n")
            onset += length + self.pause
        events = self.ses / "func" / f"sub-01_ses-001_task-shinobi_run-{run}_events.tsv"
        events.parent.mkdir(parents=True, exist_ok=True)
        events.write_text("".join(rows))
        self.clock += timedelta(seconds=onset + 60)
        return self

    def runs(self):
        return list(load_runs(self.root))


def test_bk2_frames_and_time(tmp_path):
    write_bk2(tmp_path / "a.bk2", 1234, T0)
    info = read_bk2(tmp_path / "a.bk2")
    assert (info.frames, info.written_at) == (1234, T0)


def test_clean_session_has_no_findings(tmp_path):
    s = Session(tmp_path).run("01", [(1, 9000), (4, 8000), (5, 7000), (1, 9500)])
    (run,) = s.runs()
    assert list(check_length(run, tmp_path)) == []
    assert list(check_clock(run)) == []
    assert list(check_references(run)) == []
    assert list(check_unreferenced_replays(s.runs(), tmp_path)) == []


def test_swapped_files_are_found_with_their_right_owner(tmp_path):
    s = Session(tmp_path)
    s.run("01", [(1, 9000), (4, 8000), (5, 7000), (1, 9500)])
    s.run("02", [(1, 9100), (4, 4000), (5, 7100), (1, 9600)],
          attach={1: s.name("01", 4, 2)})  # run-02's level-4 row points to run-01's file
    run02 = s.runs()[1]
    (f,) = check_length(run02, tmp_path)
    assert f.check == "length-mismatch"
    assert f.evidence["bk2_frames"] == 8000 and f.evidence["logged_frames"] == 4000
    assert f.evidence["matching_files_in_session"] == [s.name("02", 4, 2)]


def test_clock_flags_a_file_from_another_time(tmp_path):
    s = Session(tmp_path).run("01", [(1, 9000), (4, 8000), (5, 7000), (1, 9500)])
    late = s.ses / "gamelogs" / s.name("01", 4, 2)
    write_bk2(late, 8000, read_bk2(late).written_at + timedelta(seconds=90))
    (f,) = check_clock(s.runs()[0])
    assert f.where == late.stem and f.evidence["offset_s"] == pytest.approx(90, abs=3)


def test_last_replay_of_run_is_not_clock_checked(tmp_path):
    # the task writes the run's last .bk2 later, at the next run or the session end
    s = Session(tmp_path).run("01", [(1, 9000), (4, 8000), (5, 7000), (1, 9500)])
    last = s.ses / "gamelogs" / s.name("01", 1, 4)
    write_bk2(last, 9500, read_bk2(last).written_at + timedelta(minutes=30))
    assert list(check_clock(s.runs()[0])) == []


def test_copy_of_previous_run_under_new_run_name(tmp_path):
    s = Session(tmp_path)
    s.run("01", [(1, 9000), (4, 8000), (5, 7000), (1, 9500)])
    s.run("02", [(1, 9400), (4, 8100), (5, 7200)], missing={0})
    # the task left run-01's last replay under run-02's name, and logged its length
    src = s.ses / "gamelogs" / s.name("01", 1, 4)
    copy = s.ses / "gamelogs" / s.name("02", 1, 4)
    copy.write_bytes(src.read_bytes())
    events = s.ses / "func" / "sub-01_ses-001_task-shinobi_run-02_events.tsv"
    lines = events.read_text().splitlines(keepends=True)
    cols = lines[1].split("\t")
    cols[3] = str(9500 / 60)  # stale duration_bk2
    lines[1] = "\t".join(cols)
    events.write_text("".join(lines))

    (f,) = check_unreferenced_replays(s.runs(), tmp_path)
    assert f.check == "copy-under-other-run" and f.where == copy.stem
    assert f.evidence["copy_of"] == src.name
    assert f.evidence["missing_row"] == f"{events.name}:0"


def test_blank_stim_file(tmp_path):
    s = Session(tmp_path).run("01", [(1, 9000), (4, 8000)])
    events = s.ses / "func" / "sub-01_ses-001_task-shinobi_run-01_events.tsv"
    events.write_text(events.read_text().replace("sub-01/ses-001/gamelogs/" + s.name("01", 4, 2), ""))
    (f,) = check_references(s.runs()[0])
    assert f.check == "blank-stim-file"


@pytest.mark.parametrize("fps", [60.0, 60.0988, 59.9227])
def test_frame_rate_is_recovered_from_onsets(tmp_path, fps):
    s = Session(tmp_path, fps=fps)
    s.run("01", [(1, 9000), (4, 8000), (5, 7000), (1, 9500), (4, 6000)])
    s.run("02", [(1, 8800), (4, 7600), (5, 7300), (1, 9900), (4, 5000)])
    (gaps, logged) = framerate.estimate(s.runs())
    assert gaps.median == pytest.approx(fps, abs=1e-3)
    assert logged.median == pytest.approx(fps, abs=1e-3)


def _variables(path: Path, lives, health, x, section):
    path.write_text(json.dumps({"lives": lives, "health": health, "X_screen_total": x,
                                "section": section, "status": [0] * len(lives)}))


def _summary(path: Path, outcome):
    path.write_text(json.dumps({"Outcome": outcome}))


def test_shinobi_outcome_checks(tmp_path):
    s = Session(tmp_path).run("01", [(4, 100), (4, 100), (4, 100)])
    g = s.ses / "gamelogs"
    stems = [g / s.name("01", 4, i).replace(".bk2", "") for i in (1, 2, 3)]
    # finished the level
    _variables(Path(f"{stems[0]}_variables.json"), [2] * 100, [16] * 100,
               list(range(8800, 8900)), [1] * 99 + [2])
    # stopped mid-level, full health, no death
    _variables(Path(f"{stems[1]}_variables.json"), [2] * 100, [16] * 100,
               list(range(3200, 3300)), [1] * 100)
    # health hit 0, replay ended before the life counter dropped
    _variables(Path(f"{stems[2]}_variables.json"), [2] * 100, [5] * 60 + [0] * 40,
               list(range(6000, 6100)), [1] * 100)
    for stem in stems:
        _summary(Path(f"{stem}_summary.json"), "cleared")

    (run,) = s.runs()
    got = {f.where: f.check for f in check_shinobi_outcome(run, {"4": 8899})}
    assert got == {stems[1].name: "stopped-mid-level-labelled-cleared",
                   stems[2].name: "death-labelled-cleared"}
