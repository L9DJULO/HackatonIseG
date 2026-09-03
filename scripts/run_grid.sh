#!/bin/bash
# Grille d'ablation. Le cache du bloc morpho pèse ~2 Go par variante : on le calcule, on lance
# le run, puis on purge avant la variante suivante.
cd "$(dirname "$0")/.."
PY=.venv/bin/python
RUNS="${*:-logreg_ABC logreg_ABCD_p0 logreg_ABCD_p1 logreg_ABCD_p2 logreg_ABCD_p3 logreg_ABCDEF logreg_ABCD_p3_l64 logreg_ABCD_p3_linear logreg_final}"
for r in $RUNS; do
  $PY scripts/purge_cache.py experiments/$r.yaml >> results/features.log 2>&1
  $PY -u -m src.cli features experiments/$r.yaml >> results/features.log 2>&1
  $PY -u -m src.cli run experiments/$r.yaml > results/$r.log 2>&1
done
$PY scripts/ablation_table.py > results/ablation.md
echo DONE > results/grid.done
