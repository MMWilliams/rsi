import copy
import json
import random

import pytest

from rsi.banks import create_banks, public_task, template
from rsi.common import ROOT, Journal, verify_journal
from rsi.evaluation import Evaluator, Worker
from rsi.operators import apply, initial_catalog, shuffled_table, validate_operator
from rsi.oracle import InvalidProgram, correct, execute
from rsi.search import BASE_CONFIG, solve, validate_config
from dsl import PosError, render, run
from trapdoor import sample_expr, sample_input


def test_independent_interpreter_matches_published_semantics():
    rng = random.Random(7281)
    for _ in range(1000):
        program, inp = sample_expr(rng, 4), sample_input(rng)
        text = render(program)
        try:
            expected = run(program, inp)
        except PosError:
            with pytest.raises(InvalidProgram):
                execute(text, inp)
        else:
            assert execute(text, inp) == expected


@pytest.mark.parametrize("text", ["__import__('os').system('whoami')", "Concat(Sub(C0,M(WORD,1,invalid)))", "Concat(*['x'])", "Concat('x', **{})", "Concat(Sub(C9999,C1))"])
def test_oracle_rejects_unsafe_or_invalid_syntax(text):
    with pytest.raises(InvalidProgram):
        execute(text, "Hello world")


def test_mutation_cannot_write_oracle_or_paths():
    operator = {"name": "attack", "origin": "model", "updates": {"oracle.py": "x"}}
    with pytest.raises(ValueError):
        validate_operator(operator)
    operator["updates"] = {"match_cost": "__import__('os')"}
    with pytest.raises(ValueError):
        validate_operator(operator)
    with pytest.raises(ValueError):
        validate_config({**BASE_CONFIG, "match_cost": float("nan")})


def test_negative_zero_matches_published_position_semantics():
    from parse import parse
    program = "Concat(Sub(C-0,C1))"
    assert execute(program, "abc") == run(parse(program), "abc") == "a"


def test_search_replays_and_has_no_hidden_task_fields():
    task = {"id": "name", "visible": [["John Smith", "John"], ["Mary Jones", "Mary"], ["Alexandria Wu", "Alexandria"]]}
    result = solve(task, BASE_CONFIG, 128)
    assert result == solve(task, BASE_CONFIG, 128)
    assert correct(result["program"], [["Jo Li", "Jo"], ["Marcus Brown", "Marcus"]])
    assert result["cost"]["expansions"] <= 128
    with pytest.raises(ValueError):
        solve({**task, "hidden": [["Secret", "answer"]]}, BASE_CONFIG, 128)


def test_banks_disjoint_and_grounded():
    config = {"bank_seed": 912, "bank_counts": {"train": 15, "final": 15}, "visible_examples": 3, "hidden_examples": 4, "max_atoms": 3}
    banks, _ = create_banks(config)
    assert not {template(row["reference"]) for row in banks["train"]} & {template(row["reference"]) for row in banks["final"]}
    assert all(set(public_task(row)) == {"id", "visible"} for rows in banks.values() for row in rows)


def test_hash_chain_detects_tampering(tmp_path):
    journal = Journal(tmp_path / "events.jsonl")
    journal.append("test", {"value": 3})
    journal.append("test", {"value": 4})
    assert verify_journal(journal.path) == 2
    journal.path.write_text(journal.path.read_text().replace('"value":3', '"value":9'))
    with pytest.raises(ValueError):
        verify_journal(journal.path)


def test_independent_sensor_rejects_forged_worker_success(tmp_path):
    class ForgedWorker:
        def request(self, request):
            return [{"task_id": "t", "program": "Concat('wrong')", "visible_outputs": ["right"], "visible_fit": True,
                     "cost": {"expansions": 1, "primitive_executions": 1}}]
    evaluator = Evaluator(Journal(tmp_path / "events.jsonl"), {"search_budget": 128, "max_atoms": 4}, ForgedWorker())
    task = {"id": "t", "visible": [["a", "right"]], "hidden": [["b", "right"]]}
    with pytest.raises(RuntimeError, match="independent execution sensor"):
        evaluator.evaluate([task], BASE_CONFIG, "attack")
    assert evaluator.ledger["incidents"] == 1


def test_scramble_preserves_records_but_changes_identity():
    table = {f"op{i}": {"trials": i, "gain_sum": i / 10} for i in range(12)}
    shuffled = shuffled_table(table, random.Random(123))
    assert shuffled != table
    assert sorted(json.dumps(value, sort_keys=True) for value in shuffled.values()) == sorted(json.dumps(value, sort_keys=True) for value in table.values())


def test_all_initial_operators_remain_bounded():
    for operator in initial_catalog():
        config = dict(BASE_CONFIG)
        for _ in range(100):
            config = apply(operator, config)
            validate_config(config)
