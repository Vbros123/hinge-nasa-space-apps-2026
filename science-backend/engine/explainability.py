"""Deterministic, template-based explanations built only from model outputs and documented assumptions. No LLM, no free text invention.

Every number in `explanation_text` is also present in the structured fields. Wording is deliberately limited to what the screening model can support
(modeled unmet crop-water demand, planned living-cover exposure, feasibility under cited calendars).
"""
from __future__ import annotations
from . import MODEL_VERSION
from .objectives import METRIC_UNITS

UNITS = {"water_deficit_mm": "mm", "rainfall_low_cover_index_mm": "mm", "living_cover_days": "days", "living_cover_equivalent_days": "days",
         "drainage_mm": "mm", "eta_total_mm": "mm", "water_deficit_cash_mm": "mm", "water_deficit_cover_mm": "mm"}
SHORT = {"water_deficit_mm": "modeled unmet crop-water demand", "rainfall_low_cover_index_mm": "rainfall falling on days with low modeled living cover",
         "living_cover_days": "planned days with a living crop on the field", "drainage_mm": "modeled deep drainage",
         "water_deficit_cover_mm": "modeled unmet water demand of the cover crop"}
CANNOT = [
    {"code": "NO_YIELD_PREDICTION", "message": "The model does not predict crop yield, revenue or profit."},
    {"code": "NO_EROSION_OR_RUNOFF_PREDICTION", "message": "The rainfall-low-cover index is an exposure proxy, not erosion, erosivity, runoff or soil loss; residue protection is not credited."},
    {"code": "NO_NITROGEN_OR_CARBON_CREDIT", "message": "No fertilizer credit, nitrogen fixation quantity or soil-carbon change is computed."},
    {"code": "NOT_A_FORECAST", "message": "Historical blocks are stress-test scenarios, not forecast probabilities, and they overlap."},
    {"code": "NOT_FIELD_VALIDATED", "message": "No comparison with field observations has been made."},
    {"code": "DEFICIT_NOT_CROP_DAMAGE", "message": "Modeled unmet water demand is a screening indicator, not observed crop damage."},
]


def _f(x, nd=1):
    return f"{x:.{nd}f}"


def _assumptions(rotation: dict, feas: dict, parameters: dict, crop_library: dict, soil: dict, storage_id: str) -> list[dict]:
    a = []
    for e in feas.get("operation_evidence", []):
        if e["status"] in ("assumed", "none"):
            a.append({"id": f"window:{e['crop']}:{e['action']}", "status": "assumed", "description": f"{e['crop']} {e['action']} window is an assumption"})
    w = parameters["water"]
    a += [{"id": "fallow_kc", "status": "assumed", "description": f"Fallow Kc {w['fallow_kc']} (never zero)"},
          {"id": "residue_kc_multiplier", "status": "assumed", "description": f"Retained-residue multiplier {w['residue_kc_multiplier']}"},
          {"id": "initial_storage_fraction", "status": "assumed", "description": f"Each block starts at {w['initial_storage_fraction']:.0%} of maximum storage (no spin-up unless a spin-up parameter set is used)"},
          {"id": "runoff", "status": "not_modeled", "description": "Surface runoff is not modeled"}]
    if rotation.get("cover_crops"):
        a += [{"id": "cover_kc", "status": "assumed", "description": f"Cover-crop Kc {w['cover_kc']['initial']}/{w['cover_kc']['mid']}/{w['cover_kc']['end']}; no published cereal-rye cover Kc found"},
              {"id": "cover_function", "status": "assumed", "description": f"Living-cover fraction ramps over {parameters['cover_function']['ramp_days']} days, declines over {parameters['cover_function']['decline_days']} days after termination"}]
    for cid in sorted(set(rotation["cash_sequence"])):
        st = crop_library["crops"][cid]["water"].get("stage_status")
        if st and st not in ("sourced",):
            a.append({"id": f"kc_stage_lengths:{cid}", "status": st, "description": f"{cid} Kc stage lengths are {st} (not a North Carolina row)"})
    sc = soil["scenarios"].get(storage_id, {})
    a.append({"id": "soil_storage", "status": sc.get("status", "unknown"), "description": f"Soil storage {sc.get('value')} mm ({sc.get('status')}); not derived from field measurements"})
    if (parameters.get("site") or {}).get("region_status", "").startswith("assumed"):
        a.append({"id": "site_region", "status": "assumed", "description": "Coastal Plain vs Piedmont assignment for the site is assumed"})
    return a


