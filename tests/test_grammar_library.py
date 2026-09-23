from rsi.grammar_library import instantiate_templates, mine_templates


def test_antiunified_templates_are_deterministic_and_visible_instantiable():
    programs = [
        "Concat(Sub(C1,C2), '-')",
        "Concat(Sub(C3,C4), '/')",
        "Concat(Sub(M(WORD,1,start),M(WORD,1,end)), '.')",
    ]
    first = mine_templates(programs, max_library=4, max_length=3, min_frequency=2)
    second = mine_templates(programs, max_library=4, max_length=3, min_frequency=2)
    assert first == second
    assert first["templates"]
    visible = [["Alice Smith", "Alice- Smith"], ["Bob Jones", "Bob- Jones"]]
    proposals = instantiate_templates(first, visible, max_proposals=32, slot_limit=8)
    assert proposals
