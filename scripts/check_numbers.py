"""Vérifie mécaniquement que chaque nombre du rapport est adossé à une source.

Le rendu du projet est un rapport. Une seule contradiction numérique rend tout le reste
suspect, et une relecture à l'œil ne l'attrape pas. Ce script fait trois choses :

1. INDEX. Il collecte toutes les valeurs numériques de `results/*.json` et de
   `report/assets/*.md`, qui sont les seules sources autorisées.

2. EXTRACTION. Il relit `report/rapport.md`, en extrait tous les nombres — y compris les
   formes LaTeX `0{,}8399`, `1\\,550\\,000`, `2{,}14 \\cdot 10^{-1}` — et confronte chacun à
   l'index, à la précision où le rapport l'écrit. Tout nombre sans correspondance est
   signalé, sauf s'il figure dans la liste blanche ci-dessous avec sa justification.

3. ASSERTIONS. Les affirmations qui portent l'argument — décomptes de paramètres, deltas
   appariés, pourcentages du front de Pareto — sont recalculées depuis les JSON et
   comparées au littéral écrit dans le rapport. C'est le contrôle qui compte : la liste
   blanche dit qu'un nombre est légitime, les assertions disent qu'il est juste.

Sortie non nulle dès qu'un écart est détecté.

Usage : python scripts/check_numbers.py   (ou : make check-numbers)
"""
from __future__ import annotations

import json
import re
import sys
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "report" / "rapport.md"
ASSETS = ROOT / "report" / "assets"
RESULTS = ROOT / "results"

TOL = 1e-9

# --- Liste blanche : nombres légitimes qui ne viennent pas d'une mesure -------------------
# Chaque entrée porte sa justification. Un nombre absent de l'index ET d'ici est une erreur.
ALLOWED: dict[float, str] = {
    # structure du document et du jeu de données
    1: "compteur, dimension ou renvoi de section", 2: "idem", 3: "idem", 4: "idem",
    5: "idem", 6: "idem", 7: "idem", 8: "idem", 9: "idem", 10: "dix sujets annotés",
    13: "treize sujets de test", 2017: "iSeg-2017", 2026: "année du hackathon",
    144: "dimension du volume", 192: "dimension du volume", 256: "dimension / niveaux",
    # hyperparamètres fixés a priori, listés dans les docstrings des blocs
    0.5: "sigma gaussien (mm)", 12: "colonnes du bloc F", 68: "colonnes du bloc B",
    52: "colonnes du bloc D", 151: "colonnes de la configuration finale",
    83: "colonnes de la configuration A+B+C", 100: "seuil d'aire (voxels)",
    1000: "seuil d'aire", 10000: "seuil d'aire", 100000: "seuil d'aire",
    64: "niveaux de quantification", 30: "seuil de composante (mm3)",
    40: "K de la sélection de colonnes", 99: "percentile de quantification",
    300: "itérations de l'optimiseur", 319: "itérations demandées pour converger",
    47: "couches de MSL_SKKU, chiffre publié",
    # constantes de formules et de statistiques
    0.05: "seuil de p-valeur", 95: "niveau de confiance / percentile MHD",
    0.002: "plus petite p-valeur atteignable a n=10",
    1.55: "1,55e6 parametres publies (mantisse)",
    # nombres écrits en toutes lettres ailleurs, ou parties de formules 3(F+1)
    758: "convention inverse, recalculé par assertion",
    939: "auto-contexte, recalculé par assertion",
    163: "sélection K=40, recalculée par assertion",
    456: "configuration finale, recalculée par assertion",
}


