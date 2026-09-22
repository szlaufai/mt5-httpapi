#!/bin/sh
# Only short-lived lifecycle writers are renamed here. API files belong to
# api_log_runner.py: never copy/truncate a live Windows/SMB output file.
set -eu
LOG_DIR="${LOG_DIR:-/logs}"
RETAIN_DAYS="${RETAIN_DAYS:-7}"
INTERVAL="${INTERVAL:-60}"
MAX_DIRECTORY_KB="${MAX_DIRECTORY_KB:-1048576}"
MAX_LIFECYCLE_BYTES="${MAX_LIFECYCLE_BYTES:-10485760}"

rotate_once() {
    for name in full install pip start windows-events; do
        f="$LOG_DIR/$name.log"
        [ -f "$f" ] || continue
        if [ "$(stat -c %s "$f")" -ge "$MAX_LIFECYCLE_BYTES" ]; then
            mv "$f" "$f.archive.$(date -u +%Y%m%dT%H%M%S)"
        fi
        # Keep the newest three lifecycle archives.
        count=0
        for old in $(ls -1 "$f".archive.* 2>/dev/null | sort -r); do
            count=$((count + 1))
            if [ "$count" -gt 3 ]; then rm -f "$old"; fi
        done
    done
    # Numeric API backups and old daily archives are closed files. Do not
    # delete active *.log files, locks, state, or terminal data.
    for old in "$LOG_DIR"/*.log.[0-9]* "$LOG_DIR"/*.log.archive.*; do
        [ -f "$old" ] || continue
        age=$(( $(date -u +%s) - $(stat -c %Y "$old") ))
        if [ "$age" -ge "$((RETAIN_DAYS * 86400))" ]; then rm -f "$old"; fi
    done
    # Prune oldest archives first when total directory usage exceeds budget.
    for old in "$LOG_DIR"/*.log.[0-9]* "$LOG_DIR"/*.log.archive.*; do
        [ -f "$old" ] || continue
        stat -c '%Y %n' "$old"
    done | sort -n | while read -r stamp old; do
        usage=$(du -sk "$LOG_DIR" | awk '{print $1}')
        [ "$usage" -gt "$MAX_DIRECTORY_KB" ] || break
        rm -f "$old"
    done
}
while true; do
    rotate_once || echo 'log retention failed' >&2
    [ "${RUN_ONCE:-0}" = 1 ] && break
    sleep "$INTERVAL"
done
