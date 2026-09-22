import logging

from mt5api.config import IDENTITY

# api_log_runner owns the file and rotation. Never duplicate high-frequency
# request logs into the multi-writer SMB full.log.
log = logging.getLogger("mt5api")
log.setLevel(logging.INFO)
log.propagate = False
if not log.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(
        logging.Formatter(
            f"[%(asctime)s] [api:{IDENTITY}] %(message)s", "%Y-%m-%d %H:%M:%S"
        )
    )
    log.addHandler(handler)
