#!/bin/bash
# Chaîne 2 : cache du bloc D (en parallèle de la chaîne 1), puis attend la fin de la chaîne 1
# et enchaîne les runs qui ont besoin de tous les caches.
cd "$(dirname "$0")/.."
PY=.venv/bin/python
$PY -u -m src.cli features experiments/cache_morpho.yaml > results/features_d.log 2>&1
while [ ! -f results/ablation_abc.done ]; do sleep 20; done
for r in logreg_all logreg_intensity_morpho logreg_intensity_spatial logreg_morpho logreg_gaussian logreg_all_boundary logreg_all_prior logreg_all_boundary_prior; do
  $PY -u -m src.cli run experiments/$r.yaml > results/$r.log 2>&1
done
echo DONE > results/ablation_d.done
