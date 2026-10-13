"""Infer the frame rate a game was actually played at, from the task clock.

Two independent estimates, both on the clock of the events.tsv `onset` column:

* onset gaps: for back-to-back repetitions in a run,
  ``onset[i+1] - onset[i] = frames[i] / fps + pause``. The slope of a line fitted
  per session gives 1 / fps; the intercept absorbs the constant pause.
* logged play time (when the task logged it, as shinobi's `duration` column):
  ``duration = frames / fps + c``.

Each session gives one estimate; we report the median and IQR across sessions.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass

import numpy as np

from .dataset import Run


@dataclass
class RateEstimate:
    method: str
    sessions: int
    pairs: int
    median: float
    q1: float
    q3: float


def _robust_slope(x: np.ndarray, y: np.ndarray) -> float | None:
    """Least squares y = a x + b, refitted after dropping >3.5 MAD residuals."""
    keep = np.ones(len(x), bool)
    for _ in range(3):
        if keep.sum() < 3 or np.ptp(x[keep]) == 0:
            return None
        a, b = np.polyfit(x[keep], y[keep], 1)
        res = y - (a * x + b)
        mad = np.median(np.abs(res[keep] - np.median(res[keep]))) or 1e-9
        new = np.abs(res - np.median(res[keep])) < 3.5 * 1.4826 * mad
        if (new == keep).all():
            break
        keep = new
    return float(a)


def _summarise(method: str, per_session: dict[str, list[tuple[float, float]]]) -> RateEstimate | None:
    rates, pairs = [], 0
    for pts in per_session.values():
        if len(pts) < 3:
            continue
        x, y = np.array(pts).T
        slope = _robust_slope(x, y)
        if slope and slope > 0:
            rates.append(1.0 / slope)
            pairs += len(pts)
    if not rates:
        return None
    q1, med, q3 = np.percentile(rates, [25, 50, 75])
    return RateEstimate(method, len(rates), pairs, float(med), float(q1), float(q3))


def estimate(runs: list[Run]) -> list[RateEstimate]:
    gaps: dict[str, list] = defaultdict(list)
    logged: dict[str, list] = defaultdict(list)
    for run in runs:
        session = f"{run.sub}/{run.ses}"
        reps = run.repetitions
        for cur, nxt in zip(reps, reps[1:]):
            if cur.bk2 and cur.bk2_state == "ok" and nxt.others_between == 0:
                gaps[session].append((cur.bk2.frames, nxt.onset - cur.onset))
        for rep in reps:
            if rep.bk2 and rep.duration is not None:
                logged[session].append((rep.bk2.frames, rep.duration))
    out = [_summarise("onset gaps", gaps)]
    if logged:
        out.append(_summarise("logged play time", logged))
    return [e for e in out if e]
