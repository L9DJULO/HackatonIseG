<!-- généré par scripts/isointensity.py, ne pas éditer à la main -->

# Recouvrement des distributions substance grise / substance blanche

OVL = somme des minima de deux histogrammes normalisés à 256 classes, sur l'étendue
intra-masque du sujet et de la modalité. 0 = disjoint, 1 = identique.
Moyenne et écart-type sur les 10 sujets annotés.

| signal | OVL moyen | écart-type | min | max | plafond de l'estimateur | écart au plafond | exactitude maximale d'une décision par voxel |
|---|---:|---:|---:|---:|---:|---:|---:|
| T1 | 0.701 | 0.048 | 0.656 | 0.805 | 0.991 | 0.291 | 65.0 % |
| T2 | 0.867 | 0.041 | 0.788 | 0.924 | 0.990 | 0.123 | 56.6 % |
| ratio T1/T2 | 0.831 | 0.051 | 0.765 | 0.910 | 0.989 | 0.158 | 58.4 % |
| couple (T1, T2) | 0.615 | 0.027 | 0.563 | 0.650 | 0.982 | 0.367 | 69.3 % |

Détail par sujet :

| sujet | OVL T1 | OVL T2 | OVL ratio | OVL couple (T1, T2) |
|---|---:|---:|---:|---:|
| 1 | 0.656 | 0.911 | 0.768 | 0.623 |
| 2 | 0.805 | 0.788 | 0.910 | 0.647 |
| 3 | 0.693 | 0.877 | 0.848 | 0.610 |
| 4 | 0.734 | 0.873 | 0.855 | 0.650 |
| 5 | 0.661 | 0.924 | 0.765 | 0.639 |
| 6 | 0.675 | 0.866 | 0.814 | 0.598 |
| 7 | 0.686 | 0.857 | 0.834 | 0.563 |
| 8 | 0.751 | 0.815 | 0.906 | 0.617 |
| 9 | 0.672 | 0.875 | 0.787 | 0.608 |
| 10 | 0.671 | 0.887 | 0.825 | 0.594 |
