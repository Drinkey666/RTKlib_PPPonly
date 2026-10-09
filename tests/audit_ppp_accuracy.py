"""Read-only, truth-referenced PPP output audit. Reference coordinates never enter the solver.

Examples:
  python tests/audit_ppp_accuracy.py --dataset mar21
  python tests/audit_ppp_accuracy.py --dataset mar17
  python tests/audit_ppp_accuracy.py --dataset mar21 --pos extra=C:/path/result.pos

Mar17's reference coordinate is provisional. All heights are interpreted as
WGS84 ellipsoidal heights; edit --truth if a better surveyed reference exists.
"""

from __future__ import annotations

import argparse
import json
import math
from collections import Counter
from pathlib import Path
from statistics import mean


WGS84_A = 6378137.0
WGS84_F = 1.0 / 298.257223563
WGS84_E2 = WGS84_F * (2.0 - WGS84_F)
HERE = Path(__file__).resolve().parents[1] / "validation" / "user_error_diagnosis"
ROBUST = HERE.parent / "robust"
TRUTH = {
    "mar21": (30.759991, 103.984034, 482.2020),
    "mar17": (30.759928, 103.984162, 482.2530),  # provisional
}


def ecef(lat: float, lon: float, height: float) -> tuple[float, float, float]:
    phi, lam = math.radians(lat), math.radians(lon)
    n = WGS84_A / math.sqrt(1.0 - WGS84_E2 * math.sin(phi) ** 2)
    return (
        (n + height) * math.cos(phi) * math.cos(lam),
        (n + height) * math.cos(phi) * math.sin(lam),
        (n * (1.0 - WGS84_E2) + height) * math.sin(phi),
    )


def enu(lat: float, lon: float, height: float,
        truth: tuple[float, float, float]) -> tuple[float, float, float]:
    dx, dy, dz = (a - b for a, b in zip(ecef(lat, lon, height), ecef(*truth)))
    phi, lam = math.radians(truth[0]), math.radians(truth[1])
    east = -math.sin(lam) * dx + math.cos(lam) * dy
    north = (-math.sin(phi) * math.cos(lam) * dx
             - math.sin(phi) * math.sin(lam) * dy + math.cos(phi) * dz)
    up = (math.cos(phi) * math.cos(lam) * dx
          + math.cos(phi) * math.sin(lam) * dy + math.sin(phi) * dz)
    return east, north, up


def read_pos(path: Path) -> list[dict]:
    rows = []
    with path.open(encoding="utf-8", errors="replace") as stream:
        for line in stream:
            if not line.strip() or line.startswith("%"):
                continue
            fields = line.split()
            if len(fields) < 10:
                raise ValueError(f"short POS row in {path}: {line!r}")
            lat, lon, h = map(float, fields[2:5])
            if not all(map(math.isfinite, (lat, lon, h))):
                raise ValueError(f"nonfinite POS row in {path}: {line!r}")
            if not -90 <= lat <= 90 or not -180 <= lon <= 180:
                raise ValueError(f"expected LLH POS coordinates, not ECEF: {path}")
            rows.append({
                "time": fields[0] + " " + fields[1],
                "lat": lat, "lon": lon, "h": h,
                "Q": int(fields[5]), "ns": int(fields[6]),
                "sdn": float(fields[7]), "sde": float(fields[8]),
                "sdu": float(fields[9]),
            })
    if not rows:
        raise ValueError(f"no solution rows: {path}")
    return rows


def companion(path: Path, suffix: str) -> Path | None:
    # The replay runner uses <stem>.trace; the GUI uses <name>.pos.trace.
    for candidate in (path.with_suffix(suffix), Path(str(path) + suffix)):
        if candidate.exists():
            return candidate
    return None


def read_trace_counts(path: Path | None) -> dict[str, int | None]:
    if path is None:
        return {key: None for key in (
            "reject_events", "slip_checks", "detected_slips",
            "arc_resets", "failure_events")}
    counts = Counter()
    with path.open(encoding="utf-8", errors="replace") as stream:
        for line in stream:
            if "$PPP_REJECT," in line:
                counts["reject_events"] += 1
            if "$SLIP_CHECK," in line:
                counts["slip_checks"] += 1
                if ",slip=1" in line:
                    counts["detected_slips"] += 1
            if "$ARC_RESET," in line:
                counts["arc_resets"] += 1
            if "$PPP_FAILURE," in line:
                counts["failure_events"] += 1
    return {key: counts[key] for key in (
        "reject_events", "slip_checks", "detected_slips",
        "arc_resets", "failure_events")}


