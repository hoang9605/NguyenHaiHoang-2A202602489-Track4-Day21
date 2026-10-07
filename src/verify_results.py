"""Rerun the saved configuration and compare every numeric benchmark CSV byte for byte."""
import argparse
import json
from pathlib import Path
import subprocess
import sys
import tempfile


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--results", type=Path, default=Path("results"))
    args = parser.parse_args()
    cfg = json.loads((args.results / "config.json").read_text(encoding="utf-8"))
    with tempfile.TemporaryDirectory(prefix="day21-reproduce-") as temp:
        subprocess.run([sys.executable, "-X", "utf8", "-m", "src.benchmark",
                        "--data-root", cfg["data_root"], "--frames", *cfg["frames"],
                        "--yaws", *map(str, cfg["yaws"]), "--min-points", str(cfg["min_points"]),
                        "--seed", str(cfg["seed"]), "--skip-figures", "--out", temp], check=True)
        subprocess.run([sys.executable, "-X", "utf8", "-m", "src.translation_sweep",
                        "--config", str(args.results / "config.json"), "--out", temp,
                        "--skip-figures"], check=True)
        for name in ("object_metrics", "frame_metrics", "object_selection",
                     "yaw_perturb_sweep", "range_summary", "translation_sweep", "translation_objects"):
            filename = name + ".csv"
            if (Path(temp) / filename).read_bytes() != (args.results / filename).read_bytes():
                raise AssertionError(f"Numeric results differ: {filename}")
            print(f"[PASS] identical CSV: {filename}")
    print("[PASS] All benchmark CSVs reproduce exactly")


if __name__ == "__main__":
    main()
