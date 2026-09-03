#!/bin/bash
# Précalcule le cache de chaque configuration puis lance la boucle LOO, et écrit le tableau final.
cd "$(dirname "$0")/.."
PY=.venv/bin/python
: > results/features.log
for f in experiments/logreg_*.yaml; do
  $PY -u -m src.cli features "$f" >> results/features.log 2>&1
done
for f in experiments/logreg_*.yaml; do
  r=$(basename "$f" .yaml)
  $PY -u -m src.cli run "$f" > "results/$r.log" 2>&1
done
$PY scripts/ablation_table.py > results/ablation.md
echo DONE > results/grid.done