def read_ztd(path: Path | None) -> list[dict]:
    if path is None:
        return []
    values = []
    with path.open(encoding="utf-8", errors="replace") as stream:
        for line in stream:
            if not line.startswith("$TROP,"):
                continue
            fields = line.strip().split(",")
            values.append({"week": int(fields[1]), "tow": float(fields[2]),
                           "ztd_m": float(fields[5]), "sigma_m": float(fields[6])})
    return values


def rms(values: list[float]) -> float:
    return math.sqrt(mean(x * x for x in values))


def summary(label: str, path: Path, truth: tuple[float, float, float]) -> tuple[dict, list[dict]]:
    rows = read_pos(path)
    valid_rows = [row for row in rows if row["Q"] > 0]
    if not valid_rows:
        raise ValueError(f"no valid solution rows: {path}")
    errors = [enu(row["lat"], row["lon"], row["h"], truth) for row in valid_rows]
    tail = errors[-60:]
    final = errors[-1]
    ztd = read_ztd(Path(str(path) + ".stat") if Path(str(path) + ".stat").exists() else None)
    out = {
        "label": label, "pos": str(path), "epochs": len(rows),
        "valid_epochs": len(valid_rows), "excluded_Q0_epochs": len(rows)-len(valid_rows),
        "ppp_epochs": sum(row["Q"] == 6 for row in rows),
        "Q_counts": dict(sorted(Counter(row["Q"] for row in rows).items())),
        "first_time": rows[0]["time"], "last_time": rows[-1]["time"],
        "final_valid_time": valid_rows[-1]["time"], "tail_valid_samples": len(tail),
        "final_ENU_m": [round(x, 6) for x in final],
        "final_horizontal_m": round(math.hypot(*final[:2]), 6),
        "final_3d_m": round(math.sqrt(sum(x * x for x in final)), 6),
        "tail60_mean_ENU_m": [round(mean(e[i] for e in tail), 6) for i in range(3)],
        "tail60_rms_horizontal_m": round(rms([math.hypot(*e[:2]) for e in tail]), 6),
        "tail60_rms_3d_m": round(rms([math.sqrt(sum(x * x for x in e)) for e in tail]), 6),
        "final_formal_sigma_ENU_m": [valid_rows[-1]["sde"], valid_rows[-1]["sdn"], valid_rows[-1]["sdu"]],
        "trace": str(companion(path, ".trace")) if companion(path, ".trace") else None,
    }
    out.update(read_trace_counts(companion(path, ".trace")))
    out["ztd"] = ({
        "epochs": len(ztd), "first_m": ztd[0]["ztd_m"],
        "final_m": ztd[-1]["ztd_m"], "final_sigma_m": ztd[-1]["sigma_m"],
        "tail60_mean_m": round(mean(x["ztd_m"] for x in ztd[-60:]), 6),
    } if ztd else None)
    return out, rows


def paired(name1: str, rows1: list[dict], name2: str, rows2: list[dict]) -> dict:
    a = {r["time"]: r for r in rows1}
    b = {r["time"]: r for r in rows2}
    common = sorted(set(a) & set(b))
    distances = []
    common_valid = [t for t in common if a[t]["Q"] > 0 and b[t]["Q"] > 0]
    for time in common_valid:
        p = ecef(a[time]["lat"], a[time]["lon"], a[time]["h"])
        q = ecef(b[time]["lat"], b[time]["lon"], b[time]["h"])
        distances.append(math.dist(p, q))
    return {
        "left": name1, "right": name2, "common_epochs": len(common),
        "common_valid_epochs": len(common_valid),
        "Q_differences": sum(a[t]["Q"] != b[t]["Q"] for t in common),
        "first_difference_time": next((t for t, d in zip(common_valid, distances) if d > 1e-6), None),
        "max_3d_difference_m": round(max(distances), 6) if distances else None,
        "final_3d_difference_m": round(distances[-1], 6) if distances else None,
    }


