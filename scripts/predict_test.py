"""Produit la soumission iSeg-2017 : segmentations des 13 sujets de test, prêtes à envoyer.

Le protocole officiel du challenge évalue sur les sujets 11 à 23, dont la vérité terrain n'est
pas publique. Ce script est la seule façon d'obtenir un chiffre comparable au classement : le
leave-one-out du rapport, lui, ne dit rien sur ces sujets-là.

DIFFÉRENCE AVEC LA BOUCLE LOO. Ici le modèle est entraîné sur les DIX sujets annotés à la
fois, pas sur neuf. C'est le régime normal d'un modèle qu'on livre : on n'a plus de raison de
retenir un sujet, puisque l'évaluation se fait ailleurs. Les chiffres du rapport et le score du
serveur ne sont donc pas produits par le même modèle, et le rapport doit le dire.

FORMAT DE SORTIE, imposé par le challenge et vérifié par verify() :
  - un fichier hdr/img par sujet, nommé subject-<id>-label, à plat dans l'archive ;
  - unsigned char 8 bits, valeurs 0 (fond), 10 (LCR), 150 (matière grise), 250 (blanche) ;
  - mêmes dimensions, même résolution et même orientation que les scans T1 et T2 du sujet.
On n'invente donc aucun en-tête : on repart de celui du T1 du sujet et on ne change que le
type de données. C'est ce qui garantit l'orientation, y compris pour le sujet 23, dont le
volume n'a pas la même taille que les autres.

Usage : python scripts/predict_test.py [--config experiments/autocontext_final.yaml]
"""
from __future__ import annotations

import argparse
import json
import platform
import sys
import time
import zipfile
from pathlib import Path

import nibabel as nib
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.cli import load_config  # noqa: E402
from src.eval.loocv import TrainContext, build_training_set, predict_full  # noqa: E402
from src.features.normalize import apply_stats, subject_stats  # noqa: E402
from src.features.registry import build_extractor  # noqa: E402
from src.io import TISSUE_CLASSES, find_subject_file, load_subject, mask_to_volume  # noqa: E402
from src.models.registry import build  # noqa: E402
from src.sampling import adjust_priors, class_priors  # noqa: E402

TRAIN_IDS = list(range(1, 11))
TEST_IDS = list(range(11, 24))
RAW_VALUES = {1: 10, 2: 150, 3: 250}  # nos classes internes -> valeurs attendues par le challenge
ALLOWED = {0, 10, 150, 250}


def write_label(seg: np.ndarray, subject_id: int, data_root: Path, out_dir: Path) -> Path:
    """Écrit subject-<id>-label.hdr/.img avec la géométrie EXACTE du T1 du sujet."""
    t1_path = find_subject_file(subject_id, data_root, "T1")
    ref = nib.load(str(t1_path))
    raw = np.zeros(seg.shape, dtype=np.uint8)
    for cls, value in RAW_VALUES.items():
        raw[seg == cls] = value
    # le challenge fournit ses labels avec la même forme que les scans, dimension finale
    # comprise : on la restitue plutôt que de livrer un volume 3D là où l'original est 4D.
    target = tuple(ref.header.get_data_shape())
    if raw.shape != target:
        raw = raw.reshape(target)
    header = ref.header.copy()
    header.set_data_dtype(np.uint8)
    out = out_dir / f"subject-{subject_id}-label.hdr"
    nib.save(type(ref)(raw, ref.affine, header), str(out))
    return out


