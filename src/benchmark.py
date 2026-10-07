"""Controlled KITTI calibration experiment. Run from repo root with -m src.benchmark.

Original lab implementation assisted by Codex; reuses instructor loaders/projection.
See report/METHOD.md for population, denominator, and interpretation limits.
"""
from __future__ import annotations

import argparse
import json
import platform
from pathlib import Path

import cv2
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
import numpy as np
import pandas as pd

from starter.datasets import list_frames, load_frame
from starter.projection import cam_to_image, perturb_extrinsic, velo_to_cam

CLASSES = ("Car", "Van", "Truck", "Pedestrian", "Cyclist")


def points_in_box(points_cam, obj):
    """KITTI bottom-center box; inverse of the object-to-camera rotation."""
    c, s = np.cos(obj.rotation_y), np.sin(obj.rotation_y)
    rotation = np.array([[c, 0, s], [0, 1, 0], [-s, 0, c]])
    finite = np.isfinite(points_cam).all(axis=1)
    local = np.full_like(points_cam, np.nan, dtype=float)
    local[finite] = (points_cam[finite] - obj.location) @ rotation
    h, w, length = obj.dimensions
    return (finite & (np.abs(local[:, 0]) <= length / 2 + 1e-9)
            & (local[:, 1] >= -h - 1e-9) & (local[:, 1] <= 1e-9)
            & (np.abs(local[:, 2]) <= w / 2 + 1e-9))


def box_hit_counts(points_cam, projection, shape, bbox):
    """Out-of-FOV points are misses, not removed from the caller's denominator."""
    uv, _, mask = cam_to_image(points_cam, projection, shape)
    inside = ((uv[:, 0] >= bbox[0]) & (uv[:, 0] <= bbox[2])
              & (uv[:, 1] >= bbox[1]) & (uv[:, 1] <= bbox[3]))
    return int(inside.sum()), int(mask.sum())


def benchmark(data_root, frames, yaws, min_points, lateral_shift_m=0.0):
    object_rows, frame_rows, selection_rows = [], [], []
    for fid in frames:
        fr = load_frame(data_root, fid)
        xyz = fr["points"][:, :3]
        base_cam = velo_to_cam(xyz, fr["calib"])
        base_uv, _, base_mask = cam_to_image(base_cam, fr["calib"].P2, fr["image"].shape)
        base_pixels = np.full((len(xyz), 2), np.nan)
        base_pixels[base_mask] = base_uv
        objects = []
        for oid, obj in enumerate(fr["labels"]):
            if obj.type not in CLASSES or (obj.dimensions <= 0).any() or obj.location[2] <= 0:
                continue
            ids = np.flatnonzero(points_in_box(base_cam, obj))
            selection_rows.append(dict(frame_id=fid, object_id=oid, class_name=obj.type,
                                       depth_m=obj.location[2], n_points=len(ids),
                                       selected=len(ids) >= min_points))
            if len(ids) >= min_points:
                objects.append((oid, obj, ids))
        for yaw in yaws:
            calib = perturb_extrinsic(fr["calib"], yaw_deg=yaw, t_xyz_m=(0, lateral_shift_m, 0))
            cam = velo_to_cam(xyz, calib)
            uv, _, mask = cam_to_image(cam, calib.P2, fr["image"].shape)
            pixels = np.full((len(xyz), 2), np.nan)
            pixels[mask] = uv
            common = mask & base_mask
            shifts = np.linalg.norm(pixels[common] - base_pixels[common], axis=1)
            frame_rows.append(dict(frame_id=fid, yaw_deg=yaw,
                                   n_finite=int(np.isfinite(xyz).all(axis=1).sum()),
                                   n_fov=int(mask.sum()), n_common=int(common.sum()),
                                   shift_p50_px=float(np.median(shifts)) if len(shifts) else np.nan))
            for oid, obj, ids in objects:
                hits, visible = box_hit_counts(cam[ids], calib.P2, fr["image"].shape, obj.bbox)
                depth = float(obj.location[2])
                object_rows.append(dict(frame_id=fid, object_id=oid, class_name=obj.type,
                                        depth_m=depth, range_bin="near <15m" if depth < 15 else
                                        "mid 15-30m" if depth < 30 else "far >=30m",
                                        truncated=obj.truncated, occluded=obj.occluded,
                                        yaw_deg=yaw, n_points=len(ids), n_visible=visible,
                                        n_hit=hits, hit_pct=100 * hits / len(ids)))
        print(f"{fid}: {len(objects)} eligible objects", flush=True)
    if not object_rows:
        raise ValueError("No eligible objects; check classes, frames, and --min-points")
    return pd.DataFrame(object_rows), pd.DataFrame(frame_rows), pd.DataFrame(selection_rows)


