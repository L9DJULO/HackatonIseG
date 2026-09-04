"""Diagnostic de redondance d'un jeu de features, sur un ou plusieurs sujets.

Usage : python scripts/feature_redundancy.py experiments/<config>.yaml [subject_ids...]

Sorties : colonnes constantes, paires de corrélation absolue >= 0.98, et le nombre de features
qui subsisteraient après suppression gloutonne d'une colonne par paire trop corrélée.
Aucun label n'est utilisé : c'est un diagnostic de structure, pas une sélection supervisée.
"""
import sys
from pathlib import Path

import numpy as np
import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.features.registry import build_extractor  # noqa: E402
from src.io import load_subject  # noqa: E402

THRESHOLD = 0.98


def drop_redundant(corr: np.ndarray, names: list[str], threshold: float = THRESHOLD) -> list[int]:
    """Indices gardés : on parcourt les colonnes dans l'ordre et on écarte celles trop corrélées
    à une colonne déjà gardée."""
    kept: list[int] = []
    for j in range(len(names)):
        if all(abs(corr[j, k]) < threshold for k in kept):
            kept.append(j)
    return kept


def main(config: str, subject_ids: list[int]) -> None:
    cfg = yaml.safe_load(Path(config).read_text())
    ext = build_extractor(cfg["features"], cache_dir=ROOT / "cache", verbose=False)
    names = ext.names
    mats = []
    for sid in subject_ids:
        s = load_subject(sid, ROOT / "data")
        X = np.asarray(ext.transform(s), dtype=np.float64)
        step = max(X.shape[0] // 60_000, 1)
        mats.append(X[::step])
    X = np.concatenate(mats)
    print(f"{config} : {X.shape[0]} voxels échantillonnés, {X.shape[1]} features, sujets {subject_ids}")

    std = X.std(axis=0)
    constant = [names[i] for i in np.flatnonzero(std < 1e-9)]
    print(f"\ncolonnes constantes : {len(constant)}")
    for n in constant:
        print(f"  {n}")

    ok = np.flatnonzero(std >= 1e-9)
    corr = np.corrcoef(X[:, ok], rowvar=False)
    sub_names = [names[i] for i in ok]
    pairs = [
        (abs(corr[i, j]), sub_names[i], sub_names[j])
        for i in range(len(ok))
        for j in range(i + 1, len(ok))
        if abs(corr[i, j]) >= THRESHOLD
    ]
    pairs.sort(reverse=True)
    print(f"\npaires de |corrélation| >= {THRESHOLD} : {len(pairs)}")
    for c, a, b in pairs[:40]:
        print(f"  {c:.4f}  {a}  ~  {b}")
    if len(pairs) > 40:
        print(f"  ... et {len(pairs) - 40} autres")

    kept = drop_redundant(corr, sub_names)
    print(f"\nfeatures restantes après suppression gloutonne : {len(kept)} sur {len(names)}")
    dropped = sorted(set(sub_names) - {sub_names[i] for i in kept}) + constant
    print("supprimées :", ", ".join(dropped) if dropped else "aucune")


if __name__ == "__main__":
    ids = [int(a) for a in sys.argv[2:]] or [1, 5]
    main(sys.argv[1], ids)
