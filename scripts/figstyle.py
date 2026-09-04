"""Palette et réglages typographiques communs aux figures du rapport.

Contraintes : lisible en niveaux de gris (les luminances des trois tissus sont bien
séparées), corps de police suffisant pour une lecture du PDF à 100 %, aucune figure ne
porte de titre interne, la légende du rapport suffit.
"""
from __future__ import annotations

import matplotlib.pyplot as plt

# Tissus. Luminances croissantes : LCR sombre, substance grise moyenne, blanche claire.
COL_CSF, COL_GM, COL_WM = "#21374B", "#E3A76F", "#F5E8CE"
EDGE_GM, EDGE_WM = "#8C4E17", "#8A7442"

# Accent : réservé à ce qui coûte des paramètres appris, et à la branche mise en évidence.
ACCENT = "#B4472A"
ACCENT_LIGHT = "#F0D3C6"

# Neutres : tout ce qui est recalculé sur le sujet courant, donc gratuit.
NEUTRAL_FILL, NEUTRAL_EDGE, NEUTRAL_TEXT = "#F2F0EC", "#6E6A64", "#2B2B2B"

RC = {
    "font.size": 8.5, "axes.labelsize": 8.5, "xtick.labelsize": 7.5,
    "ytick.labelsize": 7.5, "legend.fontsize": 7.5, "axes.linewidth": 0.6,
    "xtick.major.width": 0.6, "ytick.major.width": 0.6, "pdf.fonttype": 42,
}


def use() -> None:
    plt.rcParams.update(RC)
