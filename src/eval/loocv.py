"""Boucle leave-one-out sur les 10 sujets labellisés.

Pour chaque fold k :
  1. features des 9 autres sujets lues depuis le cache, sous-échantillonnées (sampling.py) ;
  2. fit du classifieur ;
  3. predict_proba sur TOUS les voxels du masque du sujet k (par blocs pour la mémoire) ;
  4. correction des priors (optionnelle), post-traitement (optionnel, côté Arthur), argmax ;
  5. métriques Dice / ASD / MHD par classe ;
  6. sauvegarde des probabilités en .npz compressé (results/proba/<run>/subject-k.npz).
Le JSON de résultats est réécrit après chaque fold : une interruption (Ctrl-C) laisse un
JSON partiel valide avec le champ "completed_folds".
"""
from __future__ import annotations

import json
import time
from datetime import datetime
from pathlib import Path
from typing import Callable

import numpy as np

from src.eval.metrics import evaluate_subject
from src.features.registry import ComposedExtractor
from src.io import TISSUE_CLASSES, Subject, load_subject, mask_to_volume
from src.sampling import adjust_priors, class_priors, sample_voxels

PostprocFn = Callable[[np.ndarray, np.ndarray, tuple], np.ndarray]
"""postproc(proba_volume (D,H,W,3) float32, mask (D,H,W) bool, spacing) -> label volume uint8 (0..3)."""


def predict_full(model, X: np.ndarray, chunk: int = 200_000) -> np.ndarray:
    """predict_proba par blocs de lignes (X peut être un memmap)."""
    out = np.empty((X.shape[0], 3), dtype=np.float32)
    for start in range(0, X.shape[0], chunk):
        out[start : start + chunk] = model.predict_proba(np.asarray(X[start : start + chunk], dtype=np.float32))
    return out


def build_training_set(
    extractor: ComposedExtractor,
    subjects: list[Subject],
    n_per_class: int,
    boundary_frac: float,
    rng: np.random.Generator,
) -> tuple[np.ndarray, np.ndarray]:
    Xs, ys = [], []
    for s in subjects:
        idx, y = sample_voxels(s, n_per_class, rng, boundary_frac=boundary_frac)
        order = np.argsort(idx)
        Xs.append(extractor.transform_rows(s, idx[order]))
        ys.append(y[order])
    return np.concatenate(Xs), np.concatenate(ys)


def _summary(per_subject: dict[str, dict[str, float]]) -> tuple[dict, dict]:
    keys = sorted({k for m in per_subject.values() for k in m})
    mean = {k: float(np.mean([m[k] for m in per_subject.values()])) for k in keys}
    std = {k: float(np.std([m[k] for m in per_subject.values()])) for k in keys}
    return mean, std


