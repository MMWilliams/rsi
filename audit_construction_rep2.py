"""Independent audit of construction-improver confirmation replication two."""
from __future__ import annotations

import sys

import audit_construction_improver_confirmation as auditor
import construction_improver_confirmation as conf
import construction_confirmation_rep2 as rep2


def install():
    conf.DEST = rep2.DEST
    conf.PANELS = rep2.PANELS


if __name__ == '__main__':
    install()
    if len(sys.argv) > 1:
        auditor.rebuild_panel(sys.argv[1])
    else:
        auditor.main()
