import sqlite3

import pytest

from scripts.migrate_database import copy_workspace


def test_workspace_copy_preserves_wal_history_and_source(tmp_path):
    source = tmp_path / "previous.db"
    target = tmp_path / "entitylens.db"
    with sqlite3.connect(source) as writer:
        writer.execute("PRAGMA journal_mode=WAL")
        writer.execute("CREATE TABLE decisions(id TEXT, rationale TEXT)")
        writer.execute("INSERT INTO decisions VALUES('decision-1','Reviewed place')")
        writer.commit()
        copy_workspace(source, target)
        with sqlite3.connect(target) as migrated:
            assert migrated.execute("SELECT * FROM decisions").fetchall() == [
                ("decision-1", "Reviewed place")
            ]
        assert writer.execute("SELECT count(*) FROM decisions").fetchone()[0] == 1
        assert not list(tmp_path.glob(".entitylens.db.*"))
        with pytest.raises(FileExistsError):
            copy_workspace(source, target)
        assert writer.execute("SELECT count(*) FROM decisions").fetchone()[0] == 1


def test_missing_source_never_creates_an_empty_workspace(tmp_path):
    with pytest.raises(FileNotFoundError):
        copy_workspace(tmp_path / "missing.db", tmp_path / "entitylens.db")
    assert not (tmp_path / "missing.db").exists()
    assert not (tmp_path / "entitylens.db").exists()