def default_cases(dataset: str) -> dict[str, Path]:
    if dataset == "mar21":
        cases = {
            "A": HERE / "mar21_A.pos", "B": HERE / "mar21_B.pos",
            "A_PCO": HERE / "mar21_A_pco.pos", "B_PCO": HERE / "mar21_B_pco.pos",
        }
    else:
        cases = {
            "A": ROBUST / "RINEX_A_new.pos", "B": ROBUST / "RINEX_B_new.pos",
            "A_PCO": HERE / "mar17_A_pco.pos", "B_PCO": HERE / "mar17_B_pco.pos",
        }
    return {name: path for name, path in cases.items() if path.exists()}



def plot_errors(data: dict, truth: tuple[float, float, float], path: Path) -> None:
    from datetime import datetime
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, axes = plt.subplots(3, 1, figsize=(10, 8), sharex=True, constrained_layout=True)
    for label, rows in data.items():
        rows = [r for r in rows if r["Q"] > 0]
        times = [datetime.strptime(r["time"], "%Y/%m/%d %H:%M:%S.%f") for r in rows]
        seconds = [(t-times[0]).total_seconds() for t in times]
        errors = [enu(r["lat"], r["lon"], r["h"], truth) for r in rows]
        for i, ax in enumerate(axes):
            ax.plot(seconds, [e[i] for e in errors], label=label, linewidth=1.25)
    for i, ax in enumerate(axes):
        ax.axhline(0, color="black", linewidth=.7)
        ax.set_ylabel(("East error (m)", "North error (m)", "Up error (m)")[i])
        ax.grid(True, alpha=.25)
    axes[0].legend(loc="best")
    axes[-1].set_xlabel("Elapsed observation time (s)")
    fig.suptitle("PPP error against independent WGS84 reference (offline only)")
    fig.savefig(path, dpi=180)
    plt.close(fig)

def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", choices=tuple(TRUTH), help="Optional stored audit dataset")
    parser.add_argument("--no-defaults", action="store_true")
    parser.add_argument("--pair", action="append", default=[], metavar="BEFORE=AFTER")
    parser.add_argument("--plot", type=Path, help="Optional ENU error figure; requires matplotlib")
    parser.add_argument("--truth", nargs=3, type=float, metavar=("LAT", "LON", "ELLIPSOID_H"))
    parser.add_argument("--pos", action="append", default=[], metavar="LABEL=PATH",
                        help="Additional POS file; may override a default case")
    parser.add_argument("--json-out", type=Path)
    args = parser.parse_args()
    if args.truth is None and args.dataset is None:
        parser.error("provide --truth LAT LON ELLIPSOID_H or --dataset")
    truth = tuple(args.truth) if args.truth else TRUTH[args.dataset]
    if not all(map(math.isfinite, truth)) or not -90 <= truth[0] <= 90 or not -180 <= truth[1] <= 180:
        parser.error("invalid WGS84 reference coordinate")
    cases = {} if args.no_defaults or args.dataset is None else default_cases(args.dataset)
    for item in args.pos:
        label, sep, raw_path = item.partition("=")
        if not sep or not label or not raw_path:
            parser.error("--pos must be LABEL=PATH")
        cases[label] = Path(raw_path).resolve()
    if not cases:
        parser.error("provide one or more --pos LABEL=PATH")
    results = {}
    data = {}
    for label, path in cases.items():
        results[label], data[label] = summary(label, path, truth)
    comparisons = []
    for left, right in (("A", "A_PCO"), ("B", "B_PCO"), ("A", "B"), ("A_PCO", "B_PCO")):
        if left in data and right in data:
            comparisons.append(paired(left, data[left], right, data[right]))
    for item in args.pair:
        left, sep, right = item.partition("=")
        if not sep or left not in data or right not in data:
            parser.error("--pair labels must match supplied --pos labels")
        comparisons.append(paired(left, data[left], right, data[right]))
    if args.plot:
        plot_errors(data, truth, args.plot)
    report = {"dataset": args.dataset, "reference_usage": "OFFLINE_ONLY_NOT_SOLVER_INPUT",
              "truth_WGS84_lat_lon_ellipsoid_h": truth,
              "cases": results, "paired": comparisons}
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if args.json_out:
        args.json_out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n",
                                 encoding="utf-8")


if __name__ == "__main__":
    main()
