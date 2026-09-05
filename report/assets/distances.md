<!-- généré par scripts/report_assets.py, ne pas éditer à la main -->

# Distances de surface : ASD et MHD par tissu

| configuration | ASD LCR | ASD SG | ASD SB | MHD LCR | MHD SG | MHD SB |
|---|---:|---:|---:|---:|---:|---:|
| A+B+C, sans morphologie (référence) | 0.31 | 0.36 | 0.68 | 1.36 | 1.41 | 2.75 |
| palier 0 : max-tree + min-tree, nœud propre | 0.24 | 0.34 | 0.63 | 1.12 | 1.41 | 2.51 |
| palier 1 : max-tree + min-tree + remontée de branche | 0.24 | 0.33 | 0.61 | 1.08 | 1.37 | 2.38 |
| palier 2 : arbre des formes + remontée de branche | 0.26 | 0.34 | 0.64 | 1.21 | 1.41 | 2.53 |
| palier 3 : palier 2 + filtres de grain | 0.26 | 0.34 | 0.64 | 1.21 | 1.41 | 2.53 |
| palier 2, quantification sur 64 niveaux | 0.26 | 0.34 | 0.64 | 1.21 | 1.41 | 2.57 |
| palier 2, quantification par rang | 0.27 | 0.34 | 0.64 | 1.25 | 1.41 | 2.57 |
| configuration finale : tous les blocs | 0.24 | 0.32 | 0.61 | 1.17 | 1.33 | 2.41 |
| sélection des 40 meilleures colonnes | 0.29 | 0.36 | 0.75 | 1.25 | 1.41 | 3.03 |
| configuration finale + lissage et nettoyage | 0.40 | 0.30 | 0.84 | 1.95 | 1.37 | 3.67 |
| configuration finale + lissage, nettoyage et contrainte topologique | 0.40 | 0.32 | 0.84 | 1.95 | 1.41 | 3.66 |
| configuration finale + auto-contexte à deux étages | 0.23 | 0.30 | 0.59 | 1.12 | 1.21 | 2.44 |
Toutes les valeurs sont en millimètres, moyennées sur les 10 sujets du leave-one-out. MHD est le 95e percentile des distances de surface symétriques, définition retenue par les tableaux du challenge (voir `src/eval/metrics.py`). Plus petit est meilleur.

Le gain n'est pas seulement volumique : les mêmes blocs rapprochent aussi les surfaces. Comparaisons appariées sur la substance grise, chacune isolée dans sa propre famille (un seul test, la correction de Holm est donc neutre).

| comparaison | métrique | A | B | Δ | écart-type Δ | sujets améliorés | p brut | p ajusté (Holm) | d de Cohen | δ de Cliff | verdict |
|---|---|---:|---:|---:|---:|:---:|---:|---:|---:|---:|---|
| logreg_ABC → logreg_final | asd_gm | 0.3552 | 0.3166 | -0.0387 | 0.0087 | 10/10 | 0.002 | 0.002 | -4.42 | +1.00 | distinguable du bruit |
| logreg_ABC → logreg_final | mhd_gm | 1.4142 | 1.3314 | -0.0828 | 0.1746 | 2/10 | 0.500 | 0.500 | -0.47 | +0.20 | NON distinguable du bruit |

