# Conductivity commands

Discover the user's selection before operating a round:

```text
datacore --json project list
datacore --json experiment list --project-id 17
datacore --json conductivity list 48
```

Use the selected round's `pageUrl` from `conductivity list` for subsequent commands. The URL's internal selection parameters are machine-managed and must not be shown as choices or requested from the user.

```text
datacore --json conductivity status "<轮次页面链接>"
datacore --json conductivity recommend "<轮次页面链接>" --yes [--wait]
datacore --json conductivity export "<轮次页面链接>" --format unilab --output task.xls
datacore --json conductivity export "<轮次页面链接>" --format xlsx --output weighing.xlsx
datacore --json conductivity export "<轮次页面链接>" --format demo --output demo.csv
datacore --json conductivity validate "<轮次页面链接>" measured.csv
datacore --json conductivity upload "<轮次页面链接>" measured.csv --yes
datacore --json conductivity train "<轮次页面链接>" --yes [--wait]
datacore --json conductivity retry-fold "<轮次页面链接>" --fold 3 --yes
datacore --json conductivity compare "<轮次页面链接>"
datacore --json conductivity decide "<轮次页面链接>" continue --reason "继续优化" --yes
datacore --json conductivity next "<轮次页面链接>" --yes
```

`validate` never submits. `upload` validates again server-side. `train` evaluates, merges training data, creates frozen splits, and submits five-fold work. `next` reuses the chain tail's frozen configuration rather than accepting regenerated experiment parameters.
