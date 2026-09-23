from rsi.architecture_evolution import architecture_id, base_architecture, mutate


def test_architecture_mutation_is_bounded_and_unique():
    parent = base_architecture()
    children = mutate(parent)
    assert children
    assert len({architecture_id(child) for child in children}) == len(children)
    assert all(child["max_atoms"] <= 5 for child in children)
    assert all(child["budget"] in (128, 256) for child in children)
