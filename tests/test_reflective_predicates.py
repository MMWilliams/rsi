from rsi.reflective_predicates import discover_reflective_predicates


def test_reflective_predicates_are_discovered_without_named_vocabulary():
    predicates = discover_reflective_predicates([["AB-17", "AB"], ["xyz-903", "xyz"]])
    names = {predicate["name"] for predicate in predicates}
    assert "isalpha" in names
    assert "isdigit" in names
    assert all(predicate["kind"] == "method" for predicate in predicates)