def summarize(objects, frames):
    rows = []
    for yaw, group in objects.groupby("yaw_deg", sort=True):
        fg = frames[frames.yaw_deg == yaw]
        rows.append(dict(yaw_deg=yaw, n_frames=len(fg), n_objects=len(group),
                         n_object_points=int(group.n_points.sum()), n_hit=int(group.n_hit.sum()),
                         hit_micro_pct=100 * group.n_hit.sum() / group.n_points.sum(),
                         hit_macro_pct=group.hit_pct.mean(),
                         fov_pct=100 * fg.n_fov.sum() / fg.n_finite.sum(),
                         median_frame_shift_px=fg.shift_p50_px.median()))
    return pd.DataFrame(rows)


def draw_curves(summary, objects, out):
    fig, axes = plt.subplots(1, 3, figsize=(15, 4.3), layout="constrained")
    axes[0].plot(summary.yaw_deg, summary.hit_micro_pct, "o-", label="Object hit (micro)")
    axes[0].plot(summary.yaw_deg, summary.hit_macro_pct, "s-", label="Object hit (macro)")
    axes[0].set(title="Fixed object populations", ylabel="Points inside matched 2D box (%)", ylim=(0, 105))
    axes[1].plot(summary.yaw_deg, summary.fov_pct, "o-", color="#667085")
    axes[1].set(title="FOV alone can miss drift", ylabel="All finite points inside image (%)")
    for name, group in objects.groupby("range_bin", sort=True):
        means = group.groupby("yaw_deg").hit_pct.mean()
        axes[2].plot(means.index, means.values, "o-", label=name)
    axes[2].set(title="Macro hit by camera depth", ylabel="Mean object hit (%)", ylim=(0, 105))
    for ax in axes:
        ax.set_xlabel("LiDAR yaw drift (degrees)")
        ax.grid(alpha=.2)
    axes[0].legend(fontsize=8)
    axes[2].legend(fontsize=8)
    fig.suptitle(f"KITTI mini | {int(summary.n_frames.iloc[0])} frames | Source: KITTI Vision Benchmark Suite", fontsize=11)
    fig.savefig(out / "yaw_perturb_curve.png", dpi=150)
    plt.close(fig)


