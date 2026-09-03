"""Supprime du cache les blocs dont la clé n'est utilisée par aucune des configs données.

Usage : python scripts/purge_cache.py experiments/a.yaml [experiments/b.yaml ...]
Sans argument, garde les clés de toutes les configs de experiments/.
Le cache du bloc morpho pèse ~200 Mo par sujet et par variante : on ne garde que l'utile.
"""
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.features.registry import build_block  # noqa: E402


def main(configs: list[str]) -> None:
    paths = [Path(c) for c in configs] if configs else sorted((ROOT / "experiments").glob("*.yaml"))
    keep = set()
    for f in paths:
        for spec in (yaml.safe_load(f.read_text()) or {}).get("features", []):
            keep.add(build_block(spec).cache_key)
    removed = freed = 0
    for p in (ROOT / "cache").glob("subject-*/*.npy"):
        if p.stem not in keep:
            freed += p.stat().st_size
            p.unlink()
            p.with_suffix(".json").unlink(missing_ok=True)
            removed += 1
    print(f"cache purgé : {removed} fichiers, {freed / 1e9:.1f} Go libérés, {len(keep)} clés gardées")


if __name__ == "__main__":
    main(sys.argv[1:])
