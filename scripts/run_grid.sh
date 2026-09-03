#!/bin/bash
# Lance toutes les configs experiments/logreg_*.yaml (cache d'abord), puis le tableau d'ablation.
cd "$(dirname "$0")/.."
PY=.venv/bin/python
$PY -u -m src.cli features experiments/logreg_ABCDEF.yaml > results/features.log 2>&1
$PY -u -m src.cli features experiments/logreg_B_zero.yaml >> results/features.log 2>&1
for f in experiments/logreg_*.yaml; do
  r=$(basename "$f" .yaml)
  $PY -u -m src.cli run "$f" > "results/$r.log" 2>&1
done
$PY scripts/ablation_table.py > results/ablation.md
echo DONE > results/grid.done
