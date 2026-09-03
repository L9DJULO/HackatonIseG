"""Tableau d'ablation markdown depuis results/*.json (Dice moyen ± écart-type en LOO)."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main(paths=None) -> None:
    files = [Path(p) for p in paths] if paths else sorted((ROOT / "results").glob("*.json"))
    rows = []
    for f in files:
        r = json.loads(f.read_text())
        if not r.get("mean"):
            continue
        m, s = r["mean"], r["std"]
        rows.append((r["run_name"], "+".join(r["feature_blocks"]), r["n_features"], r["model"], r["n_params"],
                     len(r["completed_folds"]), m["dice_csf"], s["dice_csf"], m["dice_gm"], s["dice_gm"],
                     m["dice_wm"], s["dice_wm"], m["dice_mean"], m.get("asd_gm", float("nan")), m.get("mhd_gm", float("nan")),
                     r.get("sampling", {}), r.get("postproc", [])))
    rows.sort(key=lambda r: r[12])
    print("| run | blocs | n_feat | modèle | n_params | folds | Dice CSF | Dice GM | Dice WM | Dice moyen | ASD GM | MHD GM | Dice/log10(params) |")
    print("|---|---|---:|---|---:|---:|---|---|---|---:|---:|---:|---:|")
    for r in rows:
        import math
        ratio = r[12] / math.log10(r[4]) if r[4] and r[4] > 1 else float("nan")
        print(f"| {r[0]} | {r[1]} | {r[2]} | {r[3]} | {r[4]} | {r[5]} | {r[6]:.3f} ± {r[7]:.3f} | {r[8]:.3f} ± {r[9]:.3f} | "
              f"{r[10]:.3f} ± {r[11]:.3f} | **{r[12]:.4f}** | {r[13]:.2f} | {r[14]:.2f} | {ratio:.3f} |")


if __name__ == "__main__":
    main(sys.argv[1:] or None)
