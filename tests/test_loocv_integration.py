"""Test d'intégration : la boucle LOO complète tourne de bout en bout sur des sujets jouets.

Les volumes sont écrits au format Analyze 7.5 sur disque, comme les vrais, et relus par
src/io.py : la chaîne testée va du fichier au JSON de résultats, en passant par les features,
l'échantillonnage, le modèle, le post-traitement et les métriques. C'est ce qui garantit que
les deux chemins — modèle ordinaire et modèle à contexte spatial — restent l'un et l'autre
fonctionnels.
"""
import numpy as np
import nibabel as nib
import pytest

from src.eval.loocv import run_loocv
from src.features.registry import build_extractor
from src.models.registry import build

SHAPE = (16, 16, 16)
RAW_LABEL = {1: 10, 2: 150, 3: 250}


def write_subject(root, sid, rng):
    """Coquille LCR / ruban GM / noyau SB, avec des intensités séparables et du bruit."""
    lab = np.zeros(SHAPE, dtype=np.uint8)
    lab[3:13, 3:13, 3:13] = 1
    lab[5:11, 5:11, 5:11] = 2
    lab[7:9, 7:9, 7:9] = 3
    jitter = rng.integers(0, 2)  # les sujets ne sont pas identiques
    lab = np.roll(lab, jitter, axis=0)
    raw = np.zeros(SHAPE, dtype=np.uint8)
    for c, v in RAW_LABEL.items():
        raw[lab == c] = v
    base = {1: 200.0, 2: 500.0, 3: 700.0}
    t1 = np.zeros(SHAPE, dtype=np.float64)
    t2 = np.zeros(SHAPE, dtype=np.float64)
    for c, v in base.items():
        t1[lab == c] = v + rng.normal(0, 25, size=int((lab == c).sum()))
        t2[lab == c] = (900.0 - v) + rng.normal(0, 25, size=int((lab == c).sum()))
    t1[lab == 0] = 0.0
    t2[lab == 0] = 0.0
    affine = np.eye(4)
    for modality, arr, dt in (("T1", t1, np.int16), ("T2", t2, np.int16), ("label", raw, np.uint8)):
        nib.save(nib.AnalyzeImage(arr.astype(dt), affine), str(root / f"subject-{sid}-{modality}.hdr"))


@pytest.fixture(scope="module")
def data_root(tmp_path_factory):
    root = tmp_path_factory.mktemp("iseg_toy")
    rng = np.random.default_rng(0)
    for sid in (1, 2, 3, 4):
        write_subject(root, sid, rng)
    return root


def run(data_root, tmp_path, model_factory, name, postproc=None, postproc_names=None):
    return run_loocv(
        extractor=build_extractor([{"name": "intensity"}, {"name": "spatial"}], cache_dir=None, verbose=False),
        model_factory=model_factory,
        run_name=name,
        data_root=data_root,
        results_dir=tmp_path,
        subject_ids=[1, 2, 3, 4],
        seed=0,
        n_per_class=60,
        prior_correction=True,
        postproc=postproc,
        postproc_names=postproc_names,
        save_proba=False,
        with_distances=True,
    )


def test_chemin_ordinaire(data_root, tmp_path):
    r = run(data_root, tmp_path, lambda: build("logreg", {"max_iter": 200}, 0), "toy_logreg")
    assert r["completed_folds"] == [1, 2, 3, 4]
    assert r["n_params"] == 3 * (r["n_features"] + 1)
    assert 0.0 <= r["mean"]["dice_mean"] <= 1.0
    assert r["mean"]["dice_mean"] > 0.5, "sur des tissus aussi séparables, le Dice doit être bon"
    for m in r["per_subject"].values():
        assert {"dice_csf", "asd_csf", "mhd_csf", "dice_mean"} <= set(m)


def test_chemin_autocontexte(data_root, tmp_path):
    r = run(data_root, tmp_path, lambda: build("autocontext", {"n_inner_folds": 3}, 0), "toy_ac")
    assert r["completed_folds"] == [1, 2, 3, 4]
    f = r["n_features"]
    attendu = 3 * (f + 1) + 3 * (f + 9 + 1)  # étage 1 sur F colonnes, étage 2 sur F + 9
    assert r["n_params"] == attendu, f"{r['n_params']} != {attendu}"
    assert set(r["n_params_breakdown"]) == {"stage1_weights", "stage1_bias", "stage2_weights", "stage2_bias"}
    assert r["mean"]["dice_mean"] > 0.5


def test_chemin_selection_de_features(data_root, tmp_path):
    r = run(data_root, tmp_path, lambda: build("select", {"k": 5}, 0), "toy_select")
    assert r["n_params"] == 3 * (5 + 1) + 5, "les indices retenus comptent comme paramètres"
    assert r["n_params_breakdown"]["feature_indices"] == 5


def test_chemin_avec_postproc(data_root, tmp_path):
    from src.postproc.topology import apply_postproc

    steps = ["smooth", "small_components", "gm_between"]
    r = run(
        data_root, tmp_path,
        lambda: build("logreg", {"max_iter": 200}, 0), "toy_pp",
        postproc=lambda pv, m, sp: apply_postproc(pv, m, sp, steps),
        postproc_names=steps,
    )
    assert r["completed_folds"] == [1, 2, 3, 4]
    assert r["postproc"] == steps
    assert r["mean"]["dice_mean"] > 0.5


def test_autocontexte_ne_voit_pas_le_sujet_de_test(data_root, tmp_path):
    """Le contexte passé au modèle ne contient que les sujets d'entraînement du pli."""
    vus = []

    class Espion:
        needs_context = True

        def fit(self, X, y, context=None):
            vus.append(sorted(s.subject_id for s in context.subjects))
            self.inner = build("logreg", {"max_iter": 100}, 0)
            self.inner.fit(X, y)
            return self

        def predict_proba_subject(self, X_full, subject):
            return self.inner.predict_proba(X_full)

        def n_params(self):
            return self.inner.n_params()

        def param_breakdown(self):
            return self.inner.param_breakdown()

    run(data_root, tmp_path, Espion, "toy_espion")
    assert vus == [[2, 3, 4], [1, 3, 4], [1, 2, 4], [1, 2, 3]]
