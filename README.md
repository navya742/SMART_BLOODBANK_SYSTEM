# 🩸 Smart Blood Bank Allocation System (UN SDG 3)

An automated, priority-based blood bank allocation and inventory management system built with a **pure Python 3 Standard Library core** and an interactive **Streamlit multi-role dashboard**[cite: 1, 8]. Designed to support **UN Sustainable Development Goal 3 (Good Health and Well-Being)** through equitable emergency triage, Earliest-Expiry-First (EEF) wastage minimization, and auditable dispatch workflows.


## ✨ Key Features

### 1. Dual-Role Interactive Web Portal (`stream.py`)
* **🏥 User / Hospital Portal:**
  * **Submit Blood Request:** Submit demand requests specifying blood group, component (`RBC`, `Plasma`, `Platelets`), required quantity, and urgency (`Critical`, `High`, `Moderate`, `Routine`)[cite: 1].
  * **Blood Directory:** View real-time available stock, earliest expiry dates, and component distribution charts[cite: 1].
  * **My Pending Requests:** Track facility-specific requests (`PENDING`, `PARTIAL`, `FULFILLED`) and remaining quantities[cite: 1].
  * **My Blood History:** View confirmed dispatches received by the hospital with automatic dispatch date and time.
* **🛡️ Admin Control Panel:**
  * **Dashboard:** Live KPIs for available units, pending requests, dispatched units, discarded/expired units, and stock/urgency visualizations[cite: 1].
  * **Manage Inventory:** Add donated blood units (auto-generating unique IDs) and update unit availability statuses (`available`, `reserved`, `discarded`)[cite: 1].
  * **Pending Requests:** Inspect all active requests ranked by urgency and arrival timestamp[cite: 1].
  * **Smart Allocation & Allocation Preview:** Simulate priority-based EEF allocation non-destructively, displaying priority rank, Request ID, hospital, requested/donor blood groups, component, required/allocated/shortfall quantities, urgency score S, and unit expiry details[cite: 1, 8].
  * **Confirm Dispatch:** Re-validate live stock at confirmation time to prevent duplicate or stale allocations, mark units as `dispatched`, retain remaining quantities on partially fulfilled requests, and record automatic timestamps[cite: 1].
  * **Dispatch History & Reports:** View full dispatch audit logs and download `dispatch_history.csv` / `dispatch_summary.txt`[cite: 1, 5].

### 2. Smart Allocation Engine (`allocater.py`)[cite: 6]
* **Priority Queue Triage (`heapq`):** Ranks requests by urgency weight (`CRITICAL = 4`, `HIGH = 3`, `MODERATE = 2`, `ROUTINE = 1`) and breaks ties deterministically by earliest `timestamp_received`[cite: 1, 6, 7].
* **Exact-Match First + Compatible Fallback (`compatibility.py`):** Attempts exact blood group matches first before falling back to biologically compatible donor groups[cite: 1, 6].
* **Earliest-Expiry-First (EEF) Rotation:** Selects viable units closest to expiration first while automatically flagging expired units (`expiry_date < today`) as `discarded`[cite: 1, 6, 7].
* **Urgency & Expiry Scoring:** Computes `S = (Urgency Weight * 100) - (Days to Expiry * 2)` for transparency in allocation previews[cite: 8].
* **Partial Fulfillment & Shortfall Tracking:** Allocates available units when full stock is unavailable and keeps remaining demand active in the pending queue[cite: 1, 6].

---

## 📂 Project Structure

```text
SMART_BLOODBANK_SYSTEM/
├── compatibility.py        # ABO/Rh compatibility matrix, blood groups, components & urgency weights
├── loader.py               # Atomic CSV persistence, input validation, expiry filtering & unique ID generators
├── allocater.py            # Priority queue + EEF simulation preview & stock-validated dispatch confirmation
├── reporter.py             # Auditable CSV and TXT dispatch summary report generator
├── stream.py               # Multi-role Streamlit web dashboard (User/Hospital & Admin interfaces)
├── m.py                    # Headless CLI entry point for batch allocation & report generation
├── requirements.txt        # Python dependencies (streamlit, pandas)
├── .gitignore              # Git ignore rules
├── inventory.csv           # Blood unit stock ledger (auto-generated if missing)
├── requests.csv            # Hospital blood demand requests (auto-generated if missing)
├── dispatch_history.csv    # Persisted log of confirmed dispatches with automatic date & time
├── dispatch_summary.csv    # Structured summary output of allocation runs
└── dispatch_summary.txt    # Human-readable audit report
