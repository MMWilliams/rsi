from rsi.ast_synthesis import synthesize_general_ast
from rsi.semantic_invention import _char_predicate


def test_general_ast_synthesizer_discovers_affine_fold():
    examples = [[chr(0x800) + chr(0x801), chr(0x800)],
                [chr(0x80f) + chr(0x810), chr(0x80f)],
                [chr(0x81e) + chr(0x81f), chr(0x81e)]]
    predicates = synthesize_general_ast(examples, max_depth=2)
    assert predicates
    assert any(_char_predicate(examples[0][0][0], predicate) for predicate in predicates)
