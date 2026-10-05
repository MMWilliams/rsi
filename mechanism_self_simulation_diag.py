import multiprocessing, sys, numpy as np
from rsi.growth_coach import Simulator
from rsi.mechanism_worlds import Harness
from rsi.self_world_model import _matrix
import mechanism_earned_confirmation as conf
import mechanism_self_simulation as sim
from mechanism_earned_trust_screen import earning_of
SEED, N = 643101, 640
def rates(earned, truth, mask=None):
    has = truth.sum(0)
    return np.where(has > 0, (earned * truth).sum(0) / np.maximum(has, 1), np.nan), has
def corr(a, b, ha, hb, floor):
    ok = ~np.isnan(a) & ~np.isnan(b) & (ha >= floor) & (hb >= floor)
    return int(ok.sum()), round(float(np.corrcoef(a[ok], b[ok])[0, 1]), 3)
if __name__ == '__main__':
    h = Harness(); s = Simulator(h); K = len(h.key_names)
    _r, _g, training, _s, streams, *_ = conf.setup(h, SEED)
    real = earning_of(SEED, streams)
    truth = _matrix([[h.key_index[k] for k in w['keys']] for w in training], K)
    E = lambda dec: _matrix([conf.earned_set(d, s.row_keys, 1) for d in dec], K)
    jobs = [(i, streams[i]) for i in range(N)]
    with multiprocessing.get_context('spawn').Pool(12, initializer=sim._init_self, initargs=(SEED, SEED)) as p:
        same = p.map(sim._earn_self, jobs, chunksize=8)
    print('reproduces real earning exactly:', same == [list(map(list, d)) for d in real[:N]] or same == real[:N])
    with multiprocessing.get_context('spawn').Pool(12, initializer=sim._init_self, initargs=(SEED, SEED + 12345)) as p:
        fresh = p.map(sim._earn_self, jobs, chunksize=8)
    ra, ha = rates(E(real[:N]), truth[:N]); rb, hb = rates(E(fresh), truth[:N])
    rc, hc = rates(E(real[N:2*N]), truth[N:2*N])
    for floor in (1, 10, 20):
        print('floor', floor, 'same worlds, fresh examples:', corr(ra, rb, ha, hb, floor),
              ' other worlds:', corr(ra, rc, ha, hc, floor))
