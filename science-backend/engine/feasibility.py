"""Crop-rotation feasibility. Hard constraints vs. warnings vs. verification flags.

Statuses
  feasible                       every check passed on sourced values
  feasible_pending_verification  no hard failure, but at least one check relies on an `assumed` parameter
  infeasible                     at least one hard constraint failed (reasons list says which and why)
severity: hard | warning | verification
"""
from __future__ import annotations
import pandas as pd
from .crop_calendar import parse_md, md_in_window, build_periods, operation_date


def _r(code, message, source_id=None, severity="hard", crop=None, **extra):
    d = {"code": code, "severity": severity, "message": message, "source_id": source_id}
    if crop:
        d["crop"] = crop
    d.update(extra)
    return d


def validate_crop_sequence(rotation: dict, crop_library: dict) -> list[dict]:
    out = []
    crops = crop_library["crops"]
    seq = rotation["cash_sequence"]
    for cid in seq + rotation.get("cover_crops", []):
        if cid not in crops:
            out.append(_r("UNKNOWN_CROP", f"{cid} is not in the crop library"))
    if out:
        return out
    for a, b in zip(seq[:-1], seq[1:]):
        ca, cb = crops[a], crops[b]
        if a in cb["rotation"].get("preceding_crop_restrictions", []) or b in ca["rotation"].get("following_crop_restrictions", []):
            out.append(_r("SEQUENCE_RESTRICTION", f"{b} may not follow {a} per sourced restriction", crop=b))
        elif ca["family"] == cb["family"] and a != b:
            out.append(_r("CROP_FAMILY_REPEAT", f"{a} -> {b}: same crop family ({ca['family']}); relevant disease/pest carry-over is qualitative only",
                          severity="warning", crop=b))
        elif a == b:
            out.append(_r("SAME_CROP_BACK_TO_BACK", f"{a} twice in a row", severity="warning", crop=b))
    for cid in dict.fromkeys(seq + rotation.get("cover_crops", [])):
        ws = list(crops[cid]["rotation"].get("warnings", []))
        if rotation.get("cover_crops"):
            ws += crops[cid]["rotation"].get("warnings_with_cover", [])
        for w in ws:
            out.append(_r("CROP_WARNING", w, severity="warning", crop=cid))
    return out


SOFT_STATUSES = ("sourced_descriptive", "sourced_secondary")
HARD_STATUSES = ("sourced",)


def _window_for(crop: dict, op: dict, action: str, region: str = "coastal_plain"):
    w = None
    if action == "plant":
        if op["crop"] == "soybean":
            key = "double_crop_window" if op.get("label") == "double_crop" else "full_season_window"
            if crop.get(key):
                w = crop[key]
        if w is None:
            w = crop.get("planting_window")
    elif action == "harvest":
        w = crop.get("harvest_window")
    elif action == "terminate":
        w = crop.get("termination_window")
    if w and region == "piedmont" and isinstance(w.get("piedmont"), dict):
        w = {**w, **w["piedmont"]}
    return w


def _in(md, lo, hi):
    return md_in_window(md, lo, hi)


def operation_evidence(rotation: dict, crop_library: dict, region: str = "coastal_plain") -> list[dict]:
    """One record per operation: which window governs it, its evidence class, and whether the date sits inside it."""
    out = []
    for op in rotation["operations"]:
        c = crop_library["crops"][op["crop"]]
        w = _window_for(c, op, op["action"], region)
        rec = {"crop": op["crop"], "action": op["action"], "date": op["date"], "year_offset": op["year_offset"],
               "window": None, "status": "none", "inside": None, "inside_most_active": None, "evidence_ids": [], "source_id": None}
        if w and w.get("earliest"):
            rec.update({"window": [w["earliest"], w["latest"]], "status": w.get("status", "assumed"), "source_id": w.get("source_id"),
                        "evidence_ids": w.get("evidence_ids", []), "inside": _in(op["date"], w["earliest"], w["latest"])})
            ma = w.get("most_active")
            if ma:
                rec["inside_most_active"] = _in(op["date"], ma["earliest"], ma["latest"])
            if w.get("extended_latest") and not rec["inside"] and op["action"] == "plant":
                rec["inside_extended"] = _in(op["date"], w["earliest"], w["extended_latest"])
        out.append(rec)
    return out


