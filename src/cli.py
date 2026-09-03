"""CLI : `python -m src.cli run experiments/foo.yaml` reproduit n'importe quel résultat.

Sous-commandes :
  run <yaml>        boucle LOO complète -> results/<run_name>.json
  features <yaml>   pré-calcule le cache de features des sujets listés (sans entraîner)
  blocks            liste les blocs de features disponibles et leurs colonnes
"""
from __future__ import annotations

import argparse
import importlib
import sys
from pathlib import Path

import numpy as np
import yaml

ROOT = Path(__file__).resolve().parents[1]
DEFAULTS = {
    "seed": 0,
    "subjects": list(range(1, 11)),
    "data_root": "data",
    "cache_dir": "cache",
    "results_dir": "results",
    "features": [{"name": "intensity"}],
    "model": {"name": "random", "config": {}},
    "sampling": {"n_per_class": 20000, "boundary_frac": 0.0, "prior_correction": False},
    "postproc": [],
    "save_proba": True,
    "with_distances": True,
}


def load_config(path: Path) -> dict:
    cfg = dict(DEFAULTS)
    user = yaml.safe_load(Path(path).read_text()) or {}
    for k, v in user.items():
        if isinstance(v, dict) and isinstance(cfg.get(k), dict):
            cfg[k] = {**cfg[k], **v}
        else:
            cfg[k] = v
    cfg.setdefault("run_name", Path(path).stem)
    return cfg


def build_model_factory(model_cfg: dict, seed: int):
    """Résout le modèle par nom.

    Ordre : src.models.registry.build(name, config, seed) s'il existe (côté Arthur), sinon
    les stubs de src/models/stub.py (random, logreg). Signalé à Arthur : c'est la signature
    que la CLI attend de son registre.
    """
    name, config = model_cfg["name"], dict(model_cfg.get("config", {}))
    try:
        registry = importlib.import_module("src.models.registry")
        return lambda: registry.build(name, config, seed)
    except (ImportError, AttributeError):
        pass
    from src.models.stub import build_stub

    build_stub(name, config, seed)  # échoue tôt si le nom est inconnu
    return lambda: build_stub(name, config, seed)


def build_postproc(steps: list[str]):
    """Résout src.postproc.topology.apply_postproc(proba_vol, mask, spacing, steps) (côté Arthur)."""
    if not steps:
        return None
    topo = importlib.import_module("src.postproc.topology")
    return lambda proba_vol, mask, spacing: topo.apply_postproc(proba_vol, mask, spacing, steps)


def cmd_run(args: argparse.Namespace) -> None:
    from src.eval.loocv import run_loocv
    from src.features.registry import build_extractor

    cfg = load_config(args.config)
    np.random.seed(cfg["seed"])
    extractor = build_extractor(cfg["features"], cache_dir=ROOT / cfg["cache_dir"])
    run_loocv(
        extractor=extractor,
        model_factory=build_model_factory(cfg["model"], cfg["seed"]),
        run_name=cfg["run_name"],
        data_root=ROOT / cfg["data_root"],
        results_dir=ROOT / cfg["results_dir"],
        subject_ids=cfg["subjects"],
        seed=cfg["seed"],
        n_per_class=cfg["sampling"]["n_per_class"],
        boundary_frac=cfg["sampling"]["boundary_frac"],
        prior_correction=cfg["sampling"]["prior_correction"],
        postproc=build_postproc(cfg["postproc"]),
        postproc_names=cfg["postproc"],
        save_proba=cfg["save_proba"],
        with_distances=cfg["with_distances"],
        model_name=cfg["model"]["name"],
        model_config=cfg["model"].get("config", {}),
        extra={"config_file": str(args.config)},
    )


def cmd_features(args: argparse.Namespace) -> None:
    from src.features.registry import build_extractor
    from src.io import load_subject

    cfg = load_config(args.config)
    extractor = build_extractor(cfg["features"], cache_dir=ROOT / cfg["cache_dir"])
    for sid in cfg["subjects"]:
        s = load_subject(sid, ROOT / cfg["data_root"])
        X = extractor.transform(s)
        print(f"subject-{sid}: {X.shape}")


def cmd_blocks(args: argparse.Namespace) -> None:
    from src.features.registry import BLOCKS, _load_blocks

    _load_blocks()
    for name, cls in sorted(BLOCKS.items()):
        b = cls()
        print(f"{name} ({b.n_features} features, config={b.config}):")
        print("   " + ", ".join(b.names))


def main(argv=None) -> None:
    p = argparse.ArgumentParser(prog="python -m src.cli")
    sub = p.add_subparsers(dest="cmd", required=True)
    for name, fn in (("run", cmd_run), ("features", cmd_features)):
        sp = sub.add_parser(name)
        sp.add_argument("config", type=Path)
        sp.set_defaults(fn=fn)
    sub.add_parser("blocks").set_defaults(fn=cmd_blocks)
    args = p.parse_args(argv)
    args.fn(args)


if __name__ == "__main__":
    main()
