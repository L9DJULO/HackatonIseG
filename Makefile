PY := .venv/bin/python
CLI := $(PY) -m src.cli

.PHONY: venv test inspect blocks features grid report-assets cost figures report-facts report-figures pdf clean-cache

venv:
	python3 -m venv .venv && .venv/bin/pip install -U pip && .venv/bin/pip install -r requirements.txt

test:
	$(PY) -m pytest -q

inspect:
	$(PY) scripts/inspect_data.py

blocks:
	$(CLI) blocks

# pré-calcule tous les blocs pour les 10 sujets (~15 min la première fois, memmap ensuite)
features:
	$(CLI) features experiments/logreg_ABCDEF.yaml

# grille complète d'ablation (toutes les configs experiments/logreg_*.yaml), ~1 h
grid:
	scripts/run_grid.sh

# régénère report/assets/ depuis results/*.json : tableaux, statistiques, chiffres citables
report-assets:
	$(PY) scripts/report_assets.py

# mesure le budget de frugalité de la configuration finale
cost:
	$(PY) scripts/measure_cost.py experiments/logreg_final.yaml
	$(PY) scripts/measure_cost.py experiments/logreg_ABC.yaml

figures:
	$(PY) scripts/plot_features.py 1

# recouvrement SG/SB sur les 10 sujets + classement par ratio brut (sections 1 et 2)
report-facts:
	$(PY) scripts/isointensity.py
	$(PY) scripts/ratio_argument.py

# figures 1 a 3 du rapport, en PDF vectoriel dans report/assets/
report-figures:
	$(PY) scripts/fig01_isointense.py
	$(PY) scripts/fig02_pipeline.py
	$(PY) scripts/fig03_shapes.py

clean-cache:
	rm -rf cache/*

# ---------------------------------------------------------------------------
# Rapport : source Markdown -> PDF via pandoc + xelatex
# ---------------------------------------------------------------------------
PANDOC_FLAGS := --from=markdown+raw_tex+tex_math_dollars \
                --pdf-engine=xelatex \
                --citeproc --bibliography=report/refs.bib \
                --include-in-header=report/preamble.tex

REPORT_DEPS := report/rapport.md report/refs.bib report/preamble.tex \
               $(wildcard report/assets/*.pdf)

pdf: report/rapport.pdf

report/rapport.pdf: $(REPORT_DEPS)
	pandoc report/rapport.md -o $@ $(PANDOC_FLAGS)
