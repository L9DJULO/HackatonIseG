"""Chargement des volumes iSeg-2017 (Analyze 7.5, paires .hdr/.img).

Faits VÉRIFIÉS sur les données (scripts/inspect_data.py) :
- shape brute (144, 192, 256, 1) -> on squeeze la dimension finale ;
- T1/T2 en int16 dans [0, 1000], label en uint8 avec valeurs {0, 10, 150, 250} ;
- spacing 1 x 1 x 1 mm sur tous les sujets ;
- (T1 != 0) == (label != 0) voxel à voxel sur les 10 sujets d'entraînement (100 %).
  Le masque cérébral est donc défini comme T1 != 0. Le T2 a parfois 1 voxel nul de
  moins à l'intérieur du masque, il n'est pas utilisé pour le masque.
- le sujet de test 23 a une shape (160, 192, 256).
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import nibabel as nib
import numpy as np

LABEL_VALUES = {0: 0, 10: 1, 150: 2, 250: 3}
CLASS_NAMES = {1: "csf", 2: "gm", 3: "wm"}
TISSUE_CLASSES = (1, 2, 3)


@dataclass
class Subject:
    t1: np.ndarray  # float32 (D, H, W)
    t2: np.ndarray  # float32 (D, H, W)
    label: np.ndarray | None  # uint8 (D, H, W), 0..3 ; None pour les sujets de test
    mask: np.ndarray  # bool (D, H, W)
    subject_id: int
    spacing: tuple[float, float, float]

    @property
    def shape(self) -> tuple[int, int, int]:
        return tuple(self.mask.shape)  # type: ignore[return-value]

    @property
    def mask_indices(self) -> np.ndarray:
        """Indices plats des voxels du masque, ordre canonique de tout le pipeline."""
        return np.flatnonzero(self.mask)

    @property
    def mask_labels(self) -> np.ndarray:
        """Labels (1..3) des voxels du masque, dans l'ordre de mask_indices."""
        if self.label is None:
            raise ValueError(f"subject-{self.subject_id} n'a pas de label")
        return self.label.reshape(-1)[self.mask_indices]


def find_subject_file(subject_id: int, root: Path, modality: str) -> Path:
    """Cherche subject-<id>-<modality>.hdr dans root, root/train, root/test, puis récursivement."""
    name = f"subject-{subject_id}-{modality}.hdr"
    for cand in (root / name, root / "train" / name, root / "test" / name):
        if cand.exists():
            return cand
    for cand in root.rglob(name):
        if "__MACOSX" not in cand.parts:
            return cand
    raise FileNotFoundError(f"{name} introuvable sous {root}")


def _read_analyze(path: Path) -> tuple[np.ndarray, tuple[float, float, float]]:
    img = nib.load(str(path))
    arr = np.asarray(img.dataobj)
    arr = np.squeeze(arr, axis=tuple(range(3, arr.ndim))) if arr.ndim > 3 else arr
    zooms = tuple(float(z) for z in img.header.get_zooms()[:3])
    return arr, zooms  # type: ignore[return-value]


def remap_labels(raw: np.ndarray) -> np.ndarray:
    """{0,10,150,250} -> {0,1,2,3}. Lève une erreur sur toute valeur inattendue."""
    out = np.zeros(raw.shape, dtype=np.uint8)
    seen = np.unique(raw)
    unknown = set(seen.tolist()) - set(LABEL_VALUES)
    if unknown:
        raise ValueError(f"valeurs de label inattendues : {sorted(unknown)}")
    for src, dst in LABEL_VALUES.items():
        if dst:
            out[raw == src] = dst
    return out


def load_subject(subject_id: int, root: Path) -> Subject:
    root = Path(root)
    t1, spacing = _read_analyze(find_subject_file(subject_id, root, "T1"))
    t2, spacing2 = _read_analyze(find_subject_file(subject_id, root, "T2"))
    if t1.shape != t2.shape or spacing != spacing2:
        raise ValueError(f"subject-{subject_id}: T1 et T2 incohérents {t1.shape}/{t2.shape}")
    mask = t1 != 0
    label = None
    try:
        raw_label, _ = _read_analyze(find_subject_file(subject_id, root, "label"))
        label = remap_labels(raw_label)
        if label.shape != t1.shape:
            raise ValueError(f"subject-{subject_id}: label shape {label.shape} != {t1.shape}")
    except FileNotFoundError:
        pass
    return Subject(
        t1=t1.astype(np.float32),
        t2=t2.astype(np.float32),
        label=label,
        mask=mask,
        subject_id=subject_id,
        spacing=spacing,
    )


def mask_agreement(subject: Subject) -> float:
    """IoU entre le masque (T1 != 0) et (label != 0). Vaut 1.0 sur les 10 sujets train."""
    if subject.label is None:
        raise ValueError("pas de label")
    lab = subject.label != 0
    return float((subject.mask & lab).sum() / (subject.mask | lab).sum())


def mask_to_volume(values: np.ndarray, mask: np.ndarray, fill=0) -> np.ndarray:
    """Replace un vecteur (n_mask, ...) dans un volume (D, H, W, ...), fill hors masque."""
    out_shape = mask.shape + values.shape[1:]
    out = np.full(out_shape, fill, dtype=values.dtype)
    out.reshape((-1,) + values.shape[1:])[np.flatnonzero(mask)] = values
    return out