def make_visuals(data_root, objects, summary, out):
    baseline = objects[objects.yaw_deg == 0].copy()
    examples = []
    for tag, target in (("near", 8), ("mid", 22), ("far", 45)):
        pool = baseline[baseline.hit_pct >= 80]
        if pool.empty:
            pool = baseline
        row = pool.loc[(pool.depth_m - target).abs().idxmin()]
        fr = load_frame(data_root, row.frame_id)
        cam = velo_to_cam(fr["points"][:, :3], fr["calib"])
        uv, depth, _ = cam_to_image(cam, fr["calib"].P2, fr["image"].shape)
        fig, ax = plt.subplots(figsize=(12.5, 4.2), layout="constrained")
        ax.imshow(cv2.cvtColor(fr["image"], cv2.COLOR_BGR2RGB))
        points = ax.scatter(uv[:, 0], uv[:, 1], c=depth, cmap="turbo_r", vmin=0, vmax=60,
                            s=1, alpha=.6, linewidths=0)
        obj = fr["labels"][int(row.object_id)]
        x1, y1, x2, y2 = obj.bbox
        ax.add_patch(Rectangle((x1, y1), x2-x1, y2-y1, fill=False, edgecolor="lime", linewidth=2))
        ax.set_title(f"Baseline | {row.frame_id} object {row.object_id} ({obj.type}) | "
                     f"camera depth {row.depth_m:.2f} m | hit {row.hit_pct:.1f}%")
        ax.set_axis_off()
        fig.colorbar(points, ax=ax, label="Camera depth (m)", shrink=.7)
        fig.savefig(out / f"demo_{tag}.png", dpi=140)
        plt.close(fig)
        examples.append(dict(kind=tag, frame_id=row.frame_id, object_id=int(row.object_id),
                             depth_m=float(row.depth_m), hit_pct=float(row.hit_pct)))

    failure_yaw = float(summary.yaw_deg.max())
    comparison = baseline.merge(objects[objects.yaw_deg == failure_yaw],
                                on=["frame_id", "object_id"], suffixes=("_base", "_drift"))
    comparison["drop_pp"] = comparison.hit_pct_base - comparison.hit_pct_drift
    candidates = comparison[comparison.hit_pct_base >= 80]
    if candidates.empty:
        candidates = comparison
    row = candidates.loc[candidates.drop_pp.idxmax()]
    fr = load_frame(data_root, row.frame_id)
    obj = fr["labels"][int(row.object_id)]
    selected = points_in_box(velo_to_cam(fr["points"][:, :3], fr["calib"]), obj)
    fig, axes = plt.subplots(2, 1, figsize=(13, 8), layout="constrained")
    for ax, yaw, hit in zip(axes, [0, failure_yaw], [row.hit_pct_base, row.hit_pct_drift]):
        calib = perturb_extrinsic(fr["calib"], yaw_deg=yaw)
        uv, _, _ = cam_to_image(velo_to_cam(fr["points"][selected, :3], calib),
                                calib.P2, fr["image"].shape)
        inside = ((uv[:, 0] >= obj.bbox[0]) & (uv[:, 0] <= obj.bbox[2]) &
                  (uv[:, 1] >= obj.bbox[1]) & (uv[:, 1] <= obj.bbox[3]))
        ax.imshow(cv2.cvtColor(fr["image"], cv2.COLOR_BGR2RGB))
        ax.scatter(uv[inside, 0], uv[inside, 1], c="lime", s=7, label="Inside matched box")
        ax.scatter(uv[~inside, 0], uv[~inside, 1], c="red", s=7, label="Outside matched box")
        x1, y1, x2, y2 = obj.bbox
        ax.add_patch(Rectangle((x1, y1), x2-x1, y2-y1, fill=False, edgecolor="yellow", linewidth=2))
        ax.set(xlim=(max(0, x1-120), min(fr["image"].shape[1], x2+120)),
               ylim=(min(fr["image"].shape[0], y2+45), max(0, y1-45)))
        ax.set_title(f"Yaw {yaw:g} deg | matched-box hit {hit:.1f}% | fixed N={int(selected.sum())}")
        ax.legend(loc="upper right", fontsize=8)
        ax.set_axis_off()
    fig.suptitle(f"Failure: {row.frame_id}, object {int(row.object_id)}, {obj.type}, "
                 f"depth {row.depth_m_base:.2f} m | Source: KITTI Vision Benchmark Suite")
    fig.savefig(out / "fail_01_yaw_drift.png", dpi=150)
    plt.close(fig)
    failure = dict(frame_id=row.frame_id, object_id=int(row.object_id), class_name=obj.type,
                   depth_m=float(row.depth_m_base), yaw_deg=failure_yaw,
                   n_points=int(selected.sum()), baseline_hit_pct=float(row.hit_pct_base),
                   drift_hit_pct=float(row.hit_pct_drift), drop_pp=float(row.drop_pp))
    return dict(demos=examples, failure=failure)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--data-root", default="data/kitti_mini")
    ap.add_argument("--frames", nargs="+", help="default: all available frames")
    ap.add_argument("--yaws", nargs="+", type=float, default=[-3, -2, -1, -.5, 0, .5, 1, 2, 3])
    ap.add_argument("--min-points", type=int, default=10)
    ap.add_argument("--seed", type=int, default=21)
    ap.add_argument("--out", type=Path, default=Path("results"))
    ap.add_argument("--skip-figures", action="store_true", help="reproduce numeric CSVs only")
    args = ap.parse_args()
    if args.min_points < 1 or not all(np.isfinite(args.yaws)) or 0 not in args.yaws or max(args.yaws) <= 0:
        ap.error("min-points must be positive; yaws must be finite and include 0 and a positive value")
    frames = args.frames or list_frames(args.data_root)
    yaws = sorted(set(args.yaws))
    np.random.seed(args.seed)  # No random sampling in this experiment.
    args.out.mkdir(parents=True, exist_ok=True)
    objects, frame_metrics, selection = benchmark(args.data_root, frames, yaws, args.min_points)
    summary = summarize(objects, frame_metrics)
    range_summary = objects.groupby(["yaw_deg", "range_bin"], as_index=False).agg(
        n_objects=("object_id", "size"), hit_macro_pct=("hit_pct", "mean"))
    for name, table in (("object_metrics", objects), ("frame_metrics", frame_metrics),
                        ("object_selection", selection), ("yaw_perturb_sweep", summary),
                        ("range_summary", range_summary)):
        table.to_csv(args.out / f"{name}.csv", index=False, float_format="%.8f")
    config = dict(data_root=args.data_root, frames=frames, yaws=yaws, min_points=args.min_points,
                  seed=args.seed, random_sampling=False, classes=list(CLASSES),
                  python=platform.python_version(), platform=platform.platform(),
                  numpy=np.__version__, opencv=cv2.__version__, matplotlib=matplotlib.__version__,
                  pandas=pd.__version__)
    (args.out / "config.json").write_text(json.dumps(config, indent=2), encoding="utf-8")
    if not args.skip_figures:
        figures = args.out / "figures"
        figures.mkdir(exist_ok=True)
        draw_curves(summary, objects, figures)
        metadata = make_visuals(args.data_root, objects, summary, figures)
        (args.out / "visual_cases.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    print(summary.to_string(index=False))


if __name__ == "__main__":
    main()
