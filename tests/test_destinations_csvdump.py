import os
import json
import asyncio
from pathlib import Path

import pytest

from backend.destinations.csvdump import CsvDumpDestination


@pytest.mark.asyncio
async def test_csvdump_writes_files(tmp_path, monkeypatch):
    # Ensure destination writes one file per document in configured dir
    monkeypatch.setenv("CSV_DUMP_DIR", str(tmp_path))

    dest = CsvDumpDestination()
    docs = [
        {"id": "a", "raw_text": "hello"},
        {"id": "b", "raw_text": "world"},
    ]

    await dest.send(payload=docs, profile_config={})

    # the directory should now contain 2 json files
    files = list(Path(tmp_path).iterdir())
    assert len(files) == 2
    # load one of them and assert content round-tripped
    with open(files[0], "r", encoding="utf-8") as fh:
        content = json.load(fh)
    assert content["raw_text"] in {"hello", "world"} 