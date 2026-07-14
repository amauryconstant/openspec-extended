# Hello, orchestrator!

This file was created by the [OpenSpec-extended](../README.md) 7-phase
orchestrator running against the
[`add-orchestrator-example`](../openspec/changes/add-orchestrator-example/)
change in this repository.

It exists to prove that the orchestrator works end-to-end on a real
spec-driven change, and to provide a self-contained, reproducible example
for the [orchestrator state machine docs](../docs/orchestrator-state-machine.md).

If you want to re-run the orchestrator yourself:

```bash
openspec-extended orchestrate add-orchestrator-example
```

See [`docs/orchestrator-state-machine.md`](../docs/orchestrator-state-machine.md)
for the full phase model and transition reasons.