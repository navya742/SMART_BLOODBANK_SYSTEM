import csv


def build_report_text(dispatch_records: list) -> str:
    """Build a formatted human-readable summary from dispatch records."""
    total_reqs = len(dispatch_records)
    fulfilled = sum(1 for r in dispatch_records if r["allocation_status"] == "FULFILLED")
    partial = sum(1 for r in dispatch_records if r["allocation_status"] == "PARTIAL_FULFILLMENT")
    shortfalls = sum(1 for r in dispatch_records if r["allocation_status"] == "SHORTFALL")
    total_units = sum(int(r["units_allocated"]) for r in dispatch_records)

    lines = [
        "=" * 68,
        "SMART BLOOD BANK ALLOCATION SYSTEM - AUDITABLE DISPATCH SUMMARY",
        "=" * 68,
        f"Total Requests Processed : {total_reqs}",
        f"Fully Fulfilled          : {fulfilled}",
        f"Partially Fulfilled      : {partial}",
        f"Unfulfilled (Shortfall)  : {shortfalls}",
        f"Total Units Dispatched   : {total_units}",
        "-" * 68,
    ]

    for r in dispatch_records:
        lines.append(
            f"{r['request_id']} | {r['hospital_id']:<12} | {r['allocation_status']:<19} | "
            f"Allocated: {r['units_allocated']} | Donors: {r['donor_group_used']:<10} | "
            f"Shortfall: {r['shortfall_qty']}"
        )
    lines.append("=" * 68)
    return "\n".join(lines)


def write_reports(dispatch_records, csv_path="dispatch_summary.csv", txt_path="dispatch_summary.txt"):
    """Write both CSV and TXT audit reports from dispatch records."""
    fieldnames = [
        "request_id",
        "hospital_id",
        "allocation_status",
        "units_allocated",
        "donor_group_used",
        "shortfall_qty",
        "processing_timestamp",
    ]

    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(dispatch_records)

    report_text = build_report_text(dispatch_records)
    with open(txt_path, "w", encoding="utf-8") as f:
        f.write(report_text)

    return report_text