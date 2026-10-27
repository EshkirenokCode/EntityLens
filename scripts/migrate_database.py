"""Copy an existing SQLite workspace to a new path without changing the source."""

import argparse
import os
import sqlite3
import tempfile
from contextlib import closing
from pathlib import Path


def copy_workspace(source: Path, target: Path):
    source = source.resolve()
    target = target.resolve()
    if not source.is_file():
        raise FileNotFoundError(source)
    if target.exists():
        raise FileExistsError(target)
    if not target.parent.is_dir():
        raise FileNotFoundError(target.parent)
    descriptor, temporary = tempfile.mkstemp(
        prefix=f".{target.name}.", dir=target.parent
    )
    os.close(descriptor)
    try:
        with (
            closing(sqlite3.connect(source.as_uri() + "?mode=ro", uri=True)) as src,
            closing(sqlite3.connect(temporary)) as dst,
        ):
            src.backup(dst)
            if dst.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
                raise RuntimeError("Workspace integrity check failed")
        os.link(temporary, target)
    finally:
        for suffix in ("", "-wal", "-shm"):
            Path(temporary + suffix).unlink(missing_ok=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("target", type=Path)
    args = parser.parse_args()
    copy_workspace(args.source, args.target)
    print(f"Workspace copied to {args.target}; source preserved.")


if __name__ == "__main__":
    main()
