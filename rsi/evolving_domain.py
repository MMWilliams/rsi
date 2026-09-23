"""V52 cross-domain banks: delimiter training, transition evaluation."""

from __future__ import annotations

import random

from .common import digest


def _delimiter_input(rng, kind):
    if kind == "email":
        return f"{rng.choice(['ana','zoe','li','omar'])}.{rng.choice(['smith','khan','ito','lee'])}{rng.randint(1,99)}@{rng.choice(['example.com','research.org','lab.net'])}", "@"
    if kind == "code":
        return "".join(rng.choice("ABCDEFGH") for _ in range(rng.randint(2,5))) + "-" + str(rng.randint(10,99999)), "-"
    return f"{rng.randint(1,28):02d}/{rng.randint(1,12):02d}/{rng.randint(1990,2035)}", "/"


def _transition_input(rng, direction, disjoint=False):
    letters = "αβγδεζηθικλμ" if disjoint else "ABCDEFGHxyz"
    digits = "٠١٢٣٤٥٦٧٨٩" if disjoint else "0123456789"
    if direction == "letter_digit":
        return "".join(rng.choice(letters) for _ in range(rng.randint(2,6))) + "".join(rng.choice(digits) for _ in range(rng.randint(1,6)))
    return "".join(rng.choice(digits) for _ in range(rng.randint(1,6))) + "".join(rng.choice(letters) for _ in range(rng.randint(2,6)))


def _transition_output(text, direction, before):
    wanted = ("letter", "digit") if direction == "letter_digit" else ("digit", "letter")
    def kind(char):
        if char.isalpha():
            return "letter"
        if char.isdigit():
            return "digit"
        return "other"
    positions = [i for i in range(1, len(text)) if
                 kind(text[i-1]) == wanted[0] and kind(text[i]) == wanted[1]]
    index = positions[0]
    return text[:index] if before else text[index:]


def _vowel_input(rng, direction, visible_index=None):
    vowels = "αεηιουω"
    consonants = "βγδζθκλμνπρσφχψ"
    left, right = (vowels, consonants) if direction == "vowel_consonant" else (consonants, vowels)
    if visible_index == 0:
        return left + right
    if visible_index == 1:
        return left[::-1] + right[::-1]
    if visible_index == 2:
        return left[::2] + right[::2]
    return "".join(rng.choice(left) for _ in range(rng.randint(2, 6))) + "".join(rng.choice(right) for _ in range(rng.randint(1, 6)))


def _vowel_output(text, direction, before):
    vowels = set("αεηιουω")
    wanted = ("vowel", "consonant") if direction == "vowel_consonant" else ("consonant", "vowel")
    def kind(char):
        return "vowel" if char in vowels else "consonant"
    positions = [i for i in range(1, len(text)) if kind(text[i - 1]) == wanted[0] and kind(text[i]) == wanted[1]]
    index = positions[0]
    return text[:index] if before else text[index:]


def _parity_input(rng, direction, visible_index=None):
    symbols = "αβγδεζηθικλμνξοπρστυφχψω"
    first = [char for char in symbols if (ord(char) % 2 == 0) == (direction == "even_odd")]
    second = [char for char in symbols if char not in first]
    if visible_index is not None and visible_index < 3:
        offset = visible_index * 2
        left = (first[offset:offset + 3] or first[:3])
        right = (second[offset:offset + 2] or second[:2])
        return "".join(left) + "".join(right)
    return "".join(rng.choice(first) for _ in range(rng.randint(2, 5))) + "".join(rng.choice(second) for _ in range(rng.randint(1, 5)))


def _parity_output(text, direction, before):
    wanted = ("even", "odd") if direction == "even_odd" else ("odd", "even")
    def kind(char):
        return "even" if ord(char) % 2 == 0 else "odd"
    positions = [i for i in range(1, len(text)) if kind(text[i - 1]) == wanted[0] and kind(text[i]) == wanted[1]]
    index = positions[0]
    return text[:index] if before else text[index:]


