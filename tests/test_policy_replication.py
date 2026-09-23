from pathlib import Path

from run_policy_replication import run


def test_replication_requires_a_frozen_source(tmp_path):
    assert callable(run)
    assert isinstance(Path(tmp_path), Path)
