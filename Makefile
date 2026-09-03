PY := .venv/bin/python
CLI := $(PY) -m src.cli

.PHONY: venv test inspect blocks stub features grid table figures clean-cache

venv:
	python3 -m venv .venv && .venv/bin/pip install -U pip && .venv/bin/pip install -r requirements.txt

test:
	$(PY) -m pytest -q

inspect:
	$(PY) scripts/inspect_data.py

blocks:
	$(CLI) blocks

stub:
	$(CLI) run experiments/stub_random.yaml

# pré-calcule tous les blocs pour les 10 sujets (~15 min la première fois, memmap ensuite)
features:
	$(CLI) features experiments/logreg_ABCDEF.yaml

# grille complète d'ablation (toutes les configs experiments/logreg_*.yaml), ~1 h
grid:
	scripts/run_grid.sh

table:
	$(PY) scripts/ablation_table.py

figures:
	$(PY) scripts/plot_features.py 1

clean-cache:
	rm -rf cache/*
