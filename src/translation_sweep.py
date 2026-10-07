"""Separate lateral translation sweep (LiDAR y-left); yaw stays zero throughout."""
import argparse
import contextlib
import io
import json
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

from src.benchmark import benchmark, summarize


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=Path("results/config.json"))
    parser.add_argument("--out", type=Path, default=Path("results"))
    parser.add_argument("--skip-figures", action="store_true")
    args = parser.parse_args()
    config = json.loads(args.config.read_text(encoding="utf-8"))
    levels_cm = [-10, -5, -2, 0, 2, 5, 10]
    summaries, all_objects = [], []
    for cm in levels_cm:
        with contextlib.redirect_stdout(io.StringIO()):
            objects, frames, _ = benchmark(config["data_root"], config["frames"], [0],
                                           config["min_points"], lateral_shift_m=cm / 100)
        summary = summarize(objects, frames).drop(columns="yaw_deg")
        summary.insert(0, "translation_y_cm", cm)
        summaries.append(summary)
        objects.insert(0, "translation_y_cm", cm)
        all_objects.append(objects)
        print(f"translation_y={cm:+d} cm: macro hit={summary.hit_macro_pct.iloc[0]:.4f}%", flush=True)
    args.out.mkdir(parents=True, exist_ok=True)
    summary = pd.concat(summaries, ignore_index=True)
    summary.to_csv(args.out / "translation_sweep.csv", index=False, float_format="%.8f")
    pd.concat(all_objects, ignore_index=True).to_csv(
        args.out / "translation_objects.csv", index=False, float_format="%.8f")
    if not args.skip_figures:
        fig, axes = plt.subplots(1, 2, figsize=(10, 4), layout="constrained")
        axes[0].plot(summary.translation_y_cm, summary.hit_micro_pct, "o-", label="Micro")
        axes[0].plot(summary.translation_y_cm, summary.hit_macro_pct, "s-", label="Macro")
        axes[0].set(ylabel="Object hit (%)", title="Fixed object populations", ylim=(0, 105))
        axes[0].legend()
        axes[1].plot(summary.translation_y_cm, summary.fov_pct, "o-", color="#667085")
        axes[1].set(ylabel="All finite points inside image (%)", title="FOV proxy")
        for ax in axes:
            ax.set_xlabel("Lateral calibration shift: LiDAR y (cm)")
            ax.grid(alpha=.2)
        fig.suptitle("KITTI | Translation only, yaw = 0 degrees")
        (args.out / "figures").mkdir(exist_ok=True)
        fig.savefig(args.out / "figures/translation_curve.png", dpi=150)
        plt.close(fig)


if __name__ == "__main__":
    main()
