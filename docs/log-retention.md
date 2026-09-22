# Bounded logs

API stdout/stderr (including startup tracebacks and library logs) is captured by
`scripts/api_log_runner.py`: one writer per API, 20 MiB per file, five backups.
It closes the file before rename and never copy-truncates across SMB. Each process
must have a unique broker/account/instance. High-frequency records are no longer
duplicated into full.log. Existing oversized files roll on the first new output.

The sidecar checks once a minute: lifecycle logs rotate at 10 MiB with three
archives, closed archives expire after seven days, and oldest archives are pruned
when the directory exceeds 1 GiB. This is a periodic budget, not a filesystem
quota; active files are never deleted to meet it. API backup counts provide the
per-process bound; a log record can span files without losing bytes. Filenames
are generated identifiers and must not contain whitespace. Native MT5 terminal
logs inside the Windows disk are separate and must be monitored independently.

For existing installations use the tracked `docker-compose.logging.yml` override
with the existing customized compose file. It caps each listed container at
20 MB x 5. Do not replace configuration or print secrets with compose config.
Sync api_runner.bat, api_log_runner.py and mt5api/logger.py to data/shared, stop
API writers by gracefully stopping the VM, retain diagnostic samples, remove old
closed logs, and recreate mt5, wickworks, nginx and log-rotator with both files.
The VM interruption requires a maintenance window and checking upstream positions,
pending orders and gateway operations first. Never delete the Windows disk,
gateway data volume, terminal history, or live Docker log files.

Deploy only committed source using git pull --ff-only. Preserve old commit and
compose configuration for rollback; use the same override on subsequent compose
commands. Verify log sizes, deleted-open handles, terminal/tick connectivity and
writer exclusivity after restart. Rolling back reintroduces unbounded logging.
