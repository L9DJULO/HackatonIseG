<!-- généré par scripts/report_assets.py, ne pas éditer à la main -->

# Comparaisons appariées

Famille de 14 comparaisons déclarées à l'avance. Le verdict est rendu sur la p-valeur ajustée de Holm, jamais sur la brute.

| comparaison | métrique | A | B | Δ | écart-type Δ | sujets améliorés | p brut | p ajusté (Holm) | d de Cohen | δ de Cliff | verdict |
|---|---|---:|---:|---:|---:|:---:|---:|---:|---:|---:|---|
| logreg_ABC → logreg_ABCD_p0 | mean | 0.8055 | 0.8156 | +0.0102 | 0.0022 | 10/10 | 0.002 | 0.027 | +4.58 | +1.00 | distinguable du bruit |
| logreg_ABCD_p0 → logreg_ABCD_p1 | mean | 0.8156 | 0.8191 | +0.0035 | 0.0022 | 10/10 | 0.002 | 0.027 | +1.57 | +1.00 | distinguable du bruit |
| logreg_ABCD_p0 → logreg_ABCD_p2 | mean | 0.8156 | 0.8154 | -0.0002 | 0.0032 | 4/10 | 0.625 | 1.000 | -0.07 | -0.20 | NON distinguable du bruit |
| logreg_ABCD_p1 → logreg_ABCD_p2 | mean | 0.8191 | 0.8154 | -0.0037 | 0.0037 | 1/10 | 0.064 | 0.322 | -1.00 | -0.80 | NON distinguable du bruit |
| logreg_ABCD_p2 → logreg_ABCD_p3 | mean | 0.8154 | 0.8154 | +0.0000 | 0.0006 | 6/10 | 0.695 | 1.000 | +0.06 | +0.20 | NON distinguable du bruit |
| logreg_ABCD_p2 → logreg_ABCD_p2_rank | mean | 0.8154 | 0.8136 | -0.0018 | 0.0030 | 2/10 | 0.064 | 0.322 | -0.60 | -0.60 | NON distinguable du bruit |
| logreg_ABCD_p2 → logreg_ABCD_p2_l64 | mean | 0.8154 | 0.8149 | -0.0005 | 0.0005 | 1/10 | 0.010 | 0.068 | -0.94 | -0.80 | NON distinguable du bruit |
| logreg_ABC → logreg_final | mean | 0.8055 | 0.8276 | +0.0221 | 0.0034 | 10/10 | 0.002 | 0.027 | +6.49 | +1.00 | distinguable du bruit |
| logreg_ABCD_p2 → logreg_final | mean | 0.8154 | 0.8276 | +0.0122 | 0.0039 | 10/10 | 0.002 | 0.027 | +3.15 | +1.00 | distinguable du bruit |
| logreg_final → logreg_final_smooth | mean | 0.8276 | 0.8246 | -0.0031 | 0.0046 | 3/10 | 0.084 | 0.322 | -0.66 | -0.40 | NON distinguable du bruit |
| logreg_final_smooth → logreg_final_postproc | mean | 0.8246 | 0.8235 | -0.0011 | 0.0005 | 0/10 | 0.002 | 0.027 | -2.13 | -1.00 | distinguable du bruit |
| logreg_final → logreg_final_postproc | mean | 0.8276 | 0.8235 | -0.0042 | 0.0049 | 3/10 | 0.037 | 0.223 | -0.85 | -0.40 | NON distinguable du bruit |
| logreg_final → autocontext_final | mean | 0.8276 | 0.8399 | +0.0122 | 0.0017 | 10/10 | 0.002 | 0.027 | +7.12 | +1.00 | distinguable du bruit |
| logreg_final → select_k40 | mean | 0.8276 | 0.8036 | -0.0240 | 0.0025 | 0/10 | 0.002 | 0.027 | -9.64 | -1.00 | distinguable du bruit |

- **apport du bloc D sans remontée de branche** : Δ = +0.0102, 10/10 sujets améliorés, p = 0.002 brut et 0.027 après Holm, distinguable du bruit.
- **apport de la remontée de branche** : Δ = +0.0035, 10/10 sujets améliorés, p = 0.002 brut et 0.027 après Holm, distinguable du bruit.
- **arbre des formes contre max-tree + min-tree** : Δ = -0.0002, 4/10 sujets améliorés, p = 0.625 brut et 1.000 après Holm, NON distinguable du bruit.
- **auto-dualité à attributs identiques** : Δ = -0.0037, 1/10 sujets améliorés, p = 0.064 brut et 0.322 après Holm, NON distinguable du bruit.
- **apport des filtres de grain** : Δ = +0.0000, 6/10 sujets améliorés, p = 0.695 brut et 1.000 après Holm, NON distinguable du bruit.
- **quantification par rang contre linéaire** : Δ = -0.0018, 2/10 sujets améliorés, p = 0.064 brut et 0.322 après Holm, NON distinguable du bruit.
- **64 niveaux contre 256** : Δ = -0.0005, 1/10 sujets améliorés, p = 0.010 brut et 0.068 après Holm, NON distinguable du bruit.
- **apport de tous les blocs sur la référence** : Δ = +0.0221, 10/10 sujets améliorés, p = 0.002 brut et 0.027 après Holm, distinguable du bruit.
- **apport des blocs symétrie et contexte** : Δ = +0.0122, 10/10 sujets améliorés, p = 0.002 brut et 0.027 après Holm, distinguable du bruit.
- **apport du lissage et du nettoyage seuls** : Δ = -0.0031, 3/10 sujets améliorés, p = 0.084 brut et 0.322 après Holm, NON distinguable du bruit.
- **apport de la contrainte topologique par-dessus** : Δ = -0.0011, 0/10 sujets améliorés, p = 0.002 brut et 0.027 après Holm, distinguable du bruit.
- **apport du post-traitement complet** : Δ = -0.0042, 3/10 sujets améliorés, p = 0.037 brut et 0.223 après Holm, NON distinguable du bruit.
- **apport de l'auto-contexte** : Δ = +0.0122, 10/10 sujets améliorés, p = 0.002 brut et 0.027 après Holm, distinguable du bruit.
- **coût en Dice de la sélection à 40 colonnes** : Δ = -0.0240, 0/10 sujets améliorés, p = 0.002 brut et 0.027 après Holm, distinguable du bruit.
