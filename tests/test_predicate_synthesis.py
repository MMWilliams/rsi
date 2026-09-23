from rsi.predicate_synthesis import synthesize_feature_languages


def test_feature_language_synthesis_generates_multiple_structural_abstractions():
    examples = [["AB-17", "AB"], ["xyz-903", "xyz"], ["Q-4", "Q"]]
    languages = synthesize_feature_languages(examples)
    assert [language["id"] for language in languages] == ["ord_interval", "category_exact", "category_prefix"]
    assert all(language["predicates"] for language in languages)
