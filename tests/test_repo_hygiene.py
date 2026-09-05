"""Le dépôt ne doit contenir ni marqueur de conflit ni fichier au nom illisible.

Deux accidents de fusion nous sont arrivés et aucun ne se voit à la relecture :

1. Des blocs `<!-- CONFLIT: ... -->` laissés dans le rapport après une réconciliation
   manuelle. Ils compilent sans erreur — pandoc les traite comme des commentaires HTML et
   les supprime — donc le PDF paraît correct alors que le texte contient les deux versions.

2. Deux fichiers vides aux noms formés d'octets non-ASCII, créés à la racine par le
   terminal et ramassés par un `git add -A`. Aucun script du dépôt ne les produit ; c'est
   le `git add` global qu'il faut arrêter, et le seul moyen fiable est de le tester.
"""
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

MARQUEURS = re.compile(r"<!-- (?:CONFLIT|FIN CONFLIT)|^<<<<<<< |^>>>>>>> |^\|\|\|\|\|\|\| ",
                       re.MULTILINE)

# Extensions dont le contenu est du texte que nous rédigeons ou du code que nous écrivons.
SOURCES = {".md", ".py", ".tex", ".bib", ".yaml", ".yml", ".toml", ".sh", ".txt", ".cfg"}

# Ce fichier-ci cite les marqueurs qu'il traque, dans sa docstring et dans son motif.
EXEMPT = {"tests/test_repo_hygiene.py"}


def tracked() -> list[str]:
    out = subprocess.run(["git", "ls-files", "-z"], cwd=ROOT, check=True,
                         capture_output=True).stdout
    return [p.decode("utf-8", "surrogateescape") for p in out.split(b"\0") if p]


def test_aucun_marqueur_de_conflit_dans_les_sources():
    coupables = []
    for rel in tracked():
        p = ROOT / rel
        if rel in EXEMPT or p.suffix not in SOURCES or not p.is_file():
            continue
        for n, ligne in enumerate(p.read_text(errors="replace").splitlines(), 1):
            if MARQUEURS.search(ligne):
                coupables.append(f"{rel}:{n}")
    assert not coupables, "marqueurs de conflit non résolus : " + ", ".join(coupables)


def test_aucun_fichier_suivi_au_nom_non_ascii():
    coupables = [rel for rel in tracked() if not rel.isascii() or any(c < " " for c in rel)]
    assert not coupables, (
        "noms de fichiers illisibles sous suivi git : " + ", ".join(map(repr, coupables))
        + " — ils viennent presque toujours d'un `git add -A` à la racine.")
