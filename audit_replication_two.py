"""Independent audit of replication two.

Same auditor as replication one, pointed at the second run's directory and
seeds. Run one panel per process, then with no argument to combine.
"""
from __future__ import annotations

import sys

import audit_contextual_improver_transfer as auditor
import contextual_improver_transfer as improver
import heterogeneous_ast_environment as env
import heterogeneous_replication_two as rep2


def install():
    env.DEST = rep2.DEST
    env.PANELS = rep2.PANELS
    improver.DEST = rep2.DEST
    improver.OUT = rep2.DEST / 'improver_results.json'
    auditor.DEST = rep2.DEST
    auditor.PANELS = rep2.PANELS
    auditor.OUT = rep2.DEST / 'audit.json'


if __name__ == '__main__':
    install()
    if len(sys.argv) > 1:
        auditor.rebuild_panel(sys.argv[1])
    else:
        auditor.main()
