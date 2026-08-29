# Experimental resources

## Bookings

```bash
datacore --json booking list
datacore --json booking qualified --station STATION --material-state liquid|solid
datacore --json booking show BOOKING_ID
datacore booking create --file booking.json --yes
datacore booking update BOOKING_ID --file patch.json --yes
datacore booking cancel BOOKING_ID --yes
```

The scheduler remains authoritative for station type, operator qualifications, lifecycle rules, and conflicts. Solid-state station rules and liquid-state qualification rules are not reimplemented in the Skill.

## Reagents and chemicals

```bash
datacore --json chemical search "LiPF6"
datacore --json chemical resolve "LiPF6" "EC"
datacore --json reagent inventory --q EC
datacore --json reagent tasks --status pending
datacore --json reagent task RECIPE_ID
```

Reagent writes use JSON plus `--yes`: `create-task`, `assign`, and `status`. `confirm` also requires `--yes`. Inventory and task visibility continues to follow reagent group roles.

## Data tools

`datacore --json tool history --limit 50` lists the signed-in user's archived tool runs. It does not expose another user's input or output. Tool execution is introduced capability by capability; use `datacore capabilities` rather than guessing an internal endpoint.
