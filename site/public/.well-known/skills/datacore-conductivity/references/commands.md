# Conductivity commands

Use `TARGET` as the full DataCore URL containing `boChain` and `boTurn`.

```text
datacore --json conductivity status TARGET
datacore --json conductivity recommend TARGET --yes [--wait]
datacore --json conductivity export TARGET --format unilab --output task.xls
datacore --json conductivity export TARGET --format xlsx --output weighing.xlsx
datacore --json conductivity export TARGET --format demo --output demo.csv
datacore --json conductivity validate TARGET measured.csv
datacore --json conductivity upload TARGET measured.csv --yes
datacore --json conductivity train TARGET --yes [--wait]
datacore --json conductivity retry-fold TARGET --fold 3 --yes
datacore --json conductivity compare TARGET
datacore --json conductivity decide TARGET continue --reason "继续优化" --yes
datacore --json conductivity next TARGET --yes
```

`validate` never submits. `upload` validates again server-side. `train` evaluates, merges training data, creates frozen splits, and submits five-fold work. `next` reuses the chain tail's frozen configuration rather than accepting regenerated experiment parameters.
