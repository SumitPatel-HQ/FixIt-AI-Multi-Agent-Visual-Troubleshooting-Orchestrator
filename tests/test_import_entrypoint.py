import os
import subprocess
import unittest
from pathlib import Path


class BackendEntrypointImportTest(unittest.TestCase):
    def test_main_imports_when_started_from_backend_directory(self):
        backend_dir = Path(__file__).resolve().parents[1] / "backend"
        python_exe = backend_dir / ".venv" / "Scripts" / "python.exe"
        env = os.environ.copy()
        env.pop("PYTHONPATH", None)

        result = subprocess.run(
            [str(python_exe), "-c", "import main"],
            cwd=backend_dir,
            env=env,
            capture_output=True,
            text=True,
        )

        if result.returncode != 0:
            self.fail(result.stderr)


if __name__ == "__main__":
    unittest.main()