def run_loocv(
    extractor: ComposedExtractor,
    model_factory: Callable[[], object],
    run_name: str,
    data_root: Path,
    results_dir: Path,
    subject_ids: list[int] = tuple(range(1, 11)),
    seed: int = 0,
    n_per_class: int = 20_000,
    boundary_frac: float = 0.0,
    prior_correction: bool = False,
    postproc: PostprocFn | None = None,
    postproc_names: list[str] | None = None,
    save_proba: bool = True,
    with_distances: bool = True,
    model_name: str = "?",
    model_config: dict | None = None,
    extra: dict | None = None,
) -> dict:
    results_dir = Path(results_dir)
    results_dir.mkdir(parents=True, exist_ok=True)
    proba_dir = results_dir / "proba" / run_name
    subject_ids = list(subject_ids)
    print(f"[{run_name}] chargement de {len(subject_ids)} sujets...")
    subjects = {sid: load_subject(sid, data_root) for sid in subject_ids}
    # Pré-calcul / vérification du cache une fois par sujet (hors chrono des folds).
    t0 = time.time()
    for s in subjects.values():
        extractor.transform(s)
    print(f"[{run_name}] features prêtes ({extractor.n_features} colonnes) en {time.time() - t0:.1f}s")

    result: dict = {
        "run_name": run_name,
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "seed": seed,
        "feature_blocks": extractor.block_names,
        "feature_config": extractor.config,
        "feature_names": extractor.names,
        "n_features": extractor.n_features,
        "n_feature_learned_params": extractor.n_learned_params,
        "model": model_name,
        "model_config": model_config or {},
        "n_params": None,
        "n_params_breakdown": {},
        "sampling": {"n_per_class": n_per_class, "boundary_frac": boundary_frac, "prior_correction": prior_correction},
        "postproc": postproc_names or [],
        "per_subject": {},
        "completed_folds": [],
        "fold_seconds": {},
        "mean": {},
        "std": {},
        "train_seconds": 0.0,
        "inference_seconds_per_subject": 0.0,
    }
    if extra:
        result.update(extra)
    out_path = results_dir / f"{run_name}.json"

    train_times, infer_times = [], []
    try:
        for k, test_id in enumerate(subject_ids):
            t_fold = time.time()
            rng = np.random.default_rng(seed * 1000 + test_id)
            train_subjects = [subjects[s] for s in subject_ids if s != test_id]
            X, y = build_training_set(extractor, train_subjects, n_per_class, boundary_frac, rng)
            t1 = time.time()
            model = model_factory()
            model.fit(X, y)
            train_times.append(time.time() - t1)

            test = subjects[test_id]
            t2 = time.time()
            proba = predict_full(model, extractor.transform(test))
            if prior_correction:
                sampled = np.array([np.mean(y == c) for c in TISSUE_CLASSES])
                proba = adjust_priors(proba, sampled, class_priors(train_subjects))
            if postproc is not None:
                proba_vol = mask_to_volume(proba, test.mask)
                seg = postproc(proba_vol, test.mask, test.spacing).astype(np.uint8)
            else:
                seg = mask_to_volume((np.argmax(proba, axis=1) + 1).astype(np.uint8), test.mask)
            seg[~test.mask] = 0
            infer_times.append(time.time() - t2)

            metrics = evaluate_subject(seg, test.label, test.spacing, with_distances=with_distances)
            result["per_subject"][str(test_id)] = metrics
            result["completed_folds"].append(test_id)
            result["fold_seconds"][str(test_id)] = round(time.time() - t_fold, 1)
            if k == 0:
                result["n_params"] = int(model.n_params())
                result["n_params_breakdown"] = {k_: int(v) for k_, v in model.param_breakdown().items()}
            if save_proba:
                proba_dir.mkdir(parents=True, exist_ok=True)
                np.savez_compressed(proba_dir / f"subject-{test_id}.npz", proba=proba.astype(np.float16), mask=test.mask)
            result["mean"], result["std"] = _summary(result["per_subject"])
            result["train_seconds"] = float(np.mean(train_times))
            result["inference_seconds_per_subject"] = float(np.mean(infer_times))
            out_path.write_text(json.dumps(result, indent=1))
            print(
                f"[{run_name}] fold {k + 1}/{len(subject_ids)} test=subject-{test_id} "
                f"dice csf/gm/wm = {metrics['dice_csf']:.3f}/{metrics['dice_gm']:.3f}/{metrics['dice_wm']:.3f} "
                f"(train {train_times[-1]:.1f}s, infer {infer_times[-1]:.1f}s, fold {time.time() - t_fold:.1f}s)"
            )
    except KeyboardInterrupt:
        result["interrupted"] = True
        out_path.write_text(json.dumps(result, indent=1))
        print(f"[{run_name}] interrompu après {len(result['completed_folds'])} folds, JSON partiel écrit")
        raise
    m, s = result["mean"], result["std"]
    print(
        f"[{run_name}] LOO terminé : dice_mean {m['dice_mean']:.4f} "
        f"(csf {m['dice_csf']:.3f}±{s['dice_csf']:.3f}, gm {m['dice_gm']:.3f}±{s['dice_gm']:.3f}, "
        f"wm {m['dice_wm']:.3f}±{s['dice_wm']:.3f}) | n_params={result['n_params']} n_features={result['n_features']}"
    )
    return result