def _periodic_input(rng, direction, visible_index=None):
    symbols = [chr(0x400 + index) for index in range(44)]
    first = [char for char in symbols if ord(char) % 11 == 0]
    second = [char for char in symbols if char not in first]
    if direction == "periodic_other":
        first, second = second, first
    if visible_index is not None and visible_index < 3:
        left = (first[visible_index:visible_index + 3] or first[:3])
        right = (second[visible_index * 2:visible_index * 2 + 2] or second[:2])
        return "".join(left) + "".join(right)
    return "".join(rng.choice(first) for _ in range(rng.randint(2, 5))) + "".join(rng.choice(second) for _ in range(rng.randint(1, 5)))


def _periodic_output(text, direction, before):
    first_is_special = direction == "special_other"
    def special(char):
        return ord(char) % 11 == 0
    positions = [i for i in range(1, len(text)) if special(text[i - 1]) != special(text[i])]
    index = positions[0]
    return text[:index] if before else text[index:]


def _bit_input(rng, direction, visible_index=None):
    symbols = [chr(0x500 + index) for index in range(64)]
    first = [char for char in symbols if (((ord(char) >> 3) & 1) == 1) == (direction == "bit_on_off")]
    second = [char for char in symbols if char not in first]
    if visible_index is not None and visible_index < 3:
        left = (first[visible_index * 2:visible_index * 2 + 4] or first[:4])
        right = (second[visible_index * 2:visible_index * 2 + 3] or second[:3])
        return "".join(left) + "".join(right)
    return "".join(rng.choice(first) for _ in range(rng.randint(2, 5))) + "".join(rng.choice(second) for _ in range(rng.randint(1, 5)))


def _bit_output(text, direction, before):
    wanted = (1, 0) if direction == "bit_on_off" else (0, 1)
    def bit(char):
        return (ord(char) >> 3) & 1
    positions = [i for i in range(1, len(text)) if (bit(text[i - 1]), bit(text[i])) == wanted]
    index = positions[0]
    return text[:index] if before else text[index:]


