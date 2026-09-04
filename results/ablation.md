| run | blocs | n_feat | modèle | n_params | folds | Dice CSF | Dice GM | Dice WM | Dice moyen | ASD GM | MHD GM | Dice/log10(params) |
|---|---|---:|---|---:|---:|---|---|---|---:|---:|---:|---:|
| logreg_ABC | intensity+gaussian+spatial | 83 | logreg | 252 | 10 | 0.851 ± 0.015 | 0.805 ± 0.011 | 0.761 ± 0.017 | **0.8055** | 0.36 | 1.41 | 0.335 |
| logreg_ABCD_p3_l64 | intensity+gaussian+spatial+morpho | 135 | logreg | 408 | 10 | 0.866 ± 0.015 | 0.814 ± 0.010 | 0.765 ± 0.017 | **0.8149** | 0.34 | 1.41 | 0.312 |
| logreg_ABCD_p2 | intensity+gaussian+spatial+morpho | 135 | logreg | 408 | 10 | 0.866 ± 0.016 | 0.814 ± 0.010 | 0.766 ± 0.017 | **0.8154** | 0.34 | 1.41 | 0.312 |
| logreg_ABCD_p3 | intensity+gaussian+spatial+morpho | 135 | logreg | 408 | 10 | 0.866 ± 0.016 | 0.814 ± 0.010 | 0.766 ± 0.017 | **0.8154** | 0.34 | 1.41 | 0.312 |
| logreg_ABCD_p3_linear | intensity+gaussian+spatial+morpho | 135 | logreg | 408 | 10 | 0.866 ± 0.016 | 0.814 ± 0.010 | 0.766 ± 0.017 | **0.8154** | 0.34 | 1.41 | 0.312 |
| logreg_ABCD_p0 | intensity+gaussian+spatial+morpho | 107 | logreg | 324 | 10 | 0.866 ± 0.012 | 0.813 ± 0.010 | 0.767 ± 0.018 | **0.8156** | 0.34 | 1.41 | 0.325 |
| logreg_ABCD_p1 | intensity+gaussian+spatial+morpho | 187 | logreg | 564 | 10 | 0.868 ± 0.012 | 0.818 ± 0.011 | 0.772 ± 0.015 | **0.8191** | 0.33 | 1.37 | 0.298 |
| logreg_ABCDEF | intensity+gaussian+spatial+morpho+symmetry+context | 151 | logreg | 456 | 10 | 0.881 ± 0.014 | 0.825 ± 0.009 | 0.777 ± 0.017 | **0.8276** | 0.32 | 1.33 | 0.311 |
| logreg_final | intensity+gaussian+spatial+morpho+symmetry+context | 151 | logreg | 456 | 10 | 0.881 ± 0.014 | 0.825 ± 0.009 | 0.777 ± 0.017 | **0.8276** | 0.32 | 1.33 | 0.311 |
