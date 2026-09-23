from rsi.expression_synthesis import synthesize_ordinal_expressions
from rsi.semantic_invention import _char_predicate


def test_generic_expression_grammar_discovers_modulus_and_bit_rules():
    mod_examples = [[chr(0x600) + chr(0x601), chr(0x600)],
                    [chr(0x60d) + chr(0x60e), chr(0x60d)],
                    [chr(0x61a) + chr(0x61b), chr(0x61a)]]
    bit_examples = [[chr(0x610) + chr(0x618), chr(0x610)],
                    [chr(0x620) + chr(0x628), chr(0x620)],
                    [chr(0x630) + chr(0x638), chr(0x630)]]
    for examples in (mod_examples, bit_examples):
        predicates = synthesize_ordinal_expressions(examples)
        assert predicates
        assert any(_char_predicate(examples[0][0][0], predicate) for predicate in predicates)


def test_generic_expression_grammar_can_compose_boolean_atoms():
    examples = [[chr(0x605) + chr(0x607), chr(0x605)],
                [chr(0x60a) + chr(0x60e), chr(0x60a)],
                [chr(0x614) + chr(0x616), chr(0x614)]]
    predicates = synthesize_ordinal_expressions(examples)
    assert any(predicate["expr"].get("op") in {"bool_or", "not"} for predicate in predicates)
