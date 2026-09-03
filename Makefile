PY := .venv/bin/python
CLI := $(PY) -m src.cli

.PHONY: venv test inspect blocks stub features ablation clean-cache

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

# pré-calcule tous les blocs pour les 10 sujets (long la première fois, memmap ensuite)
features:
	$(CLI) features experiments/logreg_all.yaml

# tableau d'ablation bloc par bloc, régression logistique
ablation:
	for f in experiments/logreg_*.yaml; do $(CLI) run $$f; done
	$(PY) scripts/ablation_table.py

clean-cache:
	rm -rf cache/*
