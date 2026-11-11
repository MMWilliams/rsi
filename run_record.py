"""run_arms.py with one more arm, 'record': the full arm with the two states of
every proof saved (rsi/seed_record.py). Usage: run_record.py record <tag> <seed>;
state goes to seeds/record_<tag>.
"""
import sys

import run_arms
from rsi.seed_arms import ARMS
from rsi.seed_record import Recording

ARMS['record'] = Recording

if __name__ == '__main__':
    sys.exit(run_arms.main())
