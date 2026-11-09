"""LaTeX tables for both papers, generated from the committed analysis JSON so
no number in them is typed by hand."""
import json

from rsi.common import ROOT

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
          'Median and minimum over seeds, 95\\% bootstrap interval of the median (10,000 resamples of seeds), and the number of seeds below the start.',
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
          'Recorded full-set proofs of the sealed seeds judged again on part of their own set: full-set acceptances the smaller set would lose and full-set rejections it would pass.',
          'tab:rejudged', 'lll', 'Set size & Acceptances lost & Rejections passed', rows)


if __name__ == '__main__':
    ten_seeds()
    rejudged()
