"""Budget de frugalité : ce que coûte réellement une configuration, au-delà du nombre de poids.

Usage : python scripts/measure_cost.py experiments/<config>.yaml [subject_id]

Mesure sur un sujet, cache vidé pour ce sujet afin de chronométrer le calcul réel :
  - temps d'extraction par bloc et pic de mémoire résidente associé ;
  - temps et pic mémoire de l'inférence sur le volume complet ;
  - temps d'entraînement d'un fold (9 sujets, échantillon de la config) ;
  - taille du modèle sérialisé sur disque.
Le résultat est écrit dans results/cost_<run_name>.json.
"""
import json
import pickle
import resource
import sys
import platform
import time
from pathlib import Path

import numpy as np
import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.cli import build_model_factory, load_config  # noqa: E402
from src.eval.loocv import build_training_set  # noqa: E402
from src.features.normalize import apply_stats, subject_stats  # noqa: E402
from src.features.registry import build_extractor  # noqa: E402
from src.io import load_subject  # noqa: E402


def peak_rss_gb() -> float:
    return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1e6


def main(config_path: str, subject_id: int = 1) -> None:
    cfg = load_config(Path(config_path))
    subject = load_subject(subject_id, ROOT / cfg["data_root"])
    out = {
        "machine": f"{platform.node()} / {platform.machine()} / python {platform.python_version()}","run_name": cfg["run_name"], "subject_id": subject_id, "blocks": {}}

    # 1. extraction, bloc par bloc, cache contourné pour chronométrer le calcul réel
    total_extract = 0.0
    for spec in cfg["features"]:
        block = build_extractor([spec], cache_dir=None, verbose=False).blocks[0]
        before = peak_rss_gb()
        t0 = time.perf_counter()
        X = block.transform(subject)
        dt = time.perf_counter() - t0
        total_extract += dt
        out["blocks"][block.name] = {
            "seconds": round(dt, 2),
            "n_features": int(X.shape[1]),
            "megabytes_float32": round(X.nbytes / 1e6, 1),
            "peak_rss_gb": round(max(peak_rss_gb(), before), 2),
        }
        del X
    out["extract_seconds_per_subject"] = round(total_extract, 2)
    out["extract_peak_rss_gb"] = round(peak_rss_gb(), 2)

    # 2. entraînement d'un fold et inférence sur un volume complet
    ext = build_extractor(cfg["features"], cache_dir=ROOT / cfg["cache_dir"], verbose=False)
    train_ids = [s for s in cfg["subjects"] if s != subject_id]
    subjects = [load_subject(s, ROOT / cfg["data_root"]) for s in train_ids]
    stats = {s.subject_id: subject_stats(ext, s, cache_dir=ROOT / cfg["cache_dir"]) for s in subjects}
    rng = np.random.default_rng(0)
    t0 = time.perf_counter()
    X, y, _ = build_training_set(ext, subjects, cfg["sampling"]["n_per_class"], cfg["sampling"]["boundary_frac"], rng, stats)
    out["training_set_seconds"] = round(time.perf_counter() - t0, 2)
    out["training_set_rows"] = int(X.shape[0])

    model = build_model_factory(cfg["model"], cfg["seed"])()
    t0 = time.perf_counter()
    model.fit(X, y)
    out["fit_seconds"] = round(time.perf_counter() - t0, 2)
    out["n_params"] = int(model.n_params())

    test_stats = subject_stats(ext, subject, cache_dir=ROOT / cfg["cache_dir"])
    Xt = ext.transform(subject)
    t0 = time.perf_counter()
    proba = np.empty((Xt.shape[0], 3), dtype=np.float32)
    for start in range(0, Xt.shape[0], 200_000):
        proba[start : start + 200_000] = model.predict_proba(apply_stats(Xt[start : start + 200_000], test_stats))
    out["inference_seconds_per_volume"] = round(time.perf_counter() - t0, 2)
    out["n_voxels_in_mask"] = int(Xt.shape[0])
    out["peak_rss_gb"] = round(peak_rss_gb(), 2)

    blob = pickle.dumps(model)
    out["model_size_kilobytes"] = round(len(blob) / 1024, 1)
    out["model_weights_kilobytes"] = round(out["n_params"] * 8 / 1024, 2)

    path = ROOT / "results" / f"cost_{cfg['run_name']}.json"
    path.write_text(json.dumps(out, indent=1))
    print(json.dumps(out, indent=1))
    print(f"\nécrit dans {path}")


if __name__ == "__main__":
    main(sys.argv[1], int(sys.argv[2]) if len(sys.argv) > 2 else 1)
