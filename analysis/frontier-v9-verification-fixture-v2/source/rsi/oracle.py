"""Independent interpreter. Never imports or calls upstream dsl.run or parse.parse."""
from __future__ import annotations

import ast
import io
import re
import tokenize
import warnings

PATTERNS = {"WORD": r"[A-Za-z]+", "DIGITS": r"[0-9]+", "UPPER": r"[A-Z]+", "LOWER": r"[a-z]+"}


class InvalidProgram(ValueError):
    pass


def _reject_trailing_commas(program: str) -> None:
    """Enforce the published DSL grammar without importing its parser."""
    previous = None
    try:
        tokens = tokenize.generate_tokens(io.StringIO(program).readline)
        for token in tokens:
            if token.type in (tokenize.ENCODING, tokenize.NL, tokenize.NEWLINE,
                              tokenize.INDENT, tokenize.DEDENT, tokenize.COMMENT):
                continue
            if token.type == tokenize.OP and token.string == ")" and previous == ",":
                raise InvalidProgram("Trailing comma")
            previous = token.string
    except (tokenize.TokenError, IndentationError) as exc:
        raise InvalidProgram("Invalid tokenization") from exc


def execute(program: str, text: str) -> str:
    if len(program) > 2048 or len(text) > 1024:
        raise InvalidProgram("Resource limit")
    _reject_trailing_commas(program)
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", SyntaxWarning)
            tree = ast.parse(program, mode="eval")
    except (SyntaxError, RecursionError) as exc:
        raise InvalidProgram("Invalid syntax") from exc
    if sum(1 for _ in ast.walk(tree)) > 256:
        raise InvalidProgram("Too many AST nodes")

    def position(node):
        if isinstance(node, ast.Name) and re.fullmatch(r"C\d+", node.id):
            value = int(node.id[1:])
        elif isinstance(node, ast.BinOp) and isinstance(node.op, ast.Sub) and isinstance(node.left, ast.Name) and node.left.id == "C" and isinstance(node.right, ast.Constant) and type(node.right.value) is int:
            signed_index = -node.right.value
            value = signed_index if signed_index >= 0 else len(text) + signed_index
        elif isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "M" and len(node.args) == 3 and not node.keywords:
            token, ordinal, side = node.args
            if not isinstance(token, ast.Name) or token.id not in PATTERNS or not isinstance(ordinal, ast.Constant) or type(ordinal.value) is not int or not isinstance(side, ast.Name) or side.id not in ("start", "end"):
                raise InvalidProgram("Bad match position")
            matches = list(re.finditer(PATTERNS[token.id], text))
            if not 1 <= ordinal.value <= len(matches):
                raise InvalidProgram("Missing match")
            match = matches[ordinal.value - 1]
            value = match.start() if side.id == "start" else match.end()
        else:
            raise InvalidProgram("Bad position")
        if not 0 <= value <= len(text):
            raise InvalidProgram("Position out of range")
        return value

    def atom(node, depth=0):
        if depth > 8:
            raise InvalidProgram("Nesting limit")
        if isinstance(node, ast.Constant) and isinstance(node.value, str) and len(node.value) <= 128:
            return node.value
        if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Name) or node.keywords:
            raise InvalidProgram("Bad atom")
        name = node.func.id
        if name == "Sub" and len(node.args) == 2:
            return text[position(node.args[0]):position(node.args[1])]
        if name in ("upper", "lower", "cap") and len(node.args) == 1:
            value = atom(node.args[0], depth + 1)
            return {"upper": str.upper, "lower": str.lower, "cap": str.capitalize}[name](value)
        raise InvalidProgram("Unknown operation")

    node = tree.body
    if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Name) or node.func.id != "Concat" or node.keywords or not 1 <= len(node.args) <= 8:
        raise InvalidProgram("Expected bounded Concat")
    return "".join(atom(part) for part in node.args)


def outcomes(program: str, examples: list) -> list:
    result = []
    for text, _ in examples:
        try:
            result.append(execute(program, text))
        except (InvalidProgram, ValueError, TypeError, OverflowError, RecursionError):
            result.append(None)
    return result


def correct(program: str, examples: list) -> bool:
    return bool(examples) and outcomes(program, examples) == [output for _, output in examples]
