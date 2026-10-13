"""gamelogs-audit DATASET_ROOT [--task shinobi] [--out report/]

Writes report.md (for people) and findings.json (for CI) and exits 1 when there is
any error-level finding, so it can run as a GitHub Action on every push.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from dataclasses import asdict
from pathlib import Path

from . import framerate
from .checks import run_all, summary_schema
from .dataset import NATIVE_FPS, load_runs

CHECK_DOCS = {
    "length-mismatch": "the attached replay's length differs from the length the task "
                       "logged for the row (`duration_bk2`)",
    "clock-mismatch": "the replay was written at a time that does not fit the row's onset",
    "copy-under-other-run": "an unreferenced replay is a byte-identical copy of another "
                            "run's replay",
    "duplicate-replay": "two rows point to byte-identical replays",
    "unreferenced-replay": "a replay no events row points to",
    "death-labelled-cleared": "health reaches 0 but the summary says `cleared`",
    "stopped-mid-level-labelled-cleared": "the replay stops mid-level with no death, "
                                          "summary says `cleared`",
    "outcome-disagrees-with-rule": "the shipped summary's Outcome differs from what "
                                   "`outcome.py` computes from the same replay",
    "blank-stim-file": "a game row with an empty `stim_file` instead of the "
                       "'Missing file' flag",
    "stim-file-not-found": "`stim_file` points to a file that is not in the dataset",
}


def _infer_task(root: Path) -> str:
    for events in root.glob("sub-*/ses-*/func/*_events.tsv"):
        for part in events.name.split("_"):
            if part.startswith("task-"):
                return part[5:]
    raise SystemExit(f"no sub-*/ses-*/func/*_events.tsv under {root}")


def render(task, runs, findings, rates, schema) -> str:
    reps = [r for run in runs for r in run.repetitions]
    states = Counter(r.bk2_state for r in reps)
    by_check = Counter(f.check for f in findings)
    out = [f"# gamelogs-audit: {task}", ""]
    out += [
        f"- runs read: **{len(runs)}** (events.tsv available)",
        f"- game repetitions: **{len(reps)}**; replay present {states['ok']}, "
        f"'Missing file' {states['missing-flag']}, blank {states['blank']}, "
        f"not downloadable {states['unavailable']}",
        f"- findings: **{sum(f.severity == 'error' for f in findings)} errors**, "
        f"{sum(f.severity == 'warning' for f in findings)} warnings",
        "",
        "Only public data is read: events.tsv, .bk2 (no emulator, no ROM), "
        "`_summary.json` and `_variables.json`.",
        "",
    ]
    if rates:
        native = NATIVE_FPS.get(task)
        out += ["## Frame rate on the task clock", "",
                "| method | sessions | pairs | median fps | IQR |", "|---|---|---|---|---|"]
        for e in rates:
            out.append(f"| {e.method} | {e.sessions} | {e.pairs} | **{e.median:.4f}** | "
                       f"{e.q1:.4f}–{e.q3:.4f} |")
        if native:
            out += ["", f"Native console rate used by the pipeline: {native:.4f} fps."]
        out.append("")
    if by_check:
        out += ["## Findings", "", "| check | count | meaning |", "|---|---|---|"]
        for check, n in by_check.most_common():
            out.append(f"| `{check}` | {n} | {CHECK_DOCS.get(check, '')} |")
        out.append("")
        for check in by_check:
            out += [f"### `{check}`", ""]
            for f in [f for f in findings if f.check == check]:
                out.append(f"- **{f.where}**: {f.message}.")
                if f.fix:
                    out.append(f"  - fix: {f.fix}")
            out.append("")
    if schema:
        out += ["## `_summary.json` keys", ""]
        for keys, n in sorted(schema.items(), key=lambda kv: -kv[1]):
            out.append(f"- {n} files: `{', '.join(keys)}`")
        out.append("")
    return "\n".join(out)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="gamelogs-audit", description=__doc__.split("\n")[0])
    ap.add_argument("root", type=Path, help="dataset root (a clone of e.g. shinobi)")
    ap.add_argument("--task", help="BIDS task label; inferred from file names if omitted")
    ap.add_argument("--out", type=Path, default=Path("report"))
    args = ap.parse_args(argv)

    root = args.root.resolve()
    task = args.task or _infer_task(root)
    runs = list(load_runs(root, task))
    findings = run_all(runs, root, task)
    rates = framerate.estimate(runs)
    schema = summary_schema(runs)

    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / "report.md").write_text(render(task, runs, findings, rates, schema))
    (args.out / "findings.json").write_text(json.dumps({
        "task": task,
        "frame_rate": [asdict(e) for e in rates],
        "findings": [asdict(f) for f in findings],
    }, indent=2, default=str))
    errors = sum(f.severity == "error" for f in findings)
    print(f"{task}: {len(runs)} runs, {errors} errors, "
          f"{len(findings) - errors} warnings -> {args.out}/report.md")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
