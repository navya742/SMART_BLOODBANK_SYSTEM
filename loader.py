import csv
import os
from datetime import datetime, timedelta
from compatibility import URGENCY_WEIGHTS, BLOOD_GROUPS, COMPONENT_TYPES

INVENTORY_FIELDS = [
    "unit_id",
    "blood_group",
    "rh_factor",
    "component_type",
    "collection_date",
    "expiry_date",
    "volume_ml",
    "status",
]

REQUEST_FIELDS = [
    "request_id",
    "hospital_id",
    "blood_group_required",
    "component_type",
    "quantity_required",
    "original_quantity",
    "urgency_level",
    "timestamp_received",
    "status",
]

DISPATCH_HISTORY_FIELDS = [
    "dispatch_id",
    "date",
    "time",
    "timestamp",
    "request_id",
    "hospital",
    "blood_group",
    "donor_group_used",
    "component_type",
    "units_dispatched",
    "unit_ids",
]

VALID_UNIT_STATUSES = {"available", "reserved", "dispatched", "discarded"}
VALID_URGENCIES = {"CRITICAL", "HIGH", "MODERATE", "ROUTINE"}


def atomic_write_csv(filepath: str, fieldnames: list, rows: list, mode: str = "w"):
    """Write CSV safely via a temporary file on overwrite to avoid partial/corrupt files."""
    if mode == "a" and os.path.exists(filepath):
        with open(filepath, "a", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
            writer.writerows(rows)
        return

    tmp_path = f"{filepath}.tmp"
    with open(tmp_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    os.replace(tmp_path, filepath)


def parse_blood_group(full_group: str) -> tuple:
    """Parse 'AB+' or 'O-' into ('AB', '+') or ('O', '-')."""
    clean = str(full_group).strip().upper()
    if clean not in BLOOD_GROUPS:
        raise ValueError(f"Unsupported blood group: {full_group}")
    return clean[:-1], clean[-1]


def generate_next_id(prefix: str, existing_ids: list, width: int = 3) -> str:
    """Generate a unique sequential ID that never collides with existing IDs."""
    existing_set = {str(x).strip() for x in existing_ids if x}
    max_num = 0
    for item_id in existing_set:
        if item_id.startswith(prefix):
            suffix = item_id[len(prefix):]
            if suffix.isdigit():
                max_num = max(max_num, int(suffix))
    candidate_num = max_num + 1
    while True:
        candidate = f"{prefix}{str(candidate_num).zfill(width)}"
        if candidate not in existing_set:
            return candidate
        candidate_num += 1


def generate_sample_files(
    inv_file="inventory.csv",
    req_file="requests.csv",
    hist_file="dispatch_history.csv",
):
    """Create initial sample CSV files only if they do not already exist."""
    today = datetime.now().date()
    try:
        if not os.path.exists(inv_file):
            inv_rows = [
                {
                    "unit_id": "U101", "blood_group": "O", "rh_factor": "-", "component_type": "RBC",
                    "collection_date": str(today - timedelta(days=20)), "expiry_date": str(today + timedelta(days=2)),
                    "volume_ml": "450", "status": "available",
                },
                {
                    "unit_id": "U102", "blood_group": "O", "rh_factor": "-", "component_type": "RBC",
                    "collection_date": str(today - timedelta(days=10)), "expiry_date": str(today + timedelta(days=15)),
                    "volume_ml": "450", "status": "available",
                },
                {
                    "unit_id": "U103", "blood_group": "A", "rh_factor": "+", "component_type": "RBC",
                    "collection_date": str(today - timedelta(days=15)), "expiry_date": str(today + timedelta(days=5)),
                    "volume_ml": "450", "status": "available",
                },
                {
                    "unit_id": "U104", "blood_group": "A", "rh_factor": "+", "component_type": "RBC",
                    "collection_date": str(today - timedelta(days=30)), "expiry_date": str(today - timedelta(days=1)),
                    "volume_ml": "450", "status": "available",
                },
                {
                    "unit_id": "U105", "blood_group": "B", "rh_factor": "+", "component_type": "Plasma",
                    "collection_date": str(today - timedelta(days=5)), "expiry_date": str(today + timedelta(days=30)),
                    "volume_ml": "250", "status": "available",
                },
                {
                    "unit_id": "U106", "blood_group": "AB", "rh_factor": "+", "component_type": "RBC",
                    "collection_date": str(today - timedelta(days=12)), "expiry_date": str(today + timedelta(days=8)),
                    "volume_ml": "450", "status": "available",
                },
                {
                    "unit_id": "U107", "blood_group": "O", "rh_factor": "+", "component_type": "RBC",
                    "collection_date": str(today - timedelta(days=18)), "expiry_date": str(today + timedelta(days=3)),
                    "volume_ml": "450", "status": "available",
                },
                {
                    "unit_id": "U108", "blood_group": "B", "rh_factor": "-", "component_type": "Platelets",
                    "collection_date": str(today - timedelta(days=2)), "expiry_date": str(today + timedelta(days=3)),
                    "volume_ml": "200", "status": "available",
                },
            ]
            atomic_write_csv(inv_file, INVENTORY_FIELDS, inv_rows, mode="w")

        if not os.path.exists(req_file):
            req_rows = [
                {
                    "request_id": "REQ01", "hospital_id": "HOSP_AIIMS", "blood_group_required": "A+",
                    "component_type": "RBC", "quantity_required": "2", "original_quantity": "2",
                    "urgency_level": "ROUTINE", "timestamp_received": "2026-11-22 08:15:00", "status": "PENDING",
                },
                {
                    "request_id": "REQ02", "hospital_id": "HOSP_MAX", "blood_group_required": "A+",
                    "component_type": "RBC", "quantity_required": "2", "original_quantity": "2",
                    "urgency_level": "CRITICAL", "timestamp_received": "2026-11-22 09:00:00", "status": "PENDING",
                },
                {
                    "request_id": "REQ03", "hospital_id": "HOSP_FORTIS", "blood_group_required": "AB+",
                    "component_type": "RBC", "quantity_required": "3", "original_quantity": "3",
                    "urgency_level": "HIGH", "timestamp_received": "2026-11-22 08:45:00", "status": "PENDING",
                },
                {
                    "request_id": "REQ04", "hospital_id": "HOSP_APOLLO", "blood_group_required": "B+",
                    "component_type": "Plasma", "quantity_required": "1", "original_quantity": "1",
                    "urgency_level": "MODERATE", "timestamp_received": "2026-11-22 09:30:00", "status": "PENDING",
                },
                {
                    "request_id": "REQ05", "hospital_id": "HOSP_JIPMER", "blood_group_required": "O-",
                    "component_type": "RBC", "quantity_required": "3", "original_quantity": "3",
                    "urgency_level": "CRITICAL", "timestamp_received": "2026-11-22 08:30:00", "status": "PENDING",
                },
            ]
            atomic_write_csv(req_file, REQUEST_FIELDS, req_rows, mode="w")

        if not os.path.exists(hist_file):
            atomic_write_csv(hist_file, DISPATCH_HISTORY_FIELDS, [], mode="w")
    except OSError as exc:
        raise RuntimeError(f"Failed initializing CSV files: {exc}") from exc


def load_all_inventory(filepath="inventory.csv") -> list:
    """Load inventory and automatically mark expired available units as 'discarded'."""
    if not os.path.exists(filepath):
        return []
    today = datetime.now().date()
    rows = []
    status_updated = False

    try:
        with open(filepath, "r", newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                try:
                    expiry = datetime.strptime(row["expiry_date"].strip(), "%Y-%m-%d").date()
                    status = row["status"].strip().lower()
                    if status not in VALID_UNIT_STATUSES:
                        status = "discarded"
                    if status == "available" and expiry < today:
                        status = "discarded"
                        status_updated = True
                    row["status"] = status
                    row["blood_group"] = row["blood_group"].strip().upper()
                    row["rh_factor"] = row["rh_factor"].strip()
                    row["component_type"] = row["component_type"].strip()
                    row["expiry_date"] = expiry.strftime("%Y-%m-%d")
                    row["full_group"] = f"{row['blood_group']}{row['rh_factor']}"
                    row["expiry_dt"] = expiry
                    rows.append(row)
                except (KeyError, ValueError):
                    continue
    except OSError:
        return []

    if status_updated:
        save_inventory(rows, filepath)
    return rows


def save_inventory(rows: list, filepath="inventory.csv"):
    atomic_write_csv(filepath, INVENTORY_FIELDS, rows, mode="w")


def load_inventory(filepath="inventory.csv") -> list:
    """Return only valid, non-expired, available units."""
    today = datetime.now().date()
    return [
        u for u in load_all_inventory(filepath)
        if u["status"] == "available" and u["expiry_dt"] >= today
    ]


def load_all_requests(filepath="requests.csv") -> list:
    """Load all hospital requests safely with urgency weight and parsed timestamp."""
    if not os.path.exists(filepath):
        return []
    requests = []
    try:
        with open(filepath, "r", newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                try:
                    urgency_str = row["urgency_level"].strip().upper()
                    if urgency_str not in URGENCY_WEIGHTS:
                        urgency_str = "ROUTINE"
                    qty = int(row["quantity_required"])
                    orig_qty = int(row.get("original_quantity") or qty)
                    raw_status = (row.get("status") or ("FULFILLED" if qty == 0 else "PENDING")).strip().upper()
                    ts = datetime.strptime(row["timestamp_received"].strip(), "%Y-%m-%d %H:%M:%S")

                    row["request_id"] = row["request_id"].strip()
                    row["hospital_id"] = row["hospital_id"].strip().upper()
                    row["blood_group_required"] = row["blood_group_required"].strip().upper()
                    row["component_type"] = row["component_type"].strip()
                    row["urgency_level"] = urgency_str
                    row["original_quantity"] = max(orig_qty, qty)
                    row["quantity_required"] = max(0, qty)
                    row["status"] = "FULFILLED" if qty == 0 else raw_status
                    row["timestamp_received"] = ts.strftime("%Y-%m-%d %H:%M:%S")
                    row["weight"] = URGENCY_WEIGHTS[urgency_str]
                    row["qty"] = row["quantity_required"]
                    row["ts"] = ts
                    requests.append(row)
                except (KeyError, ValueError):
                    continue
    except OSError:
        return []
    return requests


def save_requests(rows: list, filepath="requests.csv"):
    atomic_write_csv(filepath, REQUEST_FIELDS, rows, mode="w")


def load_requests(filepath="requests.csv") -> list:
    """Return only active pending or partially fulfilled requests with remaining qty > 0."""
    return [
        r for r in load_all_requests(filepath)
        if r["status"] in ("PENDING", "PARTIAL", "PARTIAL_FULFILLMENT") and r["qty"] > 0
    ]


def load_dispatch_history(filepath="dispatch_history.csv") -> list:
    if not os.path.exists(filepath):
        return []
    try:
        with open(filepath, "r", newline="", encoding="utf-8") as f:
            return list(csv.DictReader(f))
    except OSError:
        return []


def append_dispatch_history(entries: list, filepath="dispatch_history.csv"):
    if not entries:
        return
    if not os.path.exists(filepath):
        atomic_write_csv(filepath, DISPATCH_HISTORY_FIELDS, entries, mode="w")
    else:
        atomic_write_csv(filepath, DISPATCH_HISTORY_FIELDS, entries, mode="a")


def add_blood_units(
    blood_group_full: str,
    component_type: str,
    collection_date: str,
    expiry_date: str,
    quantity: int,
    volume_ml: int = 450,
    status: str = "available",
    filepath="inventory.csv",
) -> list:
    """Validate inputs and append new donated blood units with unique IDs."""
    if blood_group_full not in BLOOD_GROUPS:
        raise ValueError("Invalid blood group selected.")
    if component_type not in COMPONENT_TYPES:
        raise ValueError("Invalid component type selected.")
    if int(quantity) <= 0 or int(volume_ml) <= 0:
        raise ValueError("Quantity and volume must be positive integers.")

    col_dt = datetime.strptime(str(collection_date), "%Y-%m-%d").date()
    exp_dt = datetime.strptime(str(expiry_date), "%Y-%m-%d").date()
    if exp_dt < col_dt:
        raise ValueError("Expiry date cannot be earlier than collection date.")

    clean_status = status.strip().lower()
    if clean_status not in VALID_UNIT_STATUSES or clean_status == "dispatched":
        raise ValueError("Invalid initial unit status.")

    rows = load_all_inventory(filepath)
    bg, rh = parse_blood_group(blood_group_full)
    existing_ids = [u["unit_id"] for u in rows]
    added = []

    for _ in range(int(quantity)):
        new_id = generate_next_id("U", existing_ids, width=3)
        existing_ids.append(new_id)
        record = {
            "unit_id": new_id,
            "blood_group": bg,
            "rh_factor": rh,
            "component_type": component_type.strip(),
            "collection_date": col_dt.strftime("%Y-%m-%d"),
            "expiry_date": exp_dt.strftime("%Y-%m-%d"),
            "volume_ml": str(int(volume_ml)),
            "status": clean_status,
        }
        rows.append(record)
        added.append(record)

    save_inventory(rows, filepath)
    return added


def submit_hospital_request(
    hospital_id: str,
    blood_group_required: str,
    component_type: str,
    quantity_required: int,
    urgency_level: str,
    filepath="requests.csv",
) -> dict:
    """Validate and save a new hospital demand request."""
    clean_hosp = str(hospital_id).strip().upper()
    if not clean_hosp:
        raise ValueError("Hospital ID cannot be empty.")
    if blood_group_required not in BLOOD_GROUPS:
        raise ValueError("Invalid blood group.")
    if component_type not in COMPONENT_TYPES:
        raise ValueError("Invalid component type.")
    if int(quantity_required) <= 0:
        raise ValueError("Required quantity must be at least 1.")

    clean_urgency = str(urgency_level).strip().upper()
    if clean_urgency not in VALID_URGENCIES:
        raise ValueError("Invalid urgency level.")

    rows = load_all_requests(filepath)
    existing_ids = [r["request_id"] for r in rows]
    new_id = generate_next_id("REQ", existing_ids, width=2)
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    new_req = {
        "request_id": new_id,
        "hospital_id": clean_hosp,
        "blood_group_required": blood_group_required.strip(),
        "component_type": component_type.strip(),
        "quantity_required": int(quantity_required),
        "original_quantity": int(quantity_required),
        "urgency_level": clean_urgency,
        "timestamp_received": now_str,
        "status": "PENDING",
    }
    rows.append(new_req)
    save_requests(rows, filepath)
    return new_req