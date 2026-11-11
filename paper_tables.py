"""LaTeX tables for both papers, generated from the committed analysis JSON so
no number in them is typed by hand."""
import json

from rsi.common import ROOT
from summarize_v11_replication import DRAWS

PAPER = ROOT / 'paper'
NAMES = {'mech': 'mechanism worlds', 'metric777001': 'metric777001', 'metric555001': 'metric555001'}


def load(name):
    return json.loads((ROOT / 'analysis' / name).read_text())


def pct(ratio):
    return f'{100 * (ratio - 1):+.0f}\\%'.replace('+', '+')


def write(name, caption, label, columns, header, rows):
    body = '\n'.join(' & '.join(r) + ' \\\\' for r in rows)
    (PAPER / name).write_text(
        f'\\begin{{table}}[t]\n\\centering\n\\caption{{{caption}}}\n\\label{{{label}}}\n\\small\n'
        f'\\begin{{tabular}}{{{columns}}}\n\\toprule\n{header} \\\\\n\\midrule\n{body}\n\\bottomrule\n\\end{{tabular}}\n\\end{{table}}\n')


def ten_seeds():
    data = load('review002-replication.json')
    areas = [k for k in data['pools'] if '/' not in k]
    rows = []
    for area in areas:
        for key in [area] + [k for k in data['pools'] if k.startswith(area + '/')]:
            p = data['pools'][key]
            if key.endswith('/env'):      # a single-pool area's pool repeats the area
                continue
            label = NAMES.get(area, area) if key == area else '\\quad ' + key.split('/')[1].replace('_', ' ')
            rows.append([label, pct(p['median']), pct(p['minimum']), f'{pct(p["interval"][0])} to {pct(p["interval"][1])}', str(p['below_100'])])
    write('table-ten-pools.tex',
          'Version 11.1 on ten sealed seeds: change from the starting state to the retained state on fresh held-out sets, by area and pool. '
          f'Median and minimum over seeds, 95\\% bootstrap interval of the median ({DRAWS:,} resamples of seeds), and the number of seeds below the start. '
          'Each seed contributes one draw of 24 worlds per pool; the interval is over random seeds for the fixed area structures.',
          'tab:tenpools', 'lrrrr', 'Area or pool & Median & Weakest seed & 95\\% interval & Seeds below start', rows)
    rows = []
    for s in data['seeds']:
        failed = [k[2:] for k, ok in s['gates'].items() if not ok and k != '5_adopted']   # gate 5 is reported, not required
        rows.append([str(s['seed']), f'{s["level0_cost"]:.2f}$\\times$', f'{s["all_proof_cost"]:.2f}$\\times$', str(s['kept_proofs']),
                     str(len(s['adopted'])), ', '.join(failed) + ' fails' if failed else 'all pass'])
    write('table-ten-seeds.tex',
          'Version 11.1 per seed: cost of level-0 proofs and of all proofs relative to living (limits 3.5 and 5.0), accepted changes, all of which replayed, procedure changes adopted, and the gate outcome.',
          'tab:tenseeds', 'lrrrrl', 'Seed & Level-0 & All proofs & Accepted & Adopted & Gates', rows)


def rejudged():
    data = load('review002-rejudged.json')
    rows = []
    for key, label in (('1/2', 'half'), ('1/4', 'quarter')):
        t = data['set_size'][key]
        accepted, rejected = t['accept_kept'] + t['accept_lost'], t['reject_passed'] + t['reject_held']
        rows.append([label, f'{t["accept_lost"]} of {accepted} ({100 * t["accept_lost"] / accepted:.0f}\\%)',
                     f'{t["reject_passed"]} of {rejected} ({100 * t["reject_passed"] / rejected:.0f}\\%)'])
    write('table-rejudged.tex',
          'Recorded full-set proofs of the sealed seeds judged again on part of their own set: full-set interval passes the smaller set would lose '
          '(a pass is kept only if it also clears the cross-area check) and full-set interval failures it would pass.',
          'tab:rejudged', 'lll', 'Set size & Passes lost & Failures passed', rows)


def arms():
    data = load('review002-arms.json')
    rows = []
    for arm, a in data['arms'].items():
        runs = [a['runs'][t] for t in data['tags']]
        diff = ', '.join(f'${x:+.3f}$' for x in a['G_minus_full']) if 'G_minus_full' in a else '--'
        harm = f'{a["harm"]["harmful"]} of {a["harm"]["kept"]}' if a['harm'] else '--'
        rows.append([arm, f'{a["mean_G"]:.3f}', diff, f'{a["mean_total_scans"] / 1e6:.0f}',
                     ', '.join(str(r['kept']) for r in runs), harm, a.get('rule', '--')])
    write('table-arms.tex',
          f'The review-002 arms on seeds 919127 to 919129, meta-level off. G is the mean over the seven areas of ln(retained/start) on fresh held-out sets; '
          f'the difference from full is per seed; scans are live plus proof, mean over seeds, in millions; harmful counts kept changes that lowered their own area on a fresh set. '
          f'Outcomes follow the rules committed before any arm ran; invention is judged on the unfamiliar-family pools of mech and str7, not on G. Brier score of the eight committed forecasts {data["brier"]:.3f}.',
          'tab:arms', 'lrlrlll', 'Arm & G & G $-$ full, per seed & Scans & Kept & Harmful & Outcome', rows)


def second_draw():
    data = load('review002-second-draw.json')
    first = load('review002-arms.json')['arms']
    rows = []
    for arm, a in data['arms'].items():
        runs = [data['runs'][t][arm] for t in data['tags']]
        diff = ', '.join(f'${r["G_minus_full"]:+.3f}${"" if r["verdict"] == "tie" else "*"}' for r in runs) if 'G_minus_full' in runs[0] else '--'
        rows.append(['start, nothing withheld' if arm == 'open' else arm, f'{first[arm]["mean_G"]:.3f}' if arm in first else '--',
                     f'{a["mean_G"]:.3f}', diff])
    write('table-second-draw.tex',
          f'The arms scored again on a second evaluation draw (salt {data["salt"]}, {data["per_pool"]} worlds per pool) that nothing had used. '
          'G as in Table~\\ref{tab:arms}, mean over the three seeds, on the first and the second draw; then the difference from full on the second draw, per seed. '
          f'A star marks a difference whose paired 95\\% bootstrap interval over worlds ({data["draws"]:,} resamples within pools) excludes zero. '
          'The last row is the starting state given every generator atom, with no model and no prior.',
          'tab:seconddraw', 'lrrl', 'Arm & G, first draw & G, second draw & G $-$ full on the second draw, per seed', rows)


def truth():
    data = load('review002-truth.json')
    labels = (('kept', 'whole rule, as run'), ('full', 'own-area test, as run'), ('half', 'interval, half set'),
              ('quarter', 'interval, quarter set'), ('point', 'point, half set'))
    rows = [[label] + [f'${r[k]:+.1f}$' if k == 'mean_gain' else str(r[k])
                       for r in (data['rules'][rule]['passed'], data['rules'][rule]['refused'])
                       for k in ('n', 'harmful', 'beneficial', 'unresolved', 'mean_gain')] for rule, label in labels]
    write('table-truth.tex',
          f'What the {data["candidates"]} candidates tested on seeds 919127 to 919129 really did, on a truth set of {data["own"]} fresh worlds of their own area. '
          'A candidate is harmful (H) or beneficial (B) when the paired 95\\% bootstrap interval of its gain over the state it was tested against '
          f'({data["draws"]:,} resamples of worlds within pools) is below or above zero, and unresolved (U) otherwise; gain is the mean true gain in tasks per world. '
          'The first row is the acceptance rule as it ran, cross-area check included, and the second its own-area test alone. '
          'The others judge the recorded test results again: the plain interval rule on half and a quarter of the set, and a positive point gain on half.',
          'tab:truth', 'lrrrrrrrrrr',
          ' & \\multicolumn{5}{c}{Passed} & \\multicolumn{5}{c}{Refused} \\\\\nRule & all & H & B & U & gain & all & H & B & U & gain', rows)


if __name__ == '__main__':
    ten_seeds()
    rejudged()
    truth()
    arms()
    second_draw()
