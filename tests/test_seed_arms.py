import numpy as np

from run_arms import lives_of, schedule_for
from rsi.seed_arms import independent


def test_frequency_orders_rows_by_earned_counts():
    appearance = np.array([5, 2, 9]) / 10
    pair = independent(appearance)
    assert list(np.argsort(-np.diag(pair))) == [2, 0, 1]
    assert np.isclose(pair[0, 2], .45) and np.isclose(pair[2, 0], .45)


def test_unmatched_arms_keep_the_schedule():
    steps = lives_of('mech:4,drawn7:3,mech:2')
    assert steps == [('mech', 4), ('drawn7', 3), ('mech', 2)]
    assert schedule_for('accept-all', 'unused', steps) == steps