def explain_all(res: dict, summary: dict, rotations: dict, parameters: dict, crop_library: dict, soil: dict,
                baseline: str = "rotation_a", provenance: str = "unspecified") -> dict:
    synthetic = "SYNTHETIC" in str(provenance).upper()
    out = {"model_version": MODEL_VERSION, "baseline_rotation_id": baseline, "data_provenance": provenance,
           "global_limitations": CANNOT, "rotations": []}
    ref_recs = [r for r in res["records"] if r["parameter_set_id"] == "reference"]
    storage_ref = "medium_storage"
    for rid in sorted(rotations):
        feas = res["feasibility"][("reference", rid)]
        rot = rotations[rid]
        hard = [r for r in feas["reasons"] if r["severity"] == "hard"]
        ver = [r for r in feas["reasons"] if r["severity"] == "verification"]
        wrn = [r for r in feas["reasons"] if r["severity"] == "warning" and r["code"] != "CROP_WARNING"]
        crop_notes = [r for r in feas["reasons"] if r["code"] == "CROP_WARNING"]
        warnings = [{"code": r["code"], "message": r["message"], "severity": r["severity"]} for r in hard + ver + wrn]
        warnings += [{"code": c["code"], "message": c["message"], "severity": "caveat"} for c in feas.get("evidence_caveats", [])]
        if synthetic:
            warnings.insert(0, {"code": "DATA_SYNTHETIC", "severity": "critical", "message": "Weather is a synthetic software-test fixture; numbers carry no agronomic meaning."})
        entry = {"rotation_id": rid, "feasibility_status": feas["status"], "feasible": feas["feasible"], "baseline_rotation_id": baseline,
                 "is_baseline": rid == baseline,
                 "feasibility": {"governing_hard_constraints": hard, "verification_items": ver, "calendar_slack_days": feas["calendar"].get("calendar_slack_days"),
                                 "evidence_summary": feas.get("evidence_summary"), "operation_evidence": feas.get("operation_evidence"),
                                 "evidence_caveats": feas.get("evidence_caveats"), "qualitative_crop_notes": [r["message"] for r in crop_notes]},
                 "comparison_metrics": [], "supporting_evidence": {}, "assumptions": [], "warnings": warnings, "sensitivity_findings": {},
                 "limitations": CANNOT}
        text = []
        if synthetic:
            text.append("DEMONSTRATION ON SYNTHETIC WEATHER: the numbers below exercise the software and carry no agronomic meaning.")
        if feas["feasible"]:
            tail = "relies on windows or evidence flagged for verification" if feas["status"] == "feasible_pending_verification" else "all operation dates fall inside the cited windows"
            text.append(f"Schedule feasibility: {rid} is {feas['status'].replace('_', ' ')}; {tail}. This is calendar feasibility under statewide usual practice and cited NC State tables, not a field guarantee.")
        else:
            text.append(f"Schedule feasibility: {rid} is infeasible: " + "; ".join(f"{r['code']} ({r['message']})" for r in hard) + ". No environmental metrics are reported for it.")
        recs = [r for r in ref_recs if r["rotation_id"] == rid and r["feasible"]]
        if recs:
            entry["assumptions"] = _assumptions(rot, feas, parameters, crop_library, soil, storage_ref)
            entry["supporting_evidence"] = {"n_historical_blocks": len(recs), "first_block": recs[0]["scenario_id"], "last_block": recs[-1]["scenario_id"],
                                            "same_weather_for_all_rotations": True, "block_note": summary.get("note"),
                                            "et0_method": res.get("et0_method"), "soil_storage_mm": recs[0]["parameters"]["soil_storage_capacity_mm"]}
            for m in ("water_deficit_mm", "rainfall_low_cover_index_mm", "living_cover_days", "drainage_mm"):
                vals = [r["metrics"][m] for r in recs]
                row = {"metric": m, "unit": UNITS[m], "definition": METRIC_UNITS[m], "rotation_mean": sum(vals) / len(vals)}
                if rid != baseline and summary.get("available"):
                    pc = [p for p in summary["paired_comparisons"] if p["parameter_set_id"] == "reference" and p["rotation_id"] == rid and p["metric"] == m]
                    if pc:
                        p = pc[0]
                        row.update({k: p[k] for k in ("baseline_mean", "mean_paired_difference", "relative_difference_of_baseline_mean", "n_blocks", "blocks_lower_count", "blocks_higher_count", "blocks_equal_count", "direction_of_mean")})
                entry["comparison_metrics"].append(row)
            by = {r["metric"]: r for r in entry["comparison_metrics"]}
            if rid == baseline:
                text.append(f"Reference rotation: mean {SHORT['water_deficit_mm']} was {_f(by['water_deficit_mm']['rotation_mean'])} mm across {len(recs)} overlapping historical 3-year blocks.")
            elif "mean_paired_difference" in by["water_deficit_mm"]:
                d = by["water_deficit_mm"]
                word = {"lower": "less", "higher": "more", "no_difference": "the same"}[d["direction_of_mean"]]
                text.append(f"Modeled water demand: under identical historical weather, {rid} had {word} {SHORT['water_deficit_mm']} than {baseline} on average "
                            f"({_f(d['rotation_mean'])} mm vs {_f(d['baseline_mean'])} mm; mean paired difference {_f(d['mean_paired_difference'])} mm); lower in {d['blocks_lower_count']} and higher in {d['blocks_higher_count']} of {d['n_blocks']} overlapping blocks. "
                            "This is a screening indicator, not crop damage.")
                c = by["rainfall_low_cover_index_mm"]; lv = by["living_cover_days"]
                if "mean_paired_difference" in c:
                    cw = {"lower": "less", "higher": "more", "no_difference": "the same"}[c["direction_of_mean"]]
                    ld = lv["mean_paired_difference"]
                    lw = "more" if ld > 0 else ("fewer" if ld < 0 else "the same number of")
                    text.append(f"Planned living cover: over the 3-year block the schedule has {_f(abs(ld), 0) + ' ' if ld else ''}{lw} planned days with a living crop than {baseline} and {cw} rainfall on days with low modeled living cover "
                                f"({_f(c['rotation_mean'])} mm vs {_f(c['baseline_mean'])} mm). This is an exposure proxy, not erosion or runoff.")
                tr = summary["tradeoffs_reference"].get(rid, {})
                if tr.get("tradeoff_present"):
                    warnings.append({"code": "TRADEOFF_ACROSS_OBJECTIVES", "severity": "finding", "message": f"Lower: {', '.join(tr['objectives_lower_than_baseline'])}; higher: {', '.join(tr['objectives_higher_than_baseline'])}"})
                    text.append("Trade-off: objectives point in different directions ("
                                f"lower than baseline: {', '.join(tr['objectives_lower_than_baseline'])}; higher: {', '.join(tr['objectives_higher_than_baseline'])}). No combined score is computed.")
                sens = summary["sensitivity"].get(rid, {})
                for m in ("water_deficit_mm", "rainfall_low_cover_index_mm"):
                    s = sens.get(m)
                    if not s:
                        continue
                    entry["sensitivity_findings"][m] = s
                    flips = s["parameter_sets_where_direction_differs_from_reference"]
                    if flips:
                        warnings.append({"code": "COMPARISON_SENSITIVE_TO_PARAMETERS", "severity": "finding", "metric": m, "parameter_sets": flips,
                                         "message": f"Direction of the {m} comparison differs from the reference in: {', '.join(flips)}"})
                        text.append(f"Sensitivity: the direction of the {SHORT[m]} comparison changed under {', '.join(flips)}.")
                    else:
                        text.append(f"Sensitivity: the direction of the {SHORT[m]} comparison ({s['reference_direction'].replace('_', ' ')}) did not change across {s['n_parameter_sets']} parameter sets (storage, Kc, dates, residue, cover and initial-condition scenarios).")
                dirs = summary["sensitivity"][rid]["water_deficit_mm"]["direction_by_parameter_set"]
                st = {p: dirs.get(p) for p in ("low_storage", "high_storage")}
                entry["sensitivity_findings"]["soil_storage_directions"] = st
                wb = summary["worst_blocks"]["water_deficit_mm"].get(rid, {}).get("largest_increase_vs_baseline_blocks")
                if wb:
                    entry["supporting_evidence"]["largest_increase_vs_baseline_blocks"] = wb
                    text.append("Unfavorable weather blocks (largest increase in modeled unmet demand versus baseline): " + ", ".join(f"{b['scenario_id']} (+{_f(b['difference'])} mm)" for b in wb) + ".")
        text.append("Not substantiated by this model: yield, profit, erosion or runoff, nitrogen or carbon credits, future outcomes, or field validity.")
        entry["warnings"] = warnings
        entry["explanation_text"] = " ".join(text)
        out["rotations"].append(entry)
    return out
