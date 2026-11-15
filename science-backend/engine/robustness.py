"""Descriptive robustness assessment of paired rotation comparisons.

Everything here is a count, a mean, a range or a sign. There are NO probabilities, NO confidence intervals and NO combined score:
historical blocks overlap (not independent) and parameter sets are scenarios, not draws from a distribution.
"""
from __future__ import annotations
import pandas as pd

OBJECTIVES = {"water_deficit_mm": "lower", "rainfall_low_cover_index_mm": "lower"}      # direction in which the modeled quantity is smaller
DESCRIPTIVE = ["eta_total_mm", "drainage_mm", "living_cover_days", "living_cover_equivalent_days", "water_deficit_cash_mm", "water_deficit_cover_mm"]
TIE_TOL = 1e-6
NOTE = ("Counts of blocks are counts of overlapping 3-year windows, not independent observations; parameter sets are scenarios, not samples. "
        "No probability, confidence interval or overall score is computed.")


def records_frame(records: list[dict], metrics: list[str]) -> pd.DataFrame:
    rows = []
    for r in records:
        if not r["feasible"] or not r["metrics"]:
            continue
        row = {"rotation_id": r["rotation_id"], "scenario_id": r["scenario_id"], "parameter_set_id": r["parameter_set_id"], "category": r.get("category"),
               "assumption_status": r.get("assumption_status")}
        row.update({m: r["metrics"][m] for m in metrics})
        rows.append(row)
    return pd.DataFrame(rows)


def _sign(x: float) -> str:
    return "lower" if x < -TIE_TOL else ("higher" if x > TIE_TOL else "no_difference")


def paired_differences(df: pd.DataFrame, metric: str, baseline: str) -> pd.DataFrame:
    """Per (parameter set, rotation): paired differences vs the baseline on identical weather blocks."""
    b = df[df.rotation_id == baseline].set_index(["parameter_set_id", "scenario_id"])[metric].rename("base")
    d = df[df.rotation_id != baseline].join(b, on=["parameter_set_id", "scenario_id"], how="inner")
    d["diff"] = d[metric] - d["base"]
    out = []
    for (pid, rid), g in d.groupby(["parameter_set_id", "rotation_id"]):
        mean_diff = float(g["diff"].mean())
        out.append({"parameter_set_id": pid, "rotation_id": rid, "metric": metric, "n_blocks": int(len(g)),
                    "baseline_mean": float(g["base"].mean()), "rotation_mean": float(g[metric].mean()),
                    "mean_paired_difference": mean_diff,
                    "relative_difference_of_baseline_mean": (mean_diff / float(g["base"].mean())) if abs(float(g["base"].mean())) > 0 else None,
                    "min_paired_difference": float(g["diff"].min()), "max_paired_difference": float(g["diff"].max()),
                    "blocks_lower_count": int((g["diff"] < -TIE_TOL).sum()), "blocks_higher_count": int((g["diff"] > TIE_TOL).sum()),
                    "blocks_equal_count": int((g["diff"].abs() <= TIE_TOL).sum()), "direction_of_mean": _sign(mean_diff)})
    return pd.DataFrame(out)


def worst_blocks(df: pd.DataFrame, metric: str, baseline: str, parameter_set_id: str = "reference", k: int = 3) -> dict:
    """Blocks with the largest absolute metric values and with the largest paired differences against the baseline."""
    ref = df[df.parameter_set_id == parameter_set_id]
    out = {}
    for rid, g in ref.groupby("rotation_id"):
        top = g.sort_values([metric, "scenario_id"], ascending=[False, True]).head(k)
        entry = {"highest_value_blocks": [{"scenario_id": r.scenario_id, "value": float(getattr(r, metric))} for r in top.itertuples()]}
        if rid != baseline:
            b = ref[ref.rotation_id == baseline].set_index("scenario_id")[metric]
            g2 = g.set_index("scenario_id")[metric] - b
            g2 = g2.dropna().reset_index().rename(columns={metric: "diff"}).sort_values(["diff", "scenario_id"], ascending=[False, True]).head(k)
            entry["largest_increase_vs_baseline_blocks"] = [{"scenario_id": r.scenario_id, "difference": float(r.diff)} for r in g2.itertuples()]
        out[rid] = entry
    return out


