"""Meta-level predicate-language synthesis for V57."""

from __future__ import annotations

import unicodedata

from .semantic_invention import induce_ord_range_predicates


def synthesize_feature_languages(visible: list[list[str]]) -> list[dict]:
    """Enumerate a small structural grammar without semantic class names.

    Values are extracted from the observed character stream.  The controller
    later chooses among these generated languages using held-out admission
    tasks; no final-task score participates in language selection.
    """
    categories = sorted({unicodedata.category(char) for text, _target in visible for char in text})
    families = sorted({category[:1] for category in categories})
    return [
        {"id": "ord_interval", "complexity": 3,
         "predicates": induce_ord_range_predicates(visible)},
        {"id": "category_exact", "complexity": 2,
         "predicates": [{"kind": "category_exact", "value": category} for category in categories]},
        {"id": "category_prefix", "complexity": 1,
         "predicates": [{"kind": "category_family", "value": family} for family in families]},
    ]
