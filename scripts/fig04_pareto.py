"""Pareto interne et comparaison officielle : deux régimes séparés."""
import json
import sys
from pathlib import Path
import matplotlib.pyplot as plt
import numpy as np
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.figstyle import ACCENT, NEUTRAL_EDGE, use
from src.eval.official import load_official_scores, XLSX_NAME

OURS = [('select_k40', '40 colonnes'), ('logreg_ABC', 'A+B+C'),
        ('logreg_ABCD_p0', 'palier 0'), ('logreg_ABCD_p1', 'palier 1'),
        ('logreg_ABCD_p2', 'palier 2'), ('logreg_ABCD_p3', 'palier 3'),
        ('logreg_ABCD_p2_l64', '64 niveaux'), ('logreg_ABCD_p2_rank', 'rangs'),
        ('logreg_final', 'tous les blocs'), ('logreg_final_smooth', 'lissage'),
        ('logreg_final_postproc', 'topologie'), ('autocontext_final', 'auto-contexte')]

def pareto_front(points):
    return sorted(p for p in points if not any(
        q[0] <= p[0] and q[1] >= p[1] and q != p for q in points))

def main():
    use()
    load = lambda name: json.loads((ROOT / 'results' / f'{name}.json').read_text(encoding='utf-8'))
    ours = [(load(k)['n_params'], load(k)['mean']['dice_mean'], label) for k, label in OURS]
    score = load_official_scores(ROOT / 'results' / XLSX_NAME)['dice_mean']
    n = load('submission')['n_params']
    refs = load('published_references')['methods']
    fig, (ax, zoom) = plt.subplots(1, 2, figsize=(8.0, 3.45), gridspec_kw={'width_ratios': [1.25, 1]})
    x, y = [p[0] for p in ours], [p[1] for p in ours]
    ax.scatter(x, y, facecolors='none', edgecolors=NEUTRAL_EDGE, s=22, label='nos variantes : leave-one-out')
    ax.scatter([n], [score], color=ACCENT, marker='*', s=100, label='notre test officiel')
    ax.annotate(f'test : {score:.4f}'.replace('.', ','), (n, score), xytext=(10, 4), textcoords='offset points', fontsize=8)
    for name, r in refs.items():
        d = np.mean([r[f'dice_{t}'] for t in ('csf', 'gm', 'wm')])
        ax.scatter(r['n_params'], d, marker='s', s=32, color=NEUTRAL_EDGE)
        ax.annotate(name, (r['n_params'], d), xytext=(0, 10 if name == 'MSL_SKKU' else -18),
                    textcoords='offset points', ha='center', fontsize=7.5)
    ax.set_xscale('log')
    ax.set_xlim(100, 4e7)
    ax.set_ylim(0.79, 0.956)
    ax.set_title('Test officiel et références publiées', fontsize=9)
    ax.set_xlabel('paramètres appris (échelle logarithmique)')
    ax.set_ylabel('Dice moyen')
    ax.legend(loc='lower right', fontsize=7, frameon=False)
    front = pareto_front([(a, b) for a, b, _ in ours])
    zoom.plot(*zip(*front), color=ACCENT, linewidth=1)
    zoom.scatter(x, y, facecolors='white', edgecolors=NEUTRAL_EDGE, s=24, zorder=3)
    for a, b, label in ours:
        offsets = {'40 colonnes': (4, -15), 'A+B+C': (4, 6), 'tous les blocs': (4, 6), 'auto-contexte': (-6, 7)}
        if label in offsets:
            zoom.annotate(label, (a,b), xytext=offsets[label], textcoords='offset points',
                          ha='right' if label == 'auto-contexte' else 'left', fontsize=7)
    zoom.set_xlim(100, 1030)
    zoom.set_ylim(0.797, 0.848)
    zoom.set_title('Zoom : front interne uniquement', fontsize=9)
    zoom.set_xlabel('paramètres appris')
    for a in (ax, zoom):
        a.grid(alpha=0.25)
        a.set_axisbelow(True)
    fig.tight_layout()
    out = ROOT / 'report/assets/fig04_pareto.pdf'
    fig.savefig(out, bbox_inches='tight')
    print(out)

if __name__ == '__main__':
    main()
