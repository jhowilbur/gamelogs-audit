# gamelogs-audit: mario

- runs read: **484** (events.tsv available)
- game repetitions: **3374**; replay present 3374, 'Missing file' 0, blank 0, not downloadable 0
- findings: **0 errors**, 0 warnings

Only public data is read: events.tsv, .bk2 (no emulator, no ROM), `_summary.json` and `_variables.json`.

## Frame rate on the task clock

| method | sessions | pairs | median fps | IQR |
|---|---|---|---|---|
| onset gaps | 119 | 2866 | **60.0013** | 59.9998–60.0034 |

Native console rate used by the pipeline: 60.0998 fps.

## `_summary.json` keys

- 3374 files: `Subject, World, Level, Duration, Outcome, ScoreGained, X_Traveled, Average_speed, Lives_lost, Hits_taken, Enemies_killed, Powerups_collected, Bricks_smashed, CoinsGained, IndexInRun, Run, IndexGlobal, IndexLevel, Phase, LevelFullName, Bk2File`
