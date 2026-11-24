import copy
import heapq
from datetime import datetime
from compatibility import get_compatible_donors
from loader import (
    load_all_inventory,
    save_inventory,
    load_all_requests,
    save_requests,
    load_dispatch_history,
    append_dispatch_history,
    generate_next_id,
)


def compute_urgency_score(urgency_weight: int, expiry_dt, reference_date=None) -> float:
    """
    PPT Urgency Score Formula:
        Score S = (Urgency Weight * 100) - (Days to Expiry * 2)
    """
    ref_date = reference_date or datetime.now().date()
    days_to_expiry = max(0, (expiry_dt - ref_date).days)
    return round((float(urgency_weight) * 100.0) - (days_to_expiry * 2.0), 2)


def preview_allocation(inventory: list, requests: list) -> list:
    """
    Generate a non-destructive allocation preview ordered by:
      1. Urgency weight descending (Critical=4, High=3, Moderate=2, Routine=1)
      2. Earlier timestamp_received first
      3. Exact blood group match first, then compatible donor groups
      4. Earliest-Expiry-First (EEF) unit selection
    Also computes the PPT urgency score S = (Weight * 100) - (Days to Expiry * 2)
    for each selected unit. Does NOT mutate live inventory or request files.
    """
    sim_inventory = copy.deepcopy(inventory)
    sim_requests = copy.deepcopy(requests)
    today = datetime.now().date()

    # Group valid available units by (blood_group, component_type)
    buckets = {}
    for unit in sim_inventory:
        if unit.get("status", "").strip().lower() != "available":
            continue
        if unit.get("expiry_dt") is not None and unit["expiry_dt"] < today:
            continue
        key = (unit["full_group"].strip(), unit["component_type"].strip())
        buckets.setdefault(key, []).append(unit)

    # Sort each bucket by earliest expiry date first, then unit_id for determinism
    for key in buckets:
        buckets[key].sort(key=lambda u: (u["expiry_dt"], u["unit_id"]))

    # Priority queue: (-urgency_weight, timestamp_received, insertion_index, request)
    pq = []
    for idx, req in enumerate(sim_requests):
        if req["qty"] <= 0:
            continue
        heapq.heappush(pq, (-req["weight"], req["ts"], idx, req))

    preview_rows = []
    rank = 1

    while pq:
        _, _, _, req = heapq.heappop(pq)
        req_group = req["blood_group_required"].strip()
        comp = req["component_type"].strip()
        needed = int(req["qty"])
        allocated_units = []
        donors_used = []
        expiry_notes = []
        unit_scores = []

        # Exact match first, followed by compatible donor groups
        donor_candidates = get_compatible_donors(req_group)

        for donor_group in donor_candidates:
            if needed == 0:
                break
            bucket = buckets.get((donor_group, comp), [])
            while bucket and needed > 0:
                unit = bucket.pop(0)
                unit["status"] = "preview_allocated"
                allocated_units.append(unit["unit_id"])
                if donor_group not in donors_used:
                    donors_used.append(donor_group)

                days_left = max(0, (unit["expiry_dt"] - today).days)
                s_score = compute_urgency_score(req["weight"], unit["expiry_dt"], today)
                unit_scores.append(s_score)
                expiry_notes.append(
                    f"{unit['unit_id']} ({donor_group}, exp: {unit['expiry_date']}, {days_left}d, S={s_score})"
                )
                needed -= 1

        allocated_qty = len(allocated_units)
        if allocated_qty == req["qty"]:
            status = "FULFILLED"
        elif allocated_qty > 0:
            status = "PARTIAL_FULFILLMENT"
        else:
            status = "SHORTFALL"

        avg_score = round(sum(unit_scores) / len(unit_scores), 2) if unit_scores else float(req["weight"] * 100)

        preview_rows.append({
            "priority_rank": rank,
            "request_id": req["request_id"],
            "hospital_id": req["hospital_id"],
            "urgency_level": req["urgency_level"],
            "urgency_score": avg_score,
            "blood_group_required": req_group,
            "component_type": comp,
            "required_qty": int(req["qty"]),
            "units_allocated": allocated_qty,
            "donor_group_used": ";".join(donors_used) if donors_used else "NONE",
            "shortfall_qty": needed,
            "expiry_info": "; ".join(expiry_notes) if expiry_notes else "No units available",
            "allocation_status": status,
            "allocated_unit_ids": allocated_units,
            "processing_timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        })
        rank += 1

    return preview_rows


def confirm_dispatch(
    preview_records: list,
    inv_file="inventory.csv",
    req_file="requests.csv",
    hist_file="dispatch_history.csv",
) -> tuple:
    """
    Re-validate live inventory and request states against the preview before
    committing any changes. Prevents duplicate unit allocation, stale previews,
    or dispatching expired/unavailable units.
    Returns (success: bool, message: str, committed_records: list).
    """
    if not preview_records:
        return False, "No preview records found to confirm.", []

    actionable = [r for r in preview_records if int(r.get("units_allocated", 0)) > 0]
    if not actionable:
        return False, "No units are allocated in this preview to dispatch.", []

    all_inventory = load_all_inventory(inv_file)
    all_requests = load_all_requests(req_file)
    today = datetime.now().date()

    inv_map = {u["unit_id"]: u for u in all_inventory}
    req_map = {r["request_id"]: r for r in all_requests}
    seen_units = set()

    # Step 1: Strict re-validation against live CSV state
    for item in actionable:
        req_id = item["request_id"]
        live_req = req_map.get(req_id)
        if not live_req:
            return False, f"Dispatch aborted: Request {req_id} no longer exists.", []
        if live_req["status"] not in ("PENDING", "PARTIAL", "PARTIAL_FULFILLMENT"):
            return False, f"Dispatch aborted: Request {req_id} is no longer active.", []
        if int(item["units_allocated"]) > int(live_req["quantity_required"]):
            return False, f"Dispatch aborted: Preview for {req_id} exceeds remaining needed quantity.", []

        for uid in item.get("allocated_unit_ids", []):
            if uid in seen_units:
                return False, f"Duplicate allocation blocked: Unit {uid} was assigned more than once.", []
            seen_units.add(uid)

            unit = inv_map.get(uid)
            if not unit:
                return False, f"Dispatch aborted: Unit {uid} is missing from inventory.", []
            if unit["status"].strip().lower() != "available":
                return False, f"Dispatch aborted: Unit {uid} is no longer available (status: {unit['status']}).", []
            if unit["expiry_dt"] < today:
                return False, f"Dispatch aborted: Unit {uid} expired on {unit['expiry_date']}.", []

    # Step 2: Commit updates with automatic current date/time
    now = datetime.now()
    date_str = now.strftime("%Y-%m-%d")
    time_str = now.strftime("%H:%M:%S")
    ts_str = now.strftime("%Y-%m-%d %H:%M:%S")

    existing_hist = load_dispatch_history(hist_file)
    existing_ids = [h.get("dispatch_id", "") for h in existing_hist]
    new_history_rows = []
    committed_records = []

    for item in preview_records:
        req_id = item["request_id"]
        live_req = req_map.get(req_id)
        allocated_qty = int(item["units_allocated"])
        unit_ids = item.get("allocated_unit_ids", [])

        if allocated_qty > 0 and live_req:
            for uid in unit_ids:
                inv_map[uid]["status"] = "dispatched"

            remaining_qty = max(0, int(live_req["quantity_required"]) - allocated_qty)
            live_req["quantity_required"] = remaining_qty
            live_req["qty"] = remaining_qty
            live_req["status"] = "FULFILLED" if remaining_qty == 0 else "PARTIAL"

            dsp_id = generate_next_id("DSP", existing_ids, width=4)
            existing_ids.append(dsp_id)
            new_history_rows.append({
                "dispatch_id": dsp_id,
                "date": date_str,
                "time": time_str,
                "timestamp": ts_str,
                "request_id": req_id,
                "hospital": item["hospital_id"],
                "blood_group": item["blood_group_required"],
                "donor_group_used": item["donor_group_used"],
                "component_type": item["component_type"],
                "units_dispatched": allocated_qty,
                "unit_ids": ";".join(unit_ids),
            })

        committed_item = dict(item)
        committed_item["processing_timestamp"] = ts_str
        committed_records.append(committed_item)

    save_inventory(all_inventory, inv_file)
    save_requests(all_requests, req_file)
    append_dispatch_history(new_history_rows, hist_file)

    return (
        True,
        f"Confirmed dispatch of {len(seen_units)} unit(s) at {ts_str}. Partial requests remain pending for remaining units.",
        committed_records,
    )


def allocate_blood(inventory: list, requests: list) -> list:
    """Compatibility wrapper for CLI execution."""
    return preview_allocation(inventory, requests)