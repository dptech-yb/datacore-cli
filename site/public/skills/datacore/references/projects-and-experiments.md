# Projects and experiments

Use read commands first:

```bash
datacore --json project list
datacore --json project show PROJECT_ID
datacore --json project lineage PROJECT_ID
datacore --json experiment list
datacore --json experiment show EXPERIMENT_ID
datacore --json experiment lineage EXPERIMENT_ID
```

Lists and records are already filtered by the signed-in user's project role and trial-account policy. A not-found response may intentionally hide a resource the user cannot access; do not probe around it.

Creating or updating records uses a reviewed JSON payload and explicit confirmation:

```bash
datacore project create --file project.json --yes
datacore project update PROJECT_ID --file patch.json --yes
datacore experiment create TASK_ID --file experiment.json --yes
datacore experiment update EXPERIMENT_ID --file patch.json --yes
```

Do not delete records through the CLI. Destructive lifecycle administration remains in the DataCore web interface.
