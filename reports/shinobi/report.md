# gamelogs-audit: shinobi

- runs read: **169** (events.tsv available)
- game repetitions: **662**; replay present 490, 'Missing file' 113, blank 7, not downloadable 52
- findings: **31 errors**, 7 warnings

Only public data is read: events.tsv, .bk2 (no emulator, no ROM), `_summary.json` and `_variables.json`.

## Frame rate on the task clock

| method | sessions | pairs | median fps | IQR |
|---|---|---|---|---|
| onset gaps | 35 | 364 | **60.0106** | 59.9993–60.0191 |
| logged play time | 35 | 490 | **60.0032** | 59.9993–60.0188 |

Native console rate used by the pipeline: 59.9227 fps.

## Findings

| check | count | meaning |
|---|---|---|
| `copy-under-other-run` | 11 | an unreferenced replay is a byte-identical copy of another run's replay |
| `stopped-mid-level-labelled-cleared` | 8 | the replay stops mid-level with no death, summary says `cleared` |
| `length-mismatch` | 8 | the attached replay's length differs from the length the task logged for the row (`duration_bk2`) |
| `blank-stim-file` | 7 | a game row with an empty `stim_file` instead of the 'Missing file' flag |
| `death-labelled-cleared` | 2 | health reaches 0 but the summary says `cleared` |
| `clock-mismatch` | 2 | the replay was written at a time that does not fit the row's onset |

### `death-labelled-cleared`

- **sub-01_ses-002_task-shinobi_run-03_level-4_rep-03**: health reaches 0 at frame 5653 and the replay ends 132 frames later, before a life is taken off.
  - fix: treat health == 0 as a death in shinobi_outcome (failed/killed)
- **sub-01_ses-011_task-shinobi_run-03_level-4_rep-03**: health reaches 0 at frame 1544 and the replay ends 255 frames later, before a life is taken off.
  - fix: treat health == 0 as a death in shinobi_outcome (failed/killed)

### `stopped-mid-level-labelled-cleared`

