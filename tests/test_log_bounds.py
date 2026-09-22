import importlib.util
from pathlib import Path
import subprocess
import sys

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "api_log_runner.py"
spec = importlib.util.spec_from_file_location("api_log_runner", SCRIPT)
runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)


def test_capture_bounds_stdout_stderr_and_propagates_exit(tmp_path):
    path = tmp_path / "api.log"
    result = runner.capture(
        [
            sys.executable,
            "-c",
            "import os; os.write(1,b'a'*10000); os.write(2,b'END'); exit(7)",
        ],
        path,
        max_bytes=1024,
        backups=3,
    )
    assert result == 7
    files = list(tmp_path.glob("api.log*"))
    assert len(files) == 4
    assert all(f.stat().st_size <= 1024 for f in files)
    assert path.read_bytes().endswith(b"END")


def test_capture_preserves_unicode_bytes_and_rotates_old_file(tmp_path):
    path = tmp_path / "api.log"
    path.write_bytes(b"old" * 100)
    payload = "测试日志".encode() * 50
    assert (
        runner.capture(
            [sys.executable, "-c", f"import os; os.write(1,{payload!r})"],
            path,
            max_bytes=128,
            backups=8,
        )
        == 0
    )
    assert (tmp_path / "api.log.5").read_bytes() == b"old" * 100
    combined = (
        b"".join((tmp_path / f"api.log.{n}").read_bytes() for n in (4, 3, 2, 1))
        + path.read_bytes()
    )
    assert combined == payload


@pytest.mark.skipif(sys.platform != "linux", reason="Alpine sidecar uses Linux stat")
def test_retention_never_truncates_active_api_and_bounds_archives(tmp_path):
    active = tmp_path / "api-demo.log"
    active.write_bytes(b"active" * 1000)
    for i in range(1, 5):
        (tmp_path / f"api-demo.log.{i}").write_bytes(b"x" * 4096)
    (tmp_path / "full.log").write_bytes(b"lifecycle" * 20)
    import os

    env = {
        **os.environ,
        "LOG_DIR": str(tmp_path),
        "RUN_ONCE": "1",
        "MAX_DIRECTORY_KB": "12",
        "MAX_LIFECYCLE_BYTES": "100",
    }
    subprocess.run(["sh", str(SCRIPT.with_name("rotate-logs.sh"))], env=env, check=True)
    assert active.read_bytes() == b"active" * 1000
    assert not (tmp_path / "full.log").exists()
    assert len(list(tmp_path.glob("api-demo.log.*"))) < 4
