#!/bin/bash
# Chaîne : cache A+B+C puis 3 runs d'ablation. Logs dans results/*.log
cd "$(dirname "$0")/.."
PY=.venv/bin/python
$PY -u -m src.cli features experiments/logreg_intensity_gaussian_spatial.yaml > results/features_abc.log 2>&1
for r in logreg_intensity logreg_intensity_gaussian logreg_intensity_gaussian_spatial; do
  $PY -u -m src.cli run experiments/$r.yaml > results/$r.log 2>&1
done
echo DONE > results/ablation_abc.done