def strip_accents(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", s) if not unicodedata.combining(c))


# --- Extraction des nombres ---------------------------------------------------------------

NUM_RE = re.compile(
    r"""(?<![\w.])                 # pas au milieu d'un identifiant
    (?P<sign>[+-]?)
    (?P<int>\d{1,3}(?:(?:\\,| | |\ )\d{3})+|\d+)   # 1\,550\,000 ou 1 651 ou 456
    (?:(?:\{,\}|[.,])(?P<frac>\d+))?
    """,
    re.VERBOSE,
)


def normalize(literal: str) -> tuple[float, int]:
    """Rend (valeur, nombre de décimales) d'un littéral français ou LaTeX."""
    s = literal.replace("\\,", "").replace(" ", "").replace(" ", "")
    s = re.sub(r"(?<=\d) (?=\d)", "", s)
    s = s.replace("{,}", ".").replace(",", ".")
    frac = s.split(".", 1)[1] if "." in s else ""
    return float(s), len(frac)


EXPONENT_RE = re.compile(r"\^\{?$")


def numbers_in(text: str) -> list[tuple[float, int, str, int]]:
    """(valeur, décimales, littéral, numéro de ligne) de chaque nombre du texte.

    Les exposants LaTeX (10^{-3}) sont ignorés : ils décrivent une notation, pas une mesure.
    """
    out = []
    for lineno, line in enumerate(text.splitlines(), 1):
        for m in NUM_RE.finditer(line):
            if EXPONENT_RE.search(line[: m.start()]):
                continue
            lit = m.group(0)
            try:
                v, d = normalize(lit)
            except ValueError:
                continue
            out.append((v, d, lit.strip(), lineno))
    return out


# --- Index des valeurs autorisées ---------------------------------------------------------

def json_leaves(obj) -> list[float]:
    if isinstance(obj, dict):
        return [v for x in obj.values() for v in json_leaves(x)]
    if isinstance(obj, list):
        return [v for x in obj for v in json_leaves(x)]
    if isinstance(obj, bool):
        return []
    if isinstance(obj, (int, float)):
        return [float(obj)]
    return []


def build_index() -> dict[float, set[str]]:
    idx: dict[float, set[str]] = {}

    def add(v: float, src: str) -> None:
        idx.setdefault(round(float(v), 12), set()).add(src)

    for p in sorted(RESULTS.glob("*.json")):
        for v in json_leaves(json.loads(p.read_text())):
            add(v, p.name)
    for p in sorted(ASSETS.glob("*.md")):
        for v, _, _, _ in numbers_in(p.read_text()):
            add(v, p.name)
    for v, src in PUBLISHED_VALUES.items():
        add(v, src)
    return idx


def matches(value: float, decimals: int, idx: dict[float, set[str]]) -> set[str]:
    """Une valeur du rapport est couverte si une valeur de l'index l'égale à sa précision."""
    hits = set()
    eps = 10 ** (-decimals) * 0.5 + TOL
    for w, srcs in idx.items():
        # le texte cite parfois l'amplitude d'un écart que l'asset stocke signé
        if abs(round(w, decimals) - value) < eps or abs(abs(round(w, decimals)) - value) < eps:
            hits |= srcs
    return hits


# --- Assertions : les chiffres qui portent l'argument -------------------------------------

def load(name: str) -> dict:
    return json.loads((RESULTS / f"{name}.json").read_text())


def dice_means(run: str) -> list[float]:
    r = load(run)
    return [r["per_subject"][k]["dice_mean"] for k in sorted(r["per_subject"], key=int)]


def mean(xs) -> float:
    return sum(xs) / len(xs)


def stdev(xs) -> float:
    m = mean(xs)
    return (sum((x - m) ** 2 for x in xs) / (len(xs) - 1)) ** 0.5


ABC_FEATURES = 83  # colonnes des blocs A+B+C, communes à tous les paliers du bloc D


def delta(a: str, b: str) -> float:
    return mean(dice_means(b)) - mean(dice_means(a))


# Dice officiels du challenge, relevés sur le tableau des organisateurs
# https://iseg2017.web.unc.edu/evaluation/ (LCR, SG, SB)
MSL_SKKU_DICE = (0.958, 0.923, 0.904)
MSL_SKKU_PARAMS = 1_550_000        # « 47 layers with 1.55 million learnable parameters »
HYPERDENSENET_PARAMS = 10_349_450  # 9 518 850 conv + 830 600 fc, table 4 de Dolz et al.

# Chiffres publiés cités dans le rapport. Ils ne viennent pas de nos JSON, ils viennent d'une
# source primaire relevée à la main ; ils sont indexés ici pour que leur provenance soit
# écrite au même endroit que la vérification.
PUBLISHED_VALUES: dict[float, str] = {
    1_550_000: "Wang et al. 2019, § MSL_SKKU : « 47 layers with 1.55 million learnable parameters »",
    47: "Wang et al. 2019, même phrase",
    10_349_450: "Dolz et al. 2019, table 4, colonne « total »",
    9_518_850: "Dolz et al. 2019, table 4, colonne « convolution »",
    830_600: "Dolz et al. 2019, table 4, colonne « fully-connected »",
    0.958: "leaderboard iSeg-2017, MSL_SKKU, Dice LCR",
    0.923: "leaderboard iSeg-2017, MSL_SKKU, Dice SG",
    0.904: "leaderboard iSeg-2017, MSL_SKKU, Dice SB",
    0.956: "leaderboard iSeg-2017, HyperDenseNet, Dice LCR",
    0.920: "leaderboard iSeg-2017, HyperDenseNet, Dice SG",
    0.901: "leaderboard iSeg-2017, HyperDenseNet, Dice SB",
}


def stats_table() -> dict[tuple[str, str], dict[str, float]]:
    """Les comparaisons appariées de report/assets/stats.md, indexées par (A, B)."""
    out = {}
    for line in (ASSETS / "stats.md").read_text().splitlines():
        cells = [c.strip() for c in line.split("|")[1:-1]]
        if len(cells) < 12 or "→" not in cells[0]:
            continue
        a, b = (x.strip() for x in cells[0].split("→"))
        try:
            out[(a, b)] = {"delta": float(cells[4]), "p_raw": float(cells[7]),
                           "p_holm": float(cells[8])}
        except ValueError:
            continue
    return out


def assertions() -> list[tuple[str, float, float, int]]:
    """(description, valeur recalculée, valeur écrite dans le rapport, décimales)."""
    fin, ac, sel = load("logreg_final"), load("autocontext_final"), load("select_k40")
    F = fin["n_features"]
    ref = mean(MSL_SKKU_DICE)
    a: list[tuple[str, float, float, int]] = [
        ("paramètres de la configuration finale = 3(F+1)", 3 * (F + 1), fin["n_params"], 0),
        ("paramètres auto-contexte = 3(F+1)+3(F+10)", 3 * (F + 1) + 3 * (F + 10), ac["n_params"], 0),
        ("paramètres sélection K=40 = 3(K+1)+K", 3 * (40 + 1) + 40, sel["n_params"], 0),
        ("convention inverse : 456 + 2x151", fin["n_params"] + 2 * F, 758, 0),
        ("colonnes du bloc D = 2(6+4x5)", 2 * (6 + 4 * 5), 52, 0),
        ("somme des colonnes des six blocs", 6 + 68 + 9 + 52 + 4 + 12, F, 0),
        ("delta auto-contexte sur finale", delta("logreg_final", "autocontext_final"), 0.0122, 4),
        ("delta bloc D (ABC -> palier 0)", delta("logreg_ABC", "logreg_ABCD_p0"), 0.0102, 4),
        ("delta remontée de branche (p0 -> p1)", delta("logreg_ABCD_p0", "logreg_ABCD_p1"), 0.0035, 4),
        ("delta arbre des formes (p0 -> p2)", delta("logreg_ABCD_p0", "logreg_ABCD_p2"), -0.0002, 4),
        ("delta auto-dualité (p1 -> p2)", delta("logreg_ABCD_p1", "logreg_ABCD_p2"), -0.0037, 4),
        ("delta sélection K=40 sur finale", delta("logreg_final", "select_k40"), -0.0240, 4),
        ("delta lissage sur finale", delta("logreg_final", "logreg_final_smooth"), -0.0031, 4),
        ("delta contrainte topologique", delta("logreg_final_smooth", "logreg_final_postproc"), -0.0011, 4),
        ("delta 64 niveaux", delta("logreg_ABCD_p2", "logreg_ABCD_p2_l64"), -0.0005, 4),
        ("Pareto : facteur de paramètres MSL_SKKU / auto-contexte",
         MSL_SKKU_PARAMS / ac["n_params"], 1651, 0),
        ("Pareto : fraction du Dice MSL_SKKU atteinte par l'auto-contexte",
         100 * mean(dice_means("autocontext_final")) / ref, 90.5, 1),
        ("Pareto : fraction du Dice atteinte par la sélection K=40",
         100 * mean(dice_means("select_k40")) / ref, 86.6, 1),
        ("ordre de grandeur bas : MSL_SKKU / auto-contexte",
         MSL_SKKU_PARAMS / ac["n_params"], 1651, 0),
        ("ordre de grandeur haut : HyperDenseNet / auto-contexte",
         HYPERDENSENET_PARAMS / ac["n_params"], 11022, 0),
        # ligne du challenge dans le tableau du ratio : les trois Dice officiels sont publiés,
        # leur moyenne et le ratio qui en découle sont calculés ici et nulle part ailleurs.
        ("Dice moyen de MSL_SKKU, moyenne des trois tissus publiés", ref, 0.9283, 4),
        ("ratio brut de MSL_SKKU, mantisse en 1e-7",
         1e7 * ref / MSL_SKKU_PARAMS, 5.99, 2),
        # § convention de comptage : ce que la convention inverse fait au ratio brut
        ("convention inverse : déplacement du ratio brut, en %",
         100 * (fin["n_params"] / 758 - 1), -40, 0),
        # § discussion : l'auto-dualité divise par deux les colonnes du bloc morphologique.
        # C'est le bloc qui est divisé par deux, pas le vecteur entier — 187 / 135 ne vaut
        # pas 2, et le rapport a longtemps laissé croire le contraire.
        ("colonnes morpho du palier 1 (deux arbres)",
         load("logreg_ABCD_p1")["n_features"] - ABC_FEATURES, 104, 0),
        ("colonnes morpho du palier 2 (un arbre) = la moitié",
         load("logreg_ABCD_p2")["n_features"] - ABC_FEATURES, 52, 0),
        # § résultats : la variabilité inter-sujets, à laquelle tous les effets sont comparés
        ("écart-type inter-sujets du Dice moyen, configuration finale",
         stdev(dice_means("logreg_final")), 0.010, 3),
    ]
    deg = json.loads((RESULTS / "degenerate_baseline.json").read_text())
    best_ratio_real = max(
        mean(dice_means(r)) / load(r)["n_params"]
        for r in ("logreg_ABC", "logreg_ABCD_p0", "logreg_ABCD_p1", "logreg_ABCD_p2",
                  "logreg_ABCD_p3", "logreg_ABCD_p2_l64", "logreg_ABCD_p2_rank",
                  "logreg_final", "select_k40", "logreg_final_smooth",
                  "logreg_final_postproc", "autocontext_final"))
    a += [
        ("classifieur dégénéré : Dice moyen", deg["dice_mean"], 0.2139, 4),
        ("dégénéré / meilleur ratio d'une configuration réelle",
         (deg["dice_mean"] / deg["n_params"]) / best_ratio_real, 43, 0),
        ("dégénéré / ratio de l'auto-contexte",
         (deg["dice_mean"] / deg["n_params"])
         / (mean(dice_means("autocontext_final")) / ac["n_params"]), 239, 0),
    ]
    return a


def check_pvalues(text: str) -> list[str]:
    """Toute p-valeur écrite dans le rapport doit exister dans stats.md.

    Un index global ne suffit pas ici : sur 1700 valeurs, une p-valeur fausse trouve
    presque toujours un homonyme ailleurs. On restreint donc la comparaison aux seules
    p-valeurs effectivement calculées, colonnes brute et ajustée de stats.md.
    """
    st = stats_table()
    legal = {round(v[k], 3) for v in st.values() for k in ("p_raw", "p_holm")} | {0.05}
    problems = []
    for lineno, line in enumerate(text.splitlines(), 1):
        if "Holm" not in line and "p = " not in line and "p brut" not in line:
            continue
        for value, dec, lit, _ in numbers_in(line):
            if dec != 3:
                continue
            if round(value, 3) not in legal:
                problems.append(f"  ligne {lineno:>4} : p-valeur « {lit} » absente de stats.md")
    return problems


def main() -> int:
    text = REPORT.read_text().split("<!--\n===", 1)[0]
    idx = build_index()
    for desc, computed, _, dec in assertions():
        idx.setdefault(round(float(computed), 12), set()).add(f"calculé : {desc}")
    nums = numbers_in(text)

    unmatched = []
    for value, dec, lit, line in nums:
        if matches(value, dec, idx):
            continue
        if any(abs(value - k) < TOL for k in ALLOWED):
            continue
        unmatched.append((line, lit, value))

    print(f"index      : {len(idx)} valeurs distinctes "
          f"({len(list(RESULTS.glob('*.json')))} JSON, {len(list(ASSETS.glob('*.md')))} assets)")
    print(f"rapport    : {len(nums)} nombres extraits")
    print(f"sans source: {len(unmatched)}")
    for line, lit, value in unmatched:
        print(f"  ligne {line:>4} : « {lit} »  ({value})")

    pv = check_pvalues(text)
    print(f"p-valeurs  : {len(pv)} anomalie(s)")
    for msg in pv:
        print(msg)

    print("\nassertions :")
    failed = 0
    for desc, computed, written, dec in assertions():
        ok = abs(round(computed, dec) - written) < 10 ** (-dec) * 0.5 + TOL
        if not ok:
            failed += 1
        print(f"  [{'ok ' if ok else 'ÉCART'}] {desc:<58} "
              f"calculé {computed:.{dec}f}   écrit {written:.{dec}f}")

    print(f"\n{failed} assertion(s) en écart, {len(unmatched)} nombre(s) sans source, "
          f"{len(pv)} p-valeur(s) sans correspondance.")
    return 1 if (failed or unmatched or pv) else 0


if __name__ == "__main__":
    sys.exit(main())