- **sub-01_ses-007_task-shinobi_run-03_level-4_rep-03**: no death and no section change, but the replay stops at X_screen_total 3506 (level end ~8892).
  - fix: label as incomplete/interrupted (shinobi #45)
- **sub-02_ses-002_task-shinobi_run-05_level-4_rep-05**: no death and no section change, but the replay stops at X_screen_total 3168 (level end ~8892).
  - fix: label as incomplete/interrupted (shinobi #45)
- **sub-02_ses-007_task-shinobi_run-05_level-4_rep-04**: no death and no section change, but the replay stops at X_screen_total 3266 (level end ~8892).
  - fix: label as incomplete/interrupted (shinobi #45)
- **sub-02_ses-008_task-shinobi_run-02_level-4_rep-02**: no death and no section change, but the replay stops at X_screen_total 3263 (level end ~8892).
  - fix: label as incomplete/interrupted (shinobi #45)
- **sub-02_ses-011_task-shinobi_run-03_level-4_rep-03**: no death and no section change, but the replay stops at X_screen_total 3296 (level end ~8892).
  - fix: label as incomplete/interrupted (shinobi #45)
- **sub-02_ses-012_task-shinobi_run-03_level-4_rep-03**: no death and no section change, but the replay stops at X_screen_total 3295 (level end ~8892).
  - fix: label as incomplete/interrupted (shinobi #45)
- **sub-02_ses-014_task-shinobi_run-02_level-4_rep-02**: no death and no section change, but the replay stops at X_screen_total 3232 (level end ~8892).
  - fix: label as incomplete/interrupted (shinobi #45)
- **sub-02_ses-015_task-shinobi_run-05_level-4_rep-05**: no death and no section change, but the replay stops at X_screen_total 3289 (level end ~8892).
  - fix: label as incomplete/interrupted (shinobi #45)

### `length-mismatch`

- **sub-02_ses-005_task-shinobi_run-01_level-1_rep-01**: replay has 9809 frames but the task logged 9879 (164.65 s) for this row.
  - fix: this row's replay is probably sub-02_ses-005_task-shinobi_run-02_level-1_rep-01.bk2
- **sub-02_ses-005_task-shinobi_run-01_level-4_rep-01**: replay has 4036 frames but the task logged 9013 (150.22 s) for this row.
  - fix: this row's replay is probably sub-02_ses-005_task-shinobi_run-02_level-4_rep-01.bk2
- **sub-02_ses-005_task-shinobi_run-01_level-5_rep-01**: replay has 11263 frames but the task logged 11035 (183.92 s) for this row.
  - fix: this row's replay is probably sub-02_ses-005_task-shinobi_run-02_level-5_rep-01.bk2
- **sub-02_ses-005_task-shinobi_run-01_level-1_rep-02**: replay has 9836 frames but the task logged 9907 (165.12 s) for this row.
  - fix: this row's replay is probably sub-02_ses-005_task-shinobi_run-02_level-1_rep-02.bk2
- **sub-02_ses-005_task-shinobi_run-02_level-1_rep-01**: replay has 9879 frames but the task logged 9809 (163.48 s) for this row.
  - fix: this row's replay is probably sub-02_ses-005_task-shinobi_run-01_level-1_rep-01.bk2
- **sub-02_ses-005_task-shinobi_run-02_level-4_rep-01**: replay has 9013 frames but the task logged 4036 (67.27 s) for this row.
  - fix: this row's replay is probably sub-02_ses-005_task-shinobi_run-01_level-4_rep-01.bk2
- **sub-02_ses-005_task-shinobi_run-02_level-5_rep-01**: replay has 11035 frames but the task logged 11263 (187.72 s) for this row.
  - fix: this row's replay is probably sub-02_ses-005_task-shinobi_run-01_level-5_rep-01.bk2
- **sub-02_ses-005_task-shinobi_run-02_level-1_rep-02**: replay has 9907 frames but the task logged 9836 (163.93 s) for this row.
  - fix: this row's replay is probably sub-02_ses-005_task-shinobi_run-01_level-1_rep-02.bk2

### `clock-mismatch`

- **sub-02_ses-005_task-shinobi_run-01_level-5_rep-01**: replay was written -83 s away from where this row's onset puts its end (run median offset).
  - fix: the file is attached to the wrong row, or the row's onset is wrong
- **sub-02_ses-005_task-shinobi_run-02_level-5_rep-01**: replay was written +81 s away from where this row's onset puts its end (run median offset).
  - fix: the file is attached to the wrong row, or the row's onset is wrong

### `blank-stim-file`

- **sub-02_ses-007_task-shinobi_run-03_events.tsv row 0**: gym-retro_game row has an empty stim_file instead of the 'Missing file' flag.
  - fix: write 'Missing file' (or n/a) like the other rows without a replay
- **sub-02_ses-007_task-shinobi_run-04_events.tsv row 0**: gym-retro_game row has an empty stim_file instead of the 'Missing file' flag.
  - fix: write 'Missing file' (or n/a) like the other rows without a replay
- **sub-02_ses-007_task-shinobi_run-05_events.tsv row 0**: gym-retro_game row has an empty stim_file instead of the 'Missing file' flag.
  - fix: write 'Missing file' (or n/a) like the other rows without a replay
- **sub-04_ses-010_task-shinobi_run-02_events.tsv row 0**: gym-retro_game row has an empty stim_file instead of the 'Missing file' flag.
  - fix: write 'Missing file' (or n/a) like the other rows without a replay
- **sub-04_ses-010_task-shinobi_run-03_events.tsv row 0**: gym-retro_game row has an empty stim_file instead of the 'Missing file' flag.
  - fix: write 'Missing file' (or n/a) like the other rows without a replay
- **sub-04_ses-010_task-shinobi_run-04_events.tsv row 1**: gym-retro_game row has an empty stim_file instead of the 'Missing file' flag.
  - fix: write 'Missing file' (or n/a) like the other rows without a replay
- **sub-04_ses-010_task-shinobi_run-05_events.tsv row 0**: gym-retro_game row has an empty stim_file instead of the 'Missing file' flag.
  - fix: write 'Missing file' (or n/a) like the other rows without a replay

### `copy-under-other-run`

- **sub-01_ses-007_task-shinobi_run-03_level-1_rep-04**: not referenced by any row, and byte-identical to sub-01_ses-007_task-shinobi_run-02_level-1_rep-04.bk2; row 0 of sub-01_ses-007_task-shinobi_run-03_events.tsv says 'Missing File' and logs this copy's length, not its own.
  - fix: delete the copy (or move it out of gamelogs/); the repetition it is named after has no replay
- **sub-01_ses-007_task-shinobi_run-05_level-4_rep-05**: not referenced by any row, and byte-identical to sub-01_ses-007_task-shinobi_run-04_level-4_rep-05.bk2; row 1 of sub-01_ses-007_task-shinobi_run-05_events.tsv says 'Missing File' and logs this copy's length, not its own.
  - fix: delete the copy (or move it out of gamelogs/); the repetition it is named after has no replay
- **sub-01_ses-009_task-shinobi_run-02_level-1_rep-02**: not referenced by any row, and byte-identical to sub-01_ses-009_task-shinobi_run-01_level-1_rep-02.bk2; row 0 of sub-01_ses-009_task-shinobi_run-02_events.tsv says 'Missing File' and logs this copy's length, not its own.
  - fix: delete the copy (or move it out of gamelogs/); the repetition it is named after has no replay
- **sub-01_ses-010_task-shinobi_run-03_level-4_rep-03**: not referenced by any row, and byte-identical to sub-01_ses-010_task-shinobi_run-02_level-4_rep-03.bk2; row 1 of sub-01_ses-010_task-shinobi_run-03_events.tsv says 'Missing File' and logs this copy's length, not its own.
  - fix: delete the copy (or move it out of gamelogs/); the repetition it is named after has no replay
- **sub-01_ses-012_task-shinobi_run-03_level-4_rep-03**: not referenced by any row, and byte-identical to sub-01_ses-012_task-shinobi_run-02_level-4_rep-03.bk2; row 1 of sub-01_ses-012_task-shinobi_run-03_events.tsv says 'Missing File' and logs this copy's length, not its own.
  - fix: delete the copy (or move it out of gamelogs/); the repetition it is named after has no replay
- **sub-02_ses-002_task-shinobi_run-04_level-4_rep-04**: not referenced by any row, and byte-identical to sub-02_ses-002_task-shinobi_run-03_level-4_rep-04.bk2; row 1 of sub-02_ses-002_task-shinobi_run-04_events.tsv says 'Missing File' and logs this copy's length, not its own.
  - fix: delete the copy (or move it out of gamelogs/); the repetition it is named after has no replay
- **sub-02_ses-006_task-shinobi_run-02_level-1_rep-02**: not referenced by any row, and byte-identical to sub-02_ses-006_task-shinobi_run-01_level-1_rep-02.bk2; row 0 of sub-02_ses-006_task-shinobi_run-02_events.tsv says 'Missing File' and logs this copy's length, not its own.
  - fix: delete the copy (or move it out of gamelogs/); the repetition it is named after has no replay
- **sub-02_ses-012_task-shinobi_run-04_level-1_rep-05**: not referenced by any row, and byte-identical to sub-02_ses-012_task-shinobi_run-03_level-1_rep-05.bk2; row 0 of sub-02_ses-012_task-shinobi_run-04_events.tsv says 'Missing File' and logs this copy's length, not its own.
  - fix: delete the copy (or move it out of gamelogs/); the repetition it is named after has no replay
- **sub-02_ses-012_task-shinobi_run-05_level-1_rep-06**: not referenced by any row, and byte-identical to sub-02_ses-012_task-shinobi_run-04_level-1_rep-06.bk2; row 0 of sub-02_ses-012_task-shinobi_run-05_events.tsv says 'Missing File' and logs this copy's length, not its own.
  - fix: delete the copy (or move it out of gamelogs/); the repetition it is named after has no replay
- **sub-02_ses-015_task-shinobi_run-03_level-1_rep-03**: not referenced by any row, and byte-identical to sub-02_ses-015_task-shinobi_run-02_level-1_rep-03.bk2; row 0 of sub-02_ses-015_task-shinobi_run-03_events.tsv says 'Missing File' and logs this copy's length, not its own.
  - fix: delete the copy (or move it out of gamelogs/); the repetition it is named after has no replay
- **sub-06_ses-013_task-shinobi_run-04_level-5_rep-01**: not referenced by any row, and byte-identical to sub-06_ses-013_task-shinobi_run-01_level-5_rep-01.bk2; row 2 of sub-06_ses-013_task-shinobi_run-04_events.tsv says 'Missing File' and logs this copy's length, not its own.
  - fix: delete the copy (or move it out of gamelogs/); the repetition it is named after has no replay

## `_summary.json` keys

- 490 files: `duration, cleared, Outcome, end_score, total health lost, shurikens used, enemies killed`