def validate_planting_windows(rotation: dict, crop_library: dict, region: str = "coastal_plain") -> list[dict]:
    """Window checks by evidence class.

    sourced              outside -> hard (PLANTING_WINDOW_CONFLICT / OPERATION_WINDOW_CONFLICT); past preferred -> LATE_ESTABLISHMENT warning
    sourced_descriptive  inside -> supported (warning only if outside the 'most active' sub-range);
    sourced_secondary    outside -> OUTSIDE_USUAL_RANGE (verification), or LATE_PLANTING_EXTENDED (warning) if within a documented late extension
    assumed / other      always ASSUMED_WINDOW (verification)
    """
    out = []
    crops = crop_library["crops"]
    for op, ev in zip(rotation["operations"], operation_evidence(rotation, crop_library, region)):
        c = crops[op["crop"]]
        w = _window_for(c, op, op["action"], region)
        what = f"{op['crop']} {op['action']} on {op['date']} (year {op['year_offset'] + 1})"
        if not w or w.get("earliest") is None:
            out.append(_r("WINDOW_UNKNOWN", f"No window known for {what}", severity="verification", crop=op["crop"]))
            continue
        inside, sid, status = ev["inside"], w.get("source_id"), w.get("status", "assumed")
        rng = f"{w['earliest']} to {w['latest']}"
        if status in HARD_STATUSES:
            if not inside:
                out.append(_r("PLANTING_WINDOW_CONFLICT" if op["action"] == "plant" else "OPERATION_WINDOW_CONFLICT",
                              f"{what} is outside the sourced window {rng}", sid, crop=op["crop"]))
            elif op["action"] == "plant" and w.get("preferred_latest") and not _in(op["date"], w["earliest"], w["preferred_latest"]):
                out.append(_r("LATE_ESTABLISHMENT", f"{what} is later than the preferred date {w['preferred_latest']}; reduced establishment likely (qualitative)",
                              sid, severity="warning", crop=op["crop"]))
        elif status in SOFT_STATUSES:
            if inside:
                if ev["inside_most_active"] is False:
                    ma = w["most_active"]
                    out.append(_r("OUTSIDE_MOST_ACTIVE", f"{what} is inside the usual range {rng} but outside the most-active period {ma['earliest']} to {ma['latest']}",
                                  sid, severity="warning", crop=op["crop"]))
            elif ev.get("inside_extended"):
                out.append(_r("LATE_PLANTING_EXTENDED", f"{what} is after the usual range {rng} but within the documented late-planting extension to {w['extended_latest']}; expect lower yield potential (qualitative)",
                              w.get("extended_source_id", sid), severity="warning", crop=op["crop"]))
            else:
                out.append(_r("OUTSIDE_USUAL_RANGE", f"{what} is outside the usual range {rng} ({status}); not a proven limit, verify",
                              sid, severity="verification", crop=op["crop"]))
        else:
            out.append(_r("ASSUMED_WINDOW", f"{what}: window {rng} is an assumption ({'inside' if inside else 'OUTSIDE'}); verify before relying on it",
                          sid, severity="verification", crop=op["crop"], inside=inside))
    return out


def validate_calendar(rotation: dict, crop_library: dict, parameters: dict, start_year: int = 2001) -> tuple[list[dict], dict]:
    """Operation ordering, overlaps, cover-termination gaps, harvest-to-planting slack, growth duration."""
    out, info = [], {}
    crops = crop_library["crops"]
    try:
        periods = build_periods(rotation, start_year)
    except Exception as e:
        return [_r("CALENDAR_INVALID", str(e))], info
    slacks = []
    warn_slack = float(parameters.get("min_slack_days_warning", 3))
    for p in periods:
        c = crops[p["crop"]]
        span = (p["end"] - p["start"]).days
        dur = c["growth"]["duration_days"]
        if c["role"] == "cash_crop" and dur.get("min") is not None and span < dur["min"]:
            sev = "hard" if dur.get("status") == "sourced" else "verification"
            out.append(_r("CROP_DURATION_SHORT", f"{p['crop']} occupies the field {span} days (planting to harvest); published minimum is {dur['min']}",
                          dur.get("source_id"), severity=sev, crop=p["crop"]))
    for a, b in zip(periods[:-1], periods[1:]):
        gap = (b["start"] - a["end"]).days
        ca, cb = crops[a["crop"]], crops[b["crop"]]
        if gap < 0:
            # overlap: only a cover crop planted before the preceding cash crop is harvested is an establishment conflict
            code = "COVER_ESTABLISHMENT_CONFLICT" if cb["role"] == "cover_crop" and ca["role"] == "cash_crop" else "OPERATION_CONFLICT"
            out.append(_r(code, f"{b['crop']} planting ({b['start'].date()}) precedes the end of {a['crop']} ({a['end'].date()}) by {-gap} days",
                          None, crop=b["crop"]))
            continue
        if ca["role"] == "cover_crop" and cb["role"] == "cash_crop":
            need = ca.get("pre_cash_crop_gap_days", {}).get("min")
            if need is not None and gap < need:
                out.append(_r("COVER_TERMINATION_GAP", f"Cover terminated {gap} days before {b['crop']} planting; NC State advises {need}-{ca['pre_cash_crop_gap_days']['max']} days",
                              ca["pre_cash_crop_gap_days"]["source_id"], crop=b["crop"]))
            slacks.append(gap)
        elif ca["role"] == "cash_crop":
            slacks.append(gap)
            if gap < warn_slack:
                out.append(_r("LOW_SLACK", f"Only {gap} days between {a['crop']} end and {b['crop']} start (assumed practical minimum {warn_slack})",
                              None, severity="warning", crop=b["crop"]))
    info["calendar_slack_days_min"] = min(slacks) if slacks else None
    info["calendar_slack_days"] = slacks
    return out, info


