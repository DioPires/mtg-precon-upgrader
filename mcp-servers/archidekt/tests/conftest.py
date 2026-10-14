"""Each case gets its own limiter folder (DEC-1092): no case reads or writes /tmp/scryfall-limit."""

import pytest


@pytest.fixture(autouse=True)
def limit_dir(tmp_path, monkeypatch):
    """A new, empty SCRYFALL_LIMIT_DIR for each case."""
    folder = tmp_path / "scryfall-limit"
    monkeypatch.setenv("SCRYFALL_LIMIT_DIR", str(folder))
    return folder
