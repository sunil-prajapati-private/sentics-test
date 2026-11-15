# Testing and demo

Run the deterministic suite with `python3 -m unittest discover -s tests -v`. Phase 6 adds two focused demonstrations:

```sh
scripts/demo/phase6-offline.sh
scripts/demo/phase6-safety.sh
```

The offline scenario persists queued commands, reconstructs them after a new scheduler instance, ignores duplicate command replay, and fails an interrupted running execution safely with `restart_recovery_ambiguous` rather than executing it twice. The safety scenario enters and leaves each cell, pauses active work, blocks starts in an occupied cell, resumes after clearance, and proves the cells are independent.

The full recording still requires the Phase 7 runtime integration: start Compose, submit jobs on both robots, stop on-prem, observe pending cloud jobs, restart on-prem, replay a duplicate, and demonstrate the UI safety reason. Docker and Node are prerequisites for that recording.