def _mixed_input(rng, rule, direction, visible_index=None):
    symbols = [chr(0x400 + index) for index in range(64)]
    def special(char):
        return (ord(char) % 11 == 0) if rule == "mod11" else (((ord(char) >> 3) & 1) == 1)
    first = [char for char in symbols if special(char) == (direction == "special_other")]
    second = [char for char in symbols if char not in first]
    if visible_index is not None and visible_index < 3:
        start = round(visible_index * max(0, len(first) - 4) / 2)
        left = first[start:start + 4] or first[:4]
        anchor = ord(left[len(left) // 2])
        right = sorted(second, key=lambda char: (abs(ord(char) - anchor), ord(char)))[:3]
        return "".join(left) + "".join(right)
    return "".join(rng.choice(first) for _ in range(rng.randint(2, 5))) + "".join(rng.choice(second) for _ in range(rng.randint(1, 5)))


def _mixed_output(text, rule, direction, before):
    def special(char):
        return (ord(char) % 11 == 0) if rule == "mod11" else (((ord(char) >> 3) & 1) == 1)
    wanted = (True, False) if direction == "special_other" else (False, True)
    positions = [i for i in range(1, len(text)) if (special(text[i - 1]), special(text[i])) == wanted]
    index = positions[0]
    return text[:index] if before else text[index:]


def _expression_input(rng, rule, direction, visible_index=None):
    symbols = [chr(0x600 + index) for index in range(128)]
    def special(char):
        code = ord(char)
        if rule == "mod13":
            return code % 13 == 0
        if rule == "mod17":
            return code % 17 == 0
        if rule == "bit4":
            return ((code >> 4) & 1) == 1
        if rule == "compound":
            return code % 5 == 0 or code % 7 == 0
        return code < 0x640
    first = [char for char in symbols if special(char) == (direction == "special_other")]
    second = [char for char in symbols if char not in first]
    if visible_index is not None and visible_index < 3:
        start = round(visible_index * max(0, len(first) - 4) / 2)
        left = first[start:start + 4] or first[:4]
        anchor = ord(left[len(left) // 2])
        right = sorted(second, key=lambda char: (abs(ord(char) - anchor), ord(char)))[:3]
        return "".join(left) + "".join(right)
    return "".join(rng.choice(first) for _ in range(rng.randint(2, 5))) + "".join(rng.choice(second) for _ in range(rng.randint(1, 5)))


def _expression_output(text, rule, direction, before):
    def special(char):
        code = ord(char)
        if rule == "mod13":
            return code % 13 == 0
        if rule == "mod17":
            return code % 17 == 0
        if rule == "bit4":
            return ((code >> 4) & 1) == 1
        if rule == "compound":
            return code % 5 == 0 or code % 7 == 0
        return code < 0x640
    wanted = (True, False) if direction == "special_other" else (False, True)
    positions = [i for i in range(1, len(text)) if (special(text[i - 1]), special(text[i])) == wanted]
    index = positions[0]
    return text[:index] if before else text[index:]


def _transform_special(char, rule):
    code = ord(char)
    if rule == "quotient_mod":
        return (code // 3) % 5 == 0
    if rule == "gray_bit":
        return ((code ^ (code >> 1)) >> 4) & 1 == 1
    return ((code >> 2) & 3) == 2


def _transform_input(rng, rule, direction, visible_index=None):
    symbols = [chr(0x700 + index) for index in range(192)]
    first = [char for char in symbols if _transform_special(char, rule) == (direction == "special_other")]
    second = [char for char in symbols if char not in first]
    if visible_index is not None and visible_index < 5:
        start = round(visible_index * max(0, len(first) - 4) / 4)
        left = first[start:start + 4] or first[:4]
        anchor = ord(left[len(left) // 2])
        right = sorted(second, key=lambda char: (abs(ord(char) - anchor), ord(char)))[:3]
        return "".join(left) + "".join(right)
    return "".join(rng.choice(first) for _ in range(rng.randint(2, 5))) + "".join(rng.choice(second) for _ in range(rng.randint(1, 5)))


def _transform_output(text, rule, direction, before):
    wanted = (True, False) if direction == "special_other" else (False, True)
    positions = [i for i in range(1, len(text)) if (_transform_special(text[i - 1], rule), _transform_special(text[i], rule)) == wanted]
    index = positions[0]
    return text[:index] if before else text[index:]


def _ast_special(char, rule):
    code = ord(char)
    if rule == "affine_fold":
        return ((code * 3 + 7) // 5) % 7 == 2
    if rule == "affine_alt":
        return ((code * 5 + 3) // 4) % 9 == 4
    return ((code ^ 0x55) >> 3) & 3 == 1


def _ast_input(rng, rule, direction, visible_index=None):
    symbols = [chr(0x800 + index) for index in range(256)]
    first = [char for char in symbols if _ast_special(char, rule) == (direction == "special_other")]
    second = [char for char in symbols if char not in first]
    if visible_index is not None:
        start = round(visible_index * max(0, len(first) - 4) / 39)
        left = first[start:start + 4] or first[:4]
        anchor = ord(left[len(left) // 2])
        right = sorted(second, key=lambda char: (abs(ord(char) - anchor), ord(char)))[:3]
        return "".join(left) + "".join(right)
    return "".join(rng.choice(first) for _ in range(rng.randint(2, 5))) + "".join(rng.choice(second) for _ in range(rng.randint(1, 5)))


def _ast_output(text, rule, direction, before):
    wanted = (True, False) if direction == "special_other" else (False, True)
    positions = [i for i in range(1, len(text)) if (_ast_special(text[i - 1], rule), _ast_special(text[i], rule)) == wanted]
    index = positions[0]
    return text[:index] if before else text[index:]


def _encoded_code(char, encoding="identity"):
    """Return the hidden code-point representation used by an encoded task.

    Identity is intentionally byte-for-byte compatible with the earlier banks.
    The other modes keep the visible alphabet fixed while changing the numeric
    representation on which the same named mechanism operates.
    """
    code = ord(char)
    if encoding == "identity":
        return code
    if encoding == "xor55":
        return code ^ 0x55
    if encoding == "affine5":
        return (5 * code + 17) & 0xff
    if encoding == "rotate3":
        value = code & 0xff
        return ((value << 3) | (value >> 5)) & 0xff
    if encoding == "bit_reverse":
        value = code & 0xff
        return int(f"{value:08b}"[::-1], 2)
    raise ValueError(f"unknown code-point encoding: {encoding}")


def _novel_special(char, rule, encoding="identity"):
    """Mechanisms deliberately outside the V66/V67 affine AST catalog."""
    code = _encoded_code(char, encoding)
    if rule == "popcount_parity":
        return code.bit_count() % 2 == 1
    if rule == "rotated_mod":
        value = code & 0xff
        rotated = ((value << 3) | (value >> 5)) & 0xff
        return rotated % 5 == 2
    if rule == "gcd_bucket":
        import math
        return math.gcd(code, 30) % 5 == 1
    return False


def _novel_input(rng, rule, direction, visible_index=None, encoding="identity"):
    symbols = [chr(0x900 + index) for index in range(256)]
    first = [char for char in symbols if _novel_special(char, rule, encoding) == (direction == "special_other")]
    second = [char for char in symbols if char not in first]
    if visible_index is not None:
        start = round(visible_index * max(0, len(first) - 4) / 39)
        left = first[start:start + 4] or first[:4]
        anchor = ord(left[len(left) // 2])
        right = sorted(second, key=lambda char: (abs(ord(char) - anchor), ord(char)))[:3]
        return "".join(left) + "".join(right)
    return "".join(rng.choice(first) for _ in range(rng.randint(2, 5))) + "".join(rng.choice(second) for _ in range(rng.randint(1, 5)))


def _novel_output(text, rule, direction, before, encoding="identity"):
    wanted = (True, False) if direction == "special_other" else (False, True)
    positions = [_index for _index in range(1, len(text))
                 if (_novel_special(text[_index - 1], rule, encoding),
                     _novel_special(text[_index], rule, encoding)) == wanted]
    index = positions[0]
    return text[:index] if before else text[index:]


def _stack_special(char, rule, encoding="identity"):
    code = _encoded_code(char, encoding) & 0xff
    if rule == "fold_parity":
        return code.bit_count() % 2 == 1
    if rule == "fold_mod3":
        return code.bit_count() % 3 == 2
    if rule == "bit_splice":
        shift = 3
        rotated = ((code << shift) | (code >> (8 - shift))) & 0xff
        return rotated % 5 == 2
    return False


def _stack_input(rng, rule, direction, visible_index=None, encoding="identity"):
    symbols = [chr(0xa00 + index) for index in range(256)]
    first = [char for char in symbols if _stack_special(char, rule, encoding) == (direction == "special_other")]
    second = [char for char in symbols if char not in first]
    if visible_index is not None:
        start = round(visible_index * max(0, len(first) - 4) / 39)
        left = first[start:start + 4] or first[:4]
        anchor = ord(left[len(left) // 2])
        right = sorted(second, key=lambda char: (abs(ord(char) - anchor), ord(char)))[:3]
        return "".join(left) + "".join(right)
    return "".join(rng.choice(first) for _ in range(rng.randint(2, 5))) + "".join(rng.choice(second) for _ in range(rng.randint(1, 5)))


def _stack_output(text, rule, direction, before, encoding="identity"):
    wanted = (True, False) if direction == "special_other" else (False, True)
    positions = [_index for _index in range(1, len(text))
                 if (_stack_special(text[_index - 1], rule, encoding),
                     _stack_special(text[_index], rule, encoding)) == wanted]
    index = positions[0]
    return text[:index] if before else text[index:]


def _raw_stack_special(char, rule):
    code = ord(char) & 0xff
    if rule == "raw_xor_parity":
        return code.bit_count() % 2 == 1
    if rule == "raw_sum_mod4":
        return code.bit_count() % 4 == 3
    if rule == "raw_splice_mod7":
        rotated = ((code << 2) | (code >> 6)) & 0xff
        return rotated % 7 == 4
    return False


def _raw_stack_input(rng, rule, direction, visible_index=None):
    symbols = [chr(0xb00 + index) for index in range(256)]
    first = [char for char in symbols if _raw_stack_special(char, rule) == (direction == "special_other")]
    second = [char for char in symbols if char not in first]
    if visible_index is not None:
        start = round(visible_index * max(0, len(first) - 4) / 39)
        left = first[start:start + 4] or first[:4]
        anchor = ord(left[len(left) // 2])
        right = sorted(second, key=lambda char: (abs(ord(char) - anchor), ord(char)))[:3]
        return "".join(left) + "".join(right)
    return "".join(rng.choice(first) for _ in range(rng.randint(2, 5))) + "".join(rng.choice(second) for _ in range(rng.randint(1, 5)))


def _raw_stack_output(text, rule, direction, before):
    wanted = (True, False) if direction == "special_other" else (False, True)
    positions = [_index for _index in range(1, len(text))
                 if (_raw_stack_special(text[_index - 1], rule), _raw_stack_special(text[_index], rule)) == wanted]
    index = positions[0]
    return text[:index] if before else text[index:]


def _mutation_special(char, rule):
    code = ord(char) & 0xff
    if rule == "mutation_xor_parity":
        return code.bit_count() % 2 == 1
    if rule == "mutation_sum_mod5":
        return code.bit_count() % 5 == 4
    if rule == "mutation_low_nibble":
        return ((code & 15).bit_count() + ((code >> 4) & 15).bit_count()) % 3 == 1
    return False


def _mutation_input(rng, rule, direction, visible_index=None):
    symbols = [chr(0xc00 + index) for index in range(256)]
    first = [char for char in symbols if _mutation_special(char, rule) == (direction == "special_other")]
    second = [char for char in symbols if char not in first]
    if visible_index is not None:
        start = round(visible_index * max(0, len(first) - 4) / 39)
        left = first[start:start + 4] or first[:4]
        anchor = ord(left[len(left) // 2])
        right = sorted(second, key=lambda char: (abs(ord(char) - anchor), ord(char)))[:3]
        return "".join(left) + "".join(right)
    return "".join(rng.choice(first) for _ in range(rng.randint(2, 5))) + "".join(rng.choice(second) for _ in range(rng.randint(1, 5)))


def _mutation_output(text, rule, direction, before):
    wanted = (True, False) if direction == "special_other" else (False, True)
    positions = [_index for _index in range(1, len(text))
                 if (_mutation_special(text[_index - 1], rule), _mutation_special(text[_index], rule)) == wanted]
    index = positions[0]
    return text[:index] if before else text[index:]


def _self_edit_special(char, rule):
    code = ord(char) & 0xff
    if rule == "grammar_not":
        return ((~code) & 0xff) % 5 == 2
    if rule == "grammar_nibble":
        return (((code & 15) ^ ((code >> 4) & 15)) % 5) == 3
    if rule == "grammar_subfold":
        return (code.bit_count() + 1) % 4 == 2
    return False


def _self_edit_input(rng, rule, direction, visible_index=None):
    symbols = [chr(0xd00 + index) for index in range(256)]
    first = [char for char in symbols if _self_edit_special(char, rule) == (direction == "special_other")]
    second = [char for char in symbols if char not in first]
    if visible_index is not None:
        start = round(visible_index * max(0, len(first) - 4) / 39)
        left = first[start:start + 4] or first[:4]
        anchor = ord(left[len(left) // 2])
        right = sorted(second, key=lambda char: (abs(ord(char) - anchor), ord(char)))[:3]
        return "".join(left) + "".join(right)
    return "".join(rng.choice(first) for _ in range(rng.randint(2, 5))) + "".join(rng.choice(second) for _ in range(rng.randint(1, 5)))


def _self_edit_output(text, rule, direction, before):
    wanted = (True, False) if direction == "special_other" else (False, True)
    positions = [_index for _index in range(1, len(text))
                 if (_self_edit_special(text[_index - 1], rule), _self_edit_special(text[_index], rule)) == wanted]
    index = positions[0]
    return text[:index] if before else text[index:]


def make_task(rng, split, index, family, visible_examples=3, hidden_examples=13,
              encoding="identity"):
    if family == "delimiter":
        kind = rng.choice(("email", "code", "slash"))
        pairs = [_delimiter_input(rng, kind) for _ in range(visible_examples + hidden_examples)]
        delimiter = pairs[0][1]
        pairs = [(text, delimiter) for text, _ in pairs]
        op = rng.choice(("before", "after"))
        outputs = []
        for text, delim in pairs:
            pos = text.find(delim)
            outputs.append(text[:pos] if op == "before" else text[pos + len(delim):])
        reference = op
    elif family == "mixed_arithmetic_transition":
        rule = rng.choice(("mod11", "bit3"))
        direction = rng.choice(("special_other", "other_special"))
        texts = [_mixed_input(rng, rule, direction, index if index < visible_examples else None)
                 for index in range(visible_examples + hidden_examples)]
        before = rng.choice((True, False))
        pairs = [(text, text) for text in texts]
        outputs = [_mixed_output(text, rule, direction, before) for text in texts]
        reference = f"mixed_arithmetic:{rule}:{direction}:{'before' if before else 'after'}"
    elif family == "expression_transition":
        rule = rng.choice(("mod13", "mod17", "bit4", "compound", "threshold"))
        direction = rng.choice(("special_other", "other_special"))
        texts = [_expression_input(rng, rule, direction, index if index < visible_examples else None)
                 for index in range(visible_examples + hidden_examples)]
        before = rng.choice((True, False))
        pairs = [(text, text) for text in texts]
        outputs = [_expression_output(text, rule, direction, before) for text in texts]
        reference = f"expression:{rule}:{direction}:{'before' if before else 'after'}"
    elif family == "transform_transition":
        rule = rng.choice(("quotient_mod", "gray_bit", "bitfield"))
        direction = rng.choice(("special_other", "other_special"))
        texts = [_transform_input(rng, rule, direction, index if index < visible_examples else None)
                 for index in range(visible_examples + hidden_examples)]
        before = rng.choice((True, False))
        pairs = [(text, text) for text in texts]
        outputs = [_transform_output(text, rule, direction, before) for text in texts]
        reference = f"transform:{rule}:{direction}:{'before' if before else 'after'}"
    elif family == "ast_transition":
        rule = rng.choice(("affine_fold", "affine_alt"))
        direction = rng.choice(("special_other", "other_special"))
        texts = [_ast_input(rng, rule, direction, index if index < visible_examples else None)
                 for index in range(visible_examples + hidden_examples)]
        before = rng.choice((True, False))
        pairs = [(text, text) for text in texts]
        outputs = [_ast_output(text, rule, direction, before) for text in texts]
        reference = f"ast:{rule}:{direction}:{'before' if before else 'after'}"
    elif family == "novel_operator_transition":
        rule = rng.choice(("popcount_parity", "rotated_mod", "gcd_bucket"))
        direction = rng.choice(("special_other", "other_special"))
        texts = [_novel_input(rng, rule, direction, index if index < visible_examples else None,
                              encoding)
                 for index in range(visible_examples + hidden_examples)]
        before = rng.choice((True, False))
        pairs = [(text, text) for text in texts]
        outputs = [_novel_output(text, rule, direction, before, encoding) for text in texts]
        reference = f"novel_operator:{rule}:{direction}:{'before' if before else 'after'}"
    elif family == "stack_transition":
        rule = rng.choice(("fold_parity", "fold_mod3", "bit_splice"))
        direction = rng.choice(("special_other", "other_special"))
        texts = [_stack_input(rng, rule, direction, index if index < visible_examples else None,
                              encoding)
                 for index in range(visible_examples + hidden_examples)]
        before = rng.choice((True, False))
        pairs = [(text, text) for text in texts]
        outputs = [_stack_output(text, rule, direction, before, encoding) for text in texts]
        reference = f"stack:{rule}:{direction}:{'before' if before else 'after'}"
    elif family == "raw_stack_transition":
        rule = rng.choice(("raw_xor_parity", "raw_sum_mod4", "raw_splice_mod7"))
        direction = rng.choice(("special_other", "other_special"))
        texts = [_raw_stack_input(rng, rule, direction, index if index < visible_examples else None)
                 for index in range(visible_examples + hidden_examples)]
        before = rng.choice((True, False))
        pairs = [(text, text) for text in texts]
        outputs = [_raw_stack_output(text, rule, direction, before) for text in texts]
        reference = f"raw_stack:{rule}:{direction}:{'before' if before else 'after'}"
    elif family == "mutation_transition":
        rule = rng.choice(("mutation_xor_parity", "mutation_sum_mod5", "mutation_low_nibble"))
        direction = rng.choice(("special_other", "other_special"))
        texts = [_mutation_input(rng, rule, direction, index if index < visible_examples else None)
                 for index in range(visible_examples + hidden_examples)]
        before = rng.choice((True, False))
        pairs = [(text, text) for text in texts]
        outputs = [_mutation_output(text, rule, direction, before) for text in texts]
        reference = f"mutation:{rule}:{direction}:{'before' if before else 'after'}"
    elif family == "self_edit_transition":
        rule = rng.choice(("grammar_not", "grammar_nibble", "grammar_subfold"))
        direction = rng.choice(("special_other", "other_special"))
        texts = [_self_edit_input(rng, rule, direction, index if index < visible_examples else None)
                 for index in range(visible_examples + hidden_examples)]
        before = rng.choice((True, False))
        pairs = [(text, text) for text in texts]
        outputs = [_self_edit_output(text, rule, direction, before) for text in texts]
        reference = f"self_edit:{rule}:{direction}:{'before' if before else 'after'}"
    elif family == "macro_transition":
        rule = rng.choice(("grammar_not", "grammar_nibble", "grammar_subfold"))
        direction = rng.choice(("special_other", "other_special"))
        texts = [_self_edit_input(rng, rule, direction, index if index < visible_examples else None)
                 for index in range(visible_examples + hidden_examples)]
        before = rng.choice((True, False))
        pairs = [(text, text) for text in texts]
        outputs = [_self_edit_output(text, rule, direction, before) for text in texts]
        reference = f"macro:{rule}:{direction}:{'before' if before else 'after'}"
    elif family == "bit_transition":
        direction = rng.choice(("bit_on_off", "bit_off_on"))
        texts = [_bit_input(rng, direction, index if index < visible_examples else None)
                 for index in range(visible_examples + hidden_examples)]
        before = rng.choice((True, False))
        pairs = [(text, text) for text in texts]
        outputs = [_bit_output(text, direction, before) for text in texts]
        reference = f"bit_transition:{direction}:{'before' if before else 'after'}"
    elif family == "periodic_transition":
        direction = rng.choice(("special_other", "other_special"))
        texts = [_periodic_input(rng, "periodic_other" if direction == "special_other" else "other_periodic",
                                 index if index < visible_examples else None)
                 for index in range(visible_examples + hidden_examples)]
        before = rng.choice((True, False))
        pairs = [(text, text) for text in texts]
        outputs = [_periodic_output(text, direction, before) for text in texts]
        reference = f"periodic_transition:{direction}:{'before' if before else 'after'}"
    elif family == "parity_transition":
        direction = rng.choice(("even_odd", "odd_even"))
        texts = [_parity_input(rng, direction, index if index < visible_examples else None)
                 for index in range(visible_examples + hidden_examples)]
        before = rng.choice((True, False))
        pairs = [(text, text) for text in texts]
        outputs = [_parity_output(text, direction, before) for text in texts]
        reference = f"parity_transition:{direction}:{'before' if before else 'after'}"
    elif family == "vowel_transition":
        direction = rng.choice(("vowel_consonant", "consonant_vowel"))
        texts = [_vowel_input(rng, direction, index if index < visible_examples else None)
                 for index in range(visible_examples + hidden_examples)]
        before = rng.choice((True, False))
        pairs = [(text, text) for text in texts]
        outputs = [_vowel_output(text, direction, before) for text in texts]
        reference = f"vowel_transition:{direction}:{'before' if before else 'after'}"
    else:
        direction = rng.choice(("letter_digit", "digit_letter"))
        texts = [_transition_input(rng, direction, disjoint=(family == "transition_disjoint"))
                 for _ in range(visible_examples + hidden_examples)]
        before = rng.choice((True, False))
        pairs = [(text, text) for text in texts]
        outputs = [_transition_output(text, direction, before) for text in texts]
        reference = f"transition:{direction}:{'before' if before else 'after'}"
    examples = [[text, output] for (text, _), output in zip(pairs, outputs)]
    return {"id": digest([split, index, reference, examples])[:20], "reference": reference,
            "encoding": encoding, "visible": examples[:visible_examples],
            "hidden": examples[visible_examples:]}


def create_evolving_banks(config):
    rng = random.Random(config["bank_seed"])
    banks, metadata = {}, {}
    for split, count in config["bank_counts"].items():
        family = config["train_family"] if split == "train" else config["eval_family"]
        rows = [make_task(rng, split, index, family, config["visible_examples"], config["hidden_examples"]) for index in range(count)]
        banks[split] = rows
        metadata[split] = {"count": len(rows), "sha256": digest(rows)}
    return banks, metadata
