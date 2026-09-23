"""Independent audit of complexity-improver confirmation replication two."""
from __future__ import annotations

import sys

import audit_complexity_improver_confirmation as auditor
import complexity_improver_confirmation as conf
import complexity_replication_two as rep2


def install():
    conf.DEST = rep2.DEST
    conf.PANELS = rep2.PANELS
    auditor.DEST = rep2.DEST
    auditor.PANELS = rep2.PANELS


if __name__ == '__main__':
    install()
    if len(sys.argv) > 1:
        auditor.rebuild_panel(sys.argv[1])
    else:
        auditor.main()
