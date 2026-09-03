"""BLOC F — statistiques de voisinage bon marché. 0 paramètre appris.

Moyenne et écart-type locaux des RANGS percentiles (T1, T2) dans une boîte de rayon r,
normalisés par le masque (uniform(I·m) / uniform(m)) pour ne pas être biaisés au bord.
C'est un contexte spatial minimal, complémentaire de l'auto-contexte (qui lisse des
probabilités apprises) : ici on lisse les données, donc c'est gratuit.
"""
from __future__ import annotations

import numpy as np
from scipy import ndimage

from src.features.base import FeatureExtractor
from src.features.gaussian import mask_bbox
from src.features.intensity import percentile_rank
from src.io import Subject


class ContextFeatures(FeatureExtractor):
    name = "context"

    def __init__(self, radii=(1, 2, 4), modalities=("t1", "t2")):
        self.radii = tuple(int(r) for r in radii)
        self.modalities = tuple(modalities)

    @property
    def config(self) -> dict:
        return {"radii_vox": list(self.radii), "modalities": list(self.modalities), "input": "percentile_rank"}

    @property
    def names(self) -> list[str]:
        return [f"{m}_r{r}_{k}" for m in self.modalities for r in self.radii for k in ("mean", "std")]

    def transform(self, subject: Subject) -> np.ndarray:
        crop = mask_bbox(subject.mask, max(self.radii))
        m = subject.mask[crop]
        mf = m.astype(np.float32)
        cols = []
        for mod in self.modalities:
            img = np.zeros(m.shape, dtype=np.float32)
            img[m] = percentile_rank(getattr(subject, mod)[subject.mask])
            for r in self.radii:
                size = 2 * r + 1
                w = np.maximum(ndimage.uniform_filter(mf, size, mode="constant"), 1e-6)
                mean = ndimage.uniform_filter(img, size, mode="constant") / w
                sq = ndimage.uniform_filter(img * img, size, mode="constant") / w
                std = np.sqrt(np.maximum(sq - mean * mean, 0.0))
                cols += [mean[m], std[m]]
        return self._check(subject, np.stack(cols, axis=1).astype(np.float32))


BLOCKS = (ContextFeatures,)
