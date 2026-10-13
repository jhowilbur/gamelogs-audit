# gamelogs-audit

Integrity checks for the CNeuroMod videogame datasets (shinobi, mario, mario3, mariostars), built from public files only. It reads the raw `func/*_events.tsv`, the `.bk2` replays (zip files: frames are counted in `Input Log.txt`, so there is no emulator and no ROM), and the `_summary.json` / `_variables.json` sidecars.

```bash
uv venv -p 3.12 .venv && uv pip install -p .venv -e '.[test]'
.venv/bin/gamelogs-audit ../data/shinobi --out reports/shinobi   # exit 1 if any error
.venv/bin/pytest -q
```

It writes `report.md` (for people) and `findings.json` (for CI).

## Checks

| check | what it catches | source |
|---|---|---|
| `length-mismatch` | the attached replay's frame count ≠ the `duration_bk2` the task logged; names the file of the session that does match | shinobi #44 |
| `clock-mismatch` | zip write time − (onset + length) off the run's constant offset; the run's last replay is skipped (written late) | shinobi #44 |
| `copy-under-other-run` | an unreferenced replay is byte-identical to another run's replay | new |
| `duplicate-replay` | two rows point to byte-identical replays | new |
| `unreferenced-replay` | a replay no events row points to | new |
| `stopped-mid-level-labelled-cleared` | `cleared`, no death, no section change, stops before the level end | shinobi #45 |
| `death-labelled-cleared` | health reaches 0 and the replay ends before `lives` drops | new |
| `outcome-disagrees-with-rule` | the shipped Outcome ≠ `outcome.py` on the same replay | videogames_utils #5 |
| `blank-stim-file` | an empty `stim_file` instead of `Missing file` | shinobi #31 |

The **frame rate** is inferred on the task clock from onset gaps (and from the logged play time where it exists), per session, as median and IQR (videogames_utils #7). The **`_summary.json` key sets** are listed per dataset (videogames_utils #6).

## Results (dev_replays, 2026-09-29/30, public subjects)

| dataset | runs | repetitions | errors | warnings | fps (onset gaps) |
|---|---|---|---|---|---|
| mario | 484 | 3374 | 0 | 0 | 60.0013 |
| shinobi | 169 | 662 | 31 | 7 | 60.0106 (logged play time: 60.0032) |

Full reports: `reports/<dataset>/report.md`.

## Running it in a dataset repo's CI

See `examples/gamelogs-audit.yml`. It fetches only `*.bk2` and `*_events.tsv` (about 45 MB for shinobi) with DataLad and fails the job on any error.
