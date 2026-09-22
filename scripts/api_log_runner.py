"""Own one API output file; rotate only after closing its Windows/SMB handle."""

import os
from pathlib import Path
import subprocess
import sys


def capture(command, path, max_bytes=20 * 1024 * 1024, backups=5):
    if max_bytes < 1 or backups < 1:
        raise ValueError("positive log bounds required")
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    output = path.open("ab")
    size = output.tell()
    try:
        with subprocess.Popen(
            command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT
        ) as process:
            assert process.stdout is not None
            try:
                return _drain(process, path, output, size, max_bytes, backups)
            except BaseException:
                process.terminate()
                try:
                    process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait()
                raise
    finally:
        output.close()


def _drain(process, path, output, size, max_bytes, backups):
    try:
        while chunk := process.stdout.read1(16384):
            while chunk:
                if size >= max_bytes:
                    output.close()
                    for index in range(backups, 0, -1):
                        source = path if index == 1 else Path(f"{path}.{index - 1}")
                        if source.exists():
                            os.replace(source, f"{path}.{index}")
                    output = path.open("ab")
                    size = 0
                part, chunk = chunk[: max_bytes - size], chunk[max_bytes - size :]
                output.write(part)
                output.flush()
                size += len(part)
        return process.wait()
    finally:
        output.close()


if __name__ == "__main__":
    sys.exit(
        capture([sys.executable, "-u", "-m", "mt5api", *sys.argv[2:]], sys.argv[1])
    )
