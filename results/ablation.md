| run | blocs | n_feat | modèle | n_params | folds | Dice CSF | Dice GM | Dice WM | Dice moyen | ASD GM | MHD GM | Dice/log10(params) |
|---|---|---:|---|---:|---:|---|---|---|---:|---:|---:|---:|
| logreg_ABC | intensity+gaussian+spatial | 83 | logreg | 418 | 10 | 0.846 ± 0.011 | 0.804 ± 0.012 | 0.763 ± 0.017 | **0.8046** | 0.36 | 1.45 | 0.307 |
| logreg_ABCD_p3_l64 | intensity+gaussian+spatial+morpho | 141 | logreg | 708 | 10 | 0.861 ± 0.012 | 0.813 ± 0.011 | 0.768 ± 0.018 | **0.8140** | 0.34 | 1.41 | 0.286 |
| logreg_ABCD_p3 | intensity+gaussian+spatial+morpho | 141 | logreg | 708 | 10 | 0.862 ± 0.012 | 0.814 ± 0.011 | 0.768 ± 0.017 | **0.8148** | 0.34 | 1.41 | 0.286 |
| logreg_ABCD_p0 | intensity+gaussian+spatial+morpho | 107 | logreg | 538 | 10 | 0.864 ± 0.013 | 0.812 ± 0.010 | 0.768 ± 0.018 | **0.8149** | 0.34 | 1.41 | 0.298 |
| logreg_ABCD_p2 | intensity+gaussian+spatial+morpho | 135 | logreg | 678 | 10 | 0.862 ± 0.012 | 0.814 ± 0.011 | 0.768 ± 0.017 | **0.8149** | 0.34 | 1.41 | 0.288 |
| logreg_ABCD_p3_linear | intensity+gaussian+spatial+morpho | 141 | logreg | 708 | 10 | 0.867 ± 0.015 | 0.817 ± 0.010 | 0.769 ± 0.018 | **0.8176** | 0.33 | 1.41 | 0.287 |
| logreg_ABCD_p1 | intensity+gaussian+spatial+morpho | 187 | logreg | 938 | 10 | 0.869 ± 0.013 | 0.818 ± 0.010 | 0.772 ± 0.018 | **0.8198** | 0.33 | 1.41 | 0.276 |
| logreg_ABCDEF | intensity+gaussian+spatial+morpho+symmetry+context | 157 | logreg | 788 | 10 | 0.876 ± 0.013 | 0.823 ± 0.013 | 0.777 ± 0.018 | **0.8254** | 0.32 | 1.33 | 0.285 |
| logreg_final | intensity+gaussian+spatial+morpho+symmetry+context | 151 | logreg | 758 | 10 | 0.882 ± 0.013 | 0.826 ± 0.011 | 0.779 ± 0.018 | **0.8289** | 0.32 | 1.29 | 0.288 |
