"""Each case gets its own limiter folder, and the run gets its own cache folder (DEC-1092).

No case reads or writes /tmp/scryfall-limit or the owner's ~/.cache/scryfall-mcp.
"""

import os
import shutil
import tempfile

import pytest

# Set before the test modules import the tools: each tool module opens its Cache at import.
_CACHE_HOME = tempfile.mkdtemp(prefix="scryfall-mcp-tests-")
os.environ["XDG_CACHE_HOME"] = _CACHE_HOME


def pytest_sessionfinish(session, exitstatus):
    shutil.rmtree(_CACHE_HOME, ignore_errors=True)


@pytest.fixture(autouse=True)
def limit_dir(tmp_path, monkeypatch):
    """A new, empty SCRYFALL_LIMIT_DIR for each case."""
    folder = tmp_path / "scryfall-limit"
    monkeypatch.setenv("SCRYFALL_LIMIT_DIR", str(folder))
    return folder
