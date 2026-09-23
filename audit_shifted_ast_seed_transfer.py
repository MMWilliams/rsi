"""Run the frozen shifted-AST audit with JSON-normalized generated tasks.

The task generator emits a tuple in reference.parameters. The sealed JSON
round-trips it as a list; normalize only this comparison, leaving the frozen
runner and its recorded hash unchanged.
"""
from __future__ import annotations

import json

import shifted_ast_seed_transfer as study


original_tasks_for=study.tasks_for


def json_normalized_tasks_for():
    return json.loads(json.dumps(original_tasks_for()))


def main():
    study.tasks_for=json_normalized_tasks_for
    study.audit()


if __name__=='__main__':main()
