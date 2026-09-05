<!-- généré par scripts/report_assets.py, ne pas éditer à la main -->

# Ablation, leave-one-out sur 10 sujets

| configuration | features | paramètres | Dice LCR | Dice SG | Dice SB | Dice moyen | ASD SG (mm) | MHD SG (mm) |
|---|---:|---:|---|---|---|---:|---:|---:|
| A+B+C, sans morphologie (référence) | 83 | 252 | 0.851 ± 0.015 | 0.805 ± 0.011 | 0.761 ± 0.017 | **0.8055** | 0.36 | 1.41 |
| palier 0 : max-tree + min-tree, nœud propre | 107 | 324 | 0.866 ± 0.012 | 0.813 ± 0.010 | 0.767 ± 0.018 | **0.8156** | 0.34 | 1.41 |
| palier 1 : max-tree + min-tree + remontée de branche | 187 | 564 | 0.868 ± 0.012 | 0.818 ± 0.011 | 0.772 ± 0.015 | **0.8191** | 0.33 | 1.37 |
| palier 2 : arbre des formes + remontée de branche | 135 | 408 | 0.866 ± 0.016 | 0.814 ± 0.010 | 0.766 ± 0.017 | **0.8154** | 0.34 | 1.41 |
| palier 3 : palier 2 + filtres de grain | 141 | 426 | 0.866 ± 0.016 | 0.814 ± 0.010 | 0.766 ± 0.017 | **0.8154** | 0.34 | 1.41 |
| palier 2, quantification sur 64 niveaux | 135 | 408 | 0.866 ± 0.015 | 0.814 ± 0.010 | 0.765 ± 0.017 | **0.8149** | 0.34 | 1.41 |
| palier 2, quantification par rang | 135 | 408 | 0.862 ± 0.013 | 0.813 ± 0.011 | 0.766 ± 0.017 | **0.8136** | 0.34 | 1.41 |
| configuration finale : tous les blocs | 151 | 456 | 0.881 ± 0.014 | 0.825 ± 0.009 | 0.777 ± 0.017 | **0.8276** | 0.32 | 1.33 |
| sélection des 40 meilleures colonnes | 151 | 163 | 0.861 ± 0.013 | 0.804 ± 0.009 | 0.746 ± 0.017 | **0.8036** | 0.36 | 1.41 |
| configuration finale + lissage et nettoyage | 151 | 456 | 0.876 ± 0.013 | 0.825 ± 0.011 | 0.773 ± 0.017 | **0.8246** | 0.30 | 1.37 |
| configuration finale + lissage, nettoyage et contrainte topologique | 151 | 456 | 0.877 ± 0.013 | 0.823 ± 0.011 | 0.770 ± 0.017 | **0.8235** | 0.32 | 1.41 |
| configuration finale + auto-contexte à deux étages | 151 | 939 | 0.891 ± 0.015 | 0.834 ± 0.009 | 0.795 ± 0.015 | **0.8399** | 0.30 | 1.21 |
