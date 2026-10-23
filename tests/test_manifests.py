import json
from pathlib import Path
from concord.features import SCHEMA
from concord.inference import score_pairs
import pytest


def test_saved_record_split_isolation():
    manifest = json.loads(Path("reports/split-manifest.json").read_text())
    seen = {}
    for label in manifest["labels"]:
        for record in [label["left"], label["right"]]:
            assert seen.setdefault(record, label["split"]) == label["split"]
    assert set(seen.values()) == {"train", "validation", "test"}


def test_incompatible_artifact_fails_closed():
    with pytest.raises(RuntimeError, match="Incompatible"):
        score_pairs([], {}, dict(schema="incompatible-" + SCHEMA))
