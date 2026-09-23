from rsi.primitive_synthesis import invent_transform_expressions
from rsi.semantic_invention import _char_predicate


def test_transform_invention_discovers_a_quotient_periodic_rule():
    examples = [[chr(0x700) + chr(0x701), chr(0x700)],
                [chr(0x70f) + chr(0x710), chr(0x70f)],
                [chr(0x71e) + chr(0x71f), chr(0x71e)]]
    predicates = invent_transform_expressions(examples)
    assert predicates
    assert any(_char_predicate(examples[0][0][0], predicate) for predicate in predicates)