def robustness_summary(records: list[dict], baseline: str = "rotation_a", metrics: list[str] | None = None) -> dict:
    metrics = metrics or list(OBJECTIVES) + DESCRIPTIVE
    df = records_frame(records, metrics)
    if df.empty or baseline not in set(df.rotation_id):
        return {"baseline_rotation_id": baseline, "note": NOTE, "available": False, "reason": "baseline rotation has no feasible simulated records"}
    pids = sorted(df.parameter_set_id.unique())
    cats = df.drop_duplicates("parameter_set_id").set_index("parameter_set_id")[["category", "assumption_status"]]
    pairs = pd.concat([paired_differences(df, m, baseline) for m in metrics], ignore_index=True)
    sens = {}
    for (rid, m), g in pairs.groupby(["rotation_id", "metric"]):
        g = g.sort_values("parameter_set_id")
        signs = {r.parameter_set_id: r.direction_of_mean for r in g.itertuples()}
        ref_sign = signs.get("reference")
        flips = sorted(p for p, sgn in signs.items() if ref_sign is not None and sgn != ref_sign)
        by_cat = {}
        for r in g.itertuples():
            c = cats.loc[r.parameter_set_id, "category"]
            lo, hi = by_cat.get(c, (r.mean_paired_difference, r.mean_paired_difference))
            by_cat[c] = (min(lo, r.mean_paired_difference), max(hi, r.mean_paired_difference))
        sens.setdefault(rid, {})[m] = {
            "reference_direction": ref_sign,
            "reference_mean_paired_difference": float(g[g.parameter_set_id == "reference"].mean_paired_difference.iloc[0]) if ref_sign else None,
            "direction_by_parameter_set": signs,
            "parameter_sets_where_direction_differs_from_reference": flips,
            "consistent_across_all_parameter_sets": not flips,
            "range_of_mean_paired_difference_by_category": {c: {"min": lo, "max": hi} for c, (lo, hi) in sorted(by_cat.items())},
            "n_parameter_sets": len(signs)}
    tradeoffs = {}
    for rid in sorted(set(pairs.rotation_id)):
        ref = pairs[(pairs.parameter_set_id == "reference") & (pairs.rotation_id == rid) & (pairs.metric.isin(OBJECTIVES))]
        better = sorted(ref[ref.direction_of_mean == "lower"].metric)
        worse = sorted(ref[ref.direction_of_mean == "higher"].metric)
        tradeoffs[rid] = {"objectives_lower_than_baseline": better, "objectives_higher_than_baseline": worse, "tradeoff_present": bool(better and worse)}
    # per-parameter-set tradeoff stability
    tr_sets = {}
    for rid in sorted(set(pairs.rotation_id)):
        tr_sets[rid] = sorted(p for p in pids if (lambda sub: bool((sub.direction_of_mean == "lower").any() and (sub.direction_of_mean == "higher").any()))(
            pairs[(pairs.parameter_set_id == p) & (pairs.rotation_id == rid) & (pairs.metric.isin(OBJECTIVES))]))
    return {"baseline_rotation_id": baseline, "available": True, "note": NOTE, "objective_direction": OBJECTIVES,
            "n_parameter_sets": len(pids), "n_blocks": int(df[df.parameter_set_id == "reference"].scenario_id.nunique()),
            "paired_comparisons": pairs.sort_values(["parameter_set_id", "rotation_id", "metric"]).to_dict("records"),
            "sensitivity": sens, "tradeoffs_reference": tradeoffs, "parameter_sets_with_tradeoff": tr_sets,
            "worst_blocks": {m: worst_blocks(df, m, baseline) for m in OBJECTIVES}}


def ranking_stability(records: list[dict], metric: str = "water_deficit_mm") -> dict:
    """Order of rotations by mean metric within each parameter set, and whether that order ever changes. Descriptive only."""
    df = records_frame(records, [metric])
    orders = {}
    for pid, g in df.groupby("parameter_set_id"):
        m = g.groupby("rotation_id")[metric].mean().sort_values(kind="stable")
        orders[pid] = list(m.index)
    distinct = sorted({tuple(v) for v in orders.values()})
    return {"metric": metric, "order_lowest_to_highest_by_parameter_set": orders, "distinct_orders": [list(o) for o in distinct],
            "order_identical_across_parameter_sets": len(distinct) == 1, "note": NOTE}