def verify(out_dir: Path, data_root: Path, subject_ids: list[int]) -> list[str]:
    """Relit chaque fichier écrit et le confronte au cahier des charges. Rend les anomalies."""
    problems = []
    for sid in subject_ids:
        p = out_dir / f"subject-{sid}-label.hdr"
        if not p.exists() or not (out_dir / f"subject-{sid}-label.img").exists():
            problems.append(f"subject-{sid} : fichier hdr ou img manquant")
            continue
        img = nib.load(str(p))
        arr = np.asarray(img.dataobj)
        ref = nib.load(str(find_subject_file(sid, data_root, "T1")))
        if arr.dtype != np.uint8:
            problems.append(f"subject-{sid} : dtype {arr.dtype}, attendu uint8")
        if int(img.header["bitpix"]) != 8:
            problems.append(f"subject-{sid} : bitpix {int(img.header['bitpix'])}, attendu 8")
        seen = set(np.unique(arr).tolist())
        if not seen <= ALLOWED:
            problems.append(f"subject-{sid} : valeurs interdites {sorted(seen - ALLOWED)}")
        if seen != ALLOWED:
            problems.append(f"subject-{sid} : valeurs absentes {sorted(ALLOWED - seen)}")
        if arr.shape != tuple(ref.header.get_data_shape()):
            problems.append(f"subject-{sid} : forme {arr.shape}, T1 {tuple(ref.header.get_data_shape())}")
        if not np.allclose(img.header.get_zooms()[:3], ref.header.get_zooms()[:3]):
            problems.append(f"subject-{sid} : résolution {img.header.get_zooms()[:3]}")
        if not np.allclose(img.affine, ref.affine):
            problems.append(f"subject-{sid} : orientation différente du T1")
        # le fond doit être exactement le complémentaire du masque cérébral
        t1 = np.squeeze(np.asarray(ref.dataobj))
        if not np.array_equal(np.squeeze(arr) != 0, t1 != 0):
            problems.append(f"subject-{sid} : le fond ne coïncide pas avec T1 == 0")
    return problems


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", type=Path, default=ROOT / "experiments" / "autocontext_final.yaml")
    ap.add_argument("--out", type=Path, default=ROOT / "submission")
    args = ap.parse_args()

    cfg = load_config(args.config)
    data_root = ROOT / cfg["data_root"]
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    np.random.seed(cfg["seed"])

    extractor = build_extractor(cfg["features"], cache_dir=ROOT / cfg["cache_dir"], verbose=False)
    print(f"[soumission] configuration {cfg['run_name']}, {extractor.n_features} colonnes")

    # --- entraînement sur les DIX sujets annotés -------------------------------------------
    t0 = time.time()
    train = [load_subject(sid, data_root) for sid in TRAIN_IDS]
    for s in train:
        extractor.transform(s)
    stats = {s.subject_id: subject_stats(extractor, s, cache_dir=ROOT / cfg["cache_dir"]) for s in train}
    rng = np.random.default_rng(cfg["seed"])
    X, y, blocks = build_training_set(
        extractor, train, cfg["sampling"]["n_per_class"], cfg["sampling"]["boundary_frac"], rng, stats
    )
    print(f"[soumission] {X.shape[0]} lignes d'entraînement en {time.time() - t0:.0f}s")

    t0 = time.time()
    model = build(cfg["model"]["name"], cfg["model"].get("config", {}), cfg["seed"])
    if getattr(model, "needs_context", False):
        model.fit(X, y, context=TrainContext(train, blocks, extractor, stats))
    else:
        model.fit(X, y)
    fit_seconds = time.time() - t0
    sampled_prior = np.array([np.mean(y == c) for c in TISSUE_CLASSES])
    target_prior = class_priors(train)
    print(f"[soumission] modèle ajusté en {fit_seconds:.0f}s, {model.n_params()} paramètres")

    # --- prédiction des 13 sujets de test ---------------------------------------------------
    per_subject_seconds = {}
    for sid in TEST_IDS:
        t0 = time.time()
        s = load_subject(sid, data_root)
        if s.label is not None:
            raise RuntimeError(f"subject-{sid} a un label : ce n'est pas un sujet de test")
        Xs = apply_stats(extractor.transform(s), subject_stats(extractor, s, cache_dir=ROOT / cfg["cache_dir"]))
        if getattr(model, "needs_context", False):
            proba = model.predict_proba_subject(Xs, s)
        else:
            proba = predict_full(model, Xs)
        if cfg["sampling"]["prior_correction"]:
            proba = adjust_priors(proba, sampled_prior, target_prior)
        seg = mask_to_volume((np.argmax(proba, axis=1) + 1).astype(np.uint8), s.mask)
        seg[~s.mask] = 0
        write_label(seg, sid, data_root, out_dir)
        per_subject_seconds[sid] = round(time.time() - t0, 1)
        frac = {n: float(np.mean(seg[s.mask] == c)) for c, n in ((1, "lcr"), (2, "sg"), (3, "sb"))}
        print(f"[soumission] subject-{sid} en {per_subject_seconds[sid]}s "
              f"(lcr {frac['lcr']:.2f} / sg {frac['sg']:.2f} / sb {frac['sb']:.2f})")

    # --- vérification puis archive ----------------------------------------------------------
    problems = verify(out_dir, data_root, TEST_IDS)
    if problems:
        print("\n!!! NON CONFORME, archive non produite :")
        for p in problems:
            print("   -", p)
        raise SystemExit(1)
    print("[soumission] les 13 fichiers passent toutes les vérifications de format")

    zip_path = out_dir / f"iseg2017_{cfg['run_name']}.zip"
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as z:
        for sid in TEST_IDS:
            for ext in (".hdr", ".img"):
                f = out_dir / f"subject-{sid}-label{ext}"
                z.write(f, arcname=f.name)  # arcname sans dossier : le challenge exige la racine
    meta = {
        "run_name": cfg["run_name"],
        "config_file": str(args.config),
        "trained_on": TRAIN_IDS,
        "predicted": TEST_IDS,
        "n_params": int(model.n_params()),
        "n_params_breakdown": {k: int(v) for k, v in model.param_breakdown().items()},
        "n_features": extractor.n_features,
        "fit_seconds": round(fit_seconds, 1),
        "seconds_per_test_subject": per_subject_seconds,
        "mean_seconds_per_test_subject": round(float(np.mean(list(per_subject_seconds.values()))), 1),
        "machine": f"{platform.node()} / {platform.machine()} / python {platform.python_version()}",
    }
    (ROOT / "results" / "submission.json").write_text(json.dumps(meta, indent=1))
    print(f"[soumission] {zip_path} ({zip_path.stat().st_size / 1e6:.1f} Mo)")
    print(f"[soumission] métadonnées dans results/submission.json")


if __name__ == "__main__":
    main()