def validate_management_constraints(rotation: dict, crop_library: dict, management: dict) -> list[dict]:
    out = []
    avail = set(management.get("equipment_available", []))
    for eq in rotation.get("required_equipment", []):
        if eq not in avail:
            out.append(_r("EQUIPMENT_UNAVAILABLE", f"Required equipment '{eq}' is not available"))
    excluded = set(management.get("excluded_crops", []))
    for cid in set(rotation["cash_sequence"]) | set(rotation.get("cover_crops", [])):
        if cid in excluded:
            out.append(_r("FARMER_EXCLUDED_CROP", f"{cid} is excluded by the farmer", crop=cid))
    method = rotation.get("termination_method", "herbicide")
    for cid in rotation.get("cover_crops", []):
        sup = crop_library["crops"][cid].get("termination_methods_supported", [])
        if method not in sup:
            out.append(_r("UNSUPPORTED_TERMINATION_METHOD", f"{cid} termination by '{method}' is not supported by the crop record", crop=cid))
        if method not in management.get("termination_methods_available", []):
            out.append(_r("TERMINATION_METHOD_UNAVAILABLE", f"Termination method '{method}' is not available on this farm", crop=cid))
    market = management.get("market_access_confirmed", {})
    for cid in rotation.get("requires_market_access", []):
        if cid not in market:
            out.append(_r("MARKET_ACCESS_UNKNOWN", f"Market access for {cid} not confirmed or denied", severity="verification", crop=cid))
        elif not market[cid]:
            out.append(_r("MARKET_ACCESS_UNCONFIRMED", f"{cid} has no confirmed buyer access", crop=cid))
    return out


def evaluate_rotation_feasibility(rotation: dict, crop_library: dict, soil: dict | None, management: dict, parameters: dict | None = None) -> dict:
    parameters = parameters or {}
    region = (parameters.get("site") or {}).get("region", "coastal_plain")
    reasons = []
    reasons += validate_crop_sequence(rotation, crop_library)
    if not any(r["code"] == "UNKNOWN_CROP" for r in reasons):
        reasons += validate_planting_windows(rotation, crop_library, region)
        cal, info = validate_calendar(rotation, crop_library, parameters)
        reasons += cal
        reasons += validate_management_constraints(rotation, crop_library, management)
    else:
        info = {}
    if not soil or not soil.get("scenarios"):
        reasons.append(_r("SOIL_STORAGE_UNKNOWN", "No soil water storage available; water metrics suppressed", severity="verification"))
    caveats = _evidence_caveats(rotation, crop_library, region, parameters) if not any(r["code"] == "UNKNOWN_CROP" for r in reasons) else []
    hard = [r for r in reasons if r["severity"] == "hard"]
    ver = [r for r in reasons if r["severity"] == "verification"]
    status = "infeasible" if hard else ("feasible_pending_verification" if ver else "feasible")
    return {"rotation_id": rotation["rotation_id"], "status": status, "feasible": not hard, "reasons": reasons,
            "assumption_dependencies": sorted({r["source_id"] for r in ver if r.get("source_id")}),
            "calendar": info, "region": region, "evidence_caveats": caveats,
            "operation_evidence": operation_evidence(rotation, crop_library, region) if not any(r["code"] == "UNKNOWN_CROP" for r in reasons) else [],
            "evidence_summary": _evidence_summary(rotation, crop_library, region) if not any(r["code"] == "UNKNOWN_CROP" for r in reasons) else {}}


def _evidence_summary(rotation, crop_library, region):
    n = {}
    for e in operation_evidence(rotation, crop_library, region):
        n[e["status"]] = n.get(e["status"], 0) + 1
    return n


def _evidence_caveats(rotation, crop_library, region, parameters):
    """Machine-readable reasons a status of `feasible` is still not a field guarantee."""
    ev = operation_evidence(rotation, crop_library, region)
    out = []
    if any(e["status"] in SOFT_STATUSES for e in ev):
        out.append({"code": "STATEWIDE_USUAL_DATES", "message": "Windows are statewide usual practice (descriptive), not Johnston County-specific limits."})
    if any(e["status"] in HARD_STATUSES for e in ev) and (parameters.get("site") or {}).get("region_status", "").startswith("assumed"):
        out.append({"code": "REGION_UNVERIFIED", "message": "Coastal Plain vs Piedmont assignment for the site is assumed; cover-crop tables differ by region."})
    if any(e["status"] == "sourced_secondary" for e in ev):
        out.append({"code": "SECONDARY_SOURCE", "message": "At least one window rests on a secondary quote of a primary source."})
    for e in ev:
        if e["status"] in ("assumed", "none"):
            out.append({"code": "ASSUMED_WINDOW_USED", "message": f"{e['crop']} {e['action']} uses an assumed window."}); break
    out.append({"code": "NO_HUMAN_REVIEW", "message": "Cited pages were read by the build agent; no human agronomist has confirmed them."})
    return out
