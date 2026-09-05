"""Registre des modèles : `build(name, config, seed)`, la signature qu'attend src/cli.py.

Noms disponibles :
  random        stub aléatoire, validation de la plomberie
  logreg        régression logistique multinomiale (le modèle de référence du rapport)
  select        logreg précédé d'une sélection de K colonnes (config: k)
  autocontext   deux étages reliés par des colonnes de contexte, avec K-fold interne
                (config: n_inner_folds, plus la config du modèle de base sous `base`)

Un nom inconnu lève KeyError, ce que la CLI transforme en échec immédiat plutôt qu'en run
silencieusement faux.
"""
from __future__ import annotations

from src.models.autocontext import AutoContext
from src.models.select import SelectedFeatures
from src.models.stub import build_stub


def _base_factory(config: dict, seed: int):
    base = dict(config.get("base", {}))
    base_name = base.pop("name", "logreg")
    return lambda: build_stub(base_name, base, seed)


def build(name: str, config: dict, seed: int):
    config = dict(config or {})
    if name in ("random", "logreg"):
        return build_stub(name, config, seed)
    if name == "select":
        k = config.pop("k", None)
        if k is None:
            raise KeyError("le modèle 'select' exige une valeur 'k' dans sa config")
        return SelectedFeatures(_base_factory(config, seed), k=int(k), seed=seed)
    if name == "autocontext":
        return AutoContext(
            _base_factory(config, seed),
            n_inner_folds=int(config.get("n_inner_folds", 3)),
            seed=seed,
        )
    raise KeyError(f"modèle inconnu {name!r}, disponibles : random, logreg, select, autocontext")
