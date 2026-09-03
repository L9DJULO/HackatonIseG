"""Composition des blocs de features par leur nom (depuis le YAML)."""
from __future__ import annotations

from pathlib import Path

import numpy as np

from src.features.base import FeatureExtractor
from src.features.cache import CachedExtractor
from src.io import Subject

BLOCKS: dict[str, type[FeatureExtractor]] = {}


def register(cls: type[FeatureExtractor]) -> type[FeatureExtractor]:
    BLOCKS[cls.name] = cls
    return cls


def _load_blocks() -> None:
    # imports tardifs pour que chaque bloc reste importable isolément
    from src.features import context, gaussian, intensity, morpho, spatial, symmetry  # noqa: F401

    for mod in (intensity, gaussian, spatial, morpho, symmetry, context):
        for cls in getattr(mod, "BLOCKS", ()):
            register(cls)


class ComposedExtractor(FeatureExtractor):
    """Concatène plusieurs blocs, colonne par colonne, dans l'ordre donné."""

    name = "composed"

    def __init__(self, blocks: list[FeatureExtractor]):
        self.blocks = blocks

    @property
    def names(self) -> list[str]:
        return [f"{b.name}/{n}" for b in self.blocks for n in b.names]

    @property
    def block_names(self) -> list[str]:
        return [b.name for b in self.blocks]

    @property
    def config(self) -> dict:
        return {b.name: b.config for b in self.blocks}

    @property
    def n_learned_params(self) -> int:
        return sum(b.n_learned_params for b in self.blocks)

    def transform(self, subject: Subject) -> np.ndarray:
        parts = [np.asarray(b.transform(subject), dtype=np.float32) for b in self.blocks]
        return np.concatenate(parts, axis=1) if len(parts) > 1 else parts[0]

    def transform_rows(self, subject: Subject, rows: np.ndarray) -> np.ndarray:
        """Comme transform mais ne matérialise que les lignes demandées (lecture memmap)."""
        rows = np.sort(rows)
        parts = [np.asarray(b.transform(subject)[rows], dtype=np.float32) for b in self.blocks]
        return np.concatenate(parts, axis=1) if len(parts) > 1 else parts[0]


def build_block(spec: dict | str) -> FeatureExtractor:
    if not BLOCKS:
        _load_blocks()
    if isinstance(spec, str):
        spec = {"name": spec}
    spec = dict(spec)
    name = spec.pop("name")
    if name not in BLOCKS:
        raise KeyError(f"bloc inconnu {name!r}, disponibles : {sorted(BLOCKS)}")
    return BLOCKS[name](**spec)


def build_extractor(specs: list[dict | str], cache_dir: Path | None = None, verbose: bool = True) -> ComposedExtractor:
    blocks = [build_block(s) for s in specs]
    if cache_dir is not None:
        blocks = [CachedExtractor(b, cache_dir, verbose=verbose) for b in blocks]
    return ComposedExtractor(blocks)
