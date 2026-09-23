"""V52 cross-domain banks: delimiter training, transition evaluation."""

from __future__ import annotations

import random

from rsi.common import digest


def _delimiter_input(rng):
    kind = rng.choice(("email", "code", "slash"))
    if kind == "email":
        return f"{rng.choice(['ana','zoe','li','omar'])}.{rng.choice(['smith','khan','ito','lee'])}{rng.randint(1,99)}@{rng.choice(['example.com','research.org','lab.net'])}", "@"
    if kind == "code":
        return "".join(rng.choice("ABCDEFGH") for _ in range(rng.randint(2,5))) + "-" + str(rng.randint(10,99999)), "-"
    return f"{rng.randint(1,28):02d}/{rng.randint(1,12):02d}/{rng.randint(1990,2035)}", "/"


def _transition_input(rng):
    direction = rng.choice(("letter_digit", "digit_letter"))
    if direction == "letter_digit":
        return "".join(rng.choice("ABCDEFGHxyz") for _ in range(rng.randint(2,6))) + "".join(rng.choice("0123456789") for _ in range(rng.randint(1,6)))
    return "".join(rng.choice("0123456789") for _ in range(rng.randint(1,6))) + "".join(rng.choice("ABCDEFGHxyz") for _ in range(rng.randint(2,6)))


def _transition_output(text, direction, before):
    wanted = ("letter", "digit") if direction == "letter_digit" else ("digit", "letter")
    positions = [i for i in range(1, len(text)) if
                 ("letter" if text[i-1].isalpha() else "digit") == wanted[0] and
                 ("letter" if text[i].isalpha() else "digit") == wanted[1]]
    index = positions[0]
    return text[:index] if before else text[index:]


def make_task(rng, split, index, family, visible_examples=3, hidden_examples=13):
    if family == "delimiter":
        pairs = [_delimiter_input(rng) for _ in range(visible_examples + hidden_examples)]
        delimiter = pairs[0][1]
        pairs = [(text, delimiter) for text, _ in pairs]
        op = rng.choice(("before", "after"))
        outputs = []
        for text, delim in pairs:
            pos = text.find(delim)
            outputs.append(text[:pos] if op == "before" else text[pos + len(delim):])
        reference = f"{op}"
    else:
        direction = rng.choice(("letter_digit", "digit_letter"))
        texts = [_transition_input(rng) for _ in range(visible_examples + hidden_examples)]
        before = rng.choice((True, False))
        pairs = [(text, text) for text in texts]
        outputs = [_transition_output(text, direction, before) for text in texts]
        reference = f"transition:{direction}:{'before' if before else 'after'}"
    examples = [[text, output] for (text, _), output in zip(pairs, outputs)]
    return {"id": digest([split, index, reference, examples])[:20], "reference": reference,
            "visible": examples[:visible_examples], "hidden": examples[visible_examples:]}


def create_evolving_banks(config):
    rng = random.Random(config["bank_seed"])
    banks, metadata = {}, {}
    for split, count in config["bank_counts"].items():
        family = config["train_family"] if split == "train" else config["eval_family"]
        rows = [make_task(rng, split, index, family, config["visible_examples"], config["hidden_examples"]) for index in range(count)]
        banks[split] = rows
        metadata[split] = {"count": len(rows), "sha256": digest(rows)}
    return banks, metadata
