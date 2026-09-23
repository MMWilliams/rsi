from rsi.oracle import InvalidProgram, execute


def test_oracle_rejects_published_grammar_trailing_comma():
    try:
        execute("Concat('-', '.',)", "anything")
    except InvalidProgram:
        pass
    else:
        raise AssertionError("oracle accepted a trailing comma rejected by the DSL parser")


def test_oracle_rejects_noncanonical_match_side():
    try:
        execute("Concat(Sub(M(WORD,1,start),M(WORD,1,End)))", "Alice")
    except InvalidProgram:
        pass
    else:
        raise AssertionError("oracle accepted a noncanonical match side")
