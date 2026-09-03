# Ablation bloc par bloc — régression logistique sklearn (stub), LOO 10 folds, seed 0, 20 000 voxels/classe/sujet

Généré par `python scripts/ablation_table.py results/logreg_*.json`. n_params = convention stub : (n_feat+1)×3 + 2×n_feat (scaler).

| run | blocs | n_feat | modèle | n_params | folds | Dice CSF | Dice GM | Dice WM | Dice moyen | ASD GM | MHD GM | Dice/log10(params) |
|---|---|---:|---|---:|---:|---|---|---|---:|---:|---:|---:|
| logreg_intensity | intensity | 6 | logreg | 33 | 10 | 0.766 ± 0.037 | 0.628 ± 0.023 | 0.601 ± 0.027 | **0.6650** | 0.48 | 1.51 | 0.438 |
| logreg_intensity_spatial | intensity+spatial | 14 | logreg | 73 | 10 | 0.780 ± 0.044 | 0.646 ± 0.020 | 0.632 ± 0.024 | **0.6858** | 0.46 | 1.54 | 0.368 |
| logreg_morpho | morpho | 42 | logreg | 213 | 10 | 0.756 ± 0.041 | 0.652 ± 0.025 | 0.659 ± 0.029 | **0.6889** | 0.45 | 1.41 | 0.296 |
| logreg_intensity_morpho | intensity+morpho | 48 | logreg | 243 | 10 | 0.788 ± 0.030 | 0.681 ± 0.029 | 0.663 ± 0.028 | **0.7106** | 0.44 | 1.45 | 0.298 |
| logreg_gaussian | gaussian | 68 | logreg | 343 | 10 | 0.828 ± 0.022 | 0.739 ± 0.013 | 0.742 ± 0.022 | **0.7696** | 0.43 | 1.45 | 0.304 |
| logreg_intensity_gaussian | intensity+gaussian | 74 | logreg | 373 | 10 | 0.834 ± 0.020 | 0.750 ± 0.010 | 0.751 ± 0.022 | **0.7784** | 0.41 | 1.41 | 0.303 |
| logreg_all_boundary | intensity+gaussian+spatial+morpho | 124 | logreg | 623 | 10 | 0.853 ± 0.021 | 0.752 ± 0.011 | 0.765 ± 0.025 | **0.7902** | 0.38 | 1.41 | 0.283 |
| logreg_intensity_gaussian_spatial | intensity+gaussian+spatial | 82 | logreg | 413 | 10 | 0.845 ± 0.019 | 0.770 ± 0.013 | 0.769 ± 0.025 | **0.7949** | 0.38 | 1.41 | 0.304 |
| logreg_all | intensity+gaussian+spatial+morpho | 124 | logreg | 623 | 10 | 0.854 ± 0.017 | 0.779 ± 0.012 | 0.774 ± 0.023 | **0.8021** | 0.36 | 1.41 | 0.287 |
| logreg_all_boundary_prior | intensity+gaussian+spatial+morpho | 124 | logreg | 623 | 10 | 0.855 ± 0.013 | 0.798 ± 0.010 | 0.768 ± 0.024 | **0.8070** | 0.36 | 1.41 | 0.289 |
| logreg_all_prior | intensity+gaussian+spatial+morpho | 124 | logreg | 623 | 10 | 0.854 ± 0.012 | 0.806 ± 0.013 | 0.768 ± 0.022 | **0.8093** | 0.36 | 1.41 | 0.290 |
