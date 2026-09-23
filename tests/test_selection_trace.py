import copy
import importlib.util
import random

import pytest

from audit_inheritance import check_selection
from rsi.common import ROOT
from rsi.operators import empty_stats, initial_catalog, select


@pytest.mark.parametrize("mode", ["adaptive", "random"])
def test_logging_preserves_archived_choices_and_rng_stream(mode):
    path = ROOT / "runs/inheritance-20260916-v4/source/rsi/operators.py"
    spec = importlib.util.spec_from_file_location("rsi.archived_v4_operators", path)
    archived = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(archived)
    catalog = initial_catalog()
    table = {op["name"]: {**empty_stats(), "trials": i + 2, "beneficial": i % 3,
                          "gain_sum": (i - 4) / 32, "descendant_trials": i % 4,
                          "descendant_gain_sum": (i - 6) / 64} for i, op in enumerate(catalog)}
    before = copy.deepcopy(table)
    for seed in (17, 29, 43, 101):
        legacy_rng, traced_rng, audit_rng = (random.Random(seed) for _ in range(3))
        for index in range(36):
            excluded = [op["name"] for op in catalog[:index % 13]]
            trace = {}
            old = archived.select(catalog, table, legacy_rng, mode=mode, exclude=excluded)
            new = select(catalog, table, traced_rng, mode=mode, exclude=excluded, trace=trace)
            assert old == new and legacy_rng.getstate() == traced_rng.getstate()
            assert check_selection(trace, catalog, table, audit_rng, mode, excluded) == new["name"]
        assert audit_rng.getstate() == traced_rng.getstate()
    assert table == before


def test_forged_selection_explanation_is_rejected():
    catalog = initial_catalog()
    table = {op["name"]: empty_stats() for op in catalog}
    trace = {}
    select(catalog, table, random.Random(73), trace=trace)
    trace["scores"][0]["productivity_draw"] += 0.1
    with pytest.raises(AssertionError, match="Selection explanation"):
        check_selection(trace, catalog, table, random.Random(73), "adaptive", [])
