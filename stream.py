import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from compatibility import BLOOD_GROUPS, COMPONENT_TYPES, COMPATIBILITY_MAP
from loader import (
    generate_sample_files,
    load_all_inventory,
    load_inventory,
    save_inventory,
    load_all_requests,
    load_requests,
    load_dispatch_history,
    add_blood_units,
    submit_hospital_request,
)
from allocater import preview_allocation, confirm_dispatch
from reporter import write_reports, build_report_text

# ------------------------------------------------------------------------------
# PAGE SETUP & SAMPLE DATA INITIALIZATION
# ------------------------------------------------------------------------------
st.set_page_config(
    page_title="Smart Blood Bank System | SDG 3",
    page_icon="🩸",
    layout="wide",
    initial_sidebar_state="expanded",
)

generate_sample_files()

if "allocation_preview" not in st.session_state:
    st.session_state["allocation_preview"] = None
if "last_submitted_req" not in st.session_state:
    st.session_state["last_submitted_req"] = None

COMPONENT_COLOR_MAP = {
    "RBC": "#dc2626",
    "Plasma": "#0284c7",
    "Platelets": "#10b981",
}

# ------------------------------------------------------------------------------
# CUSTOM STYLING
# ------------------------------------------------------------------------------
st.markdown(
    """
    <style>
        .user-header {
            background: linear-gradient(120deg, #991b1b 0%, #dc2626 60%, #f43f5e 100%);
            padding: 1.3rem 1.6rem;
            border-radius: 14px;
            color: #ffffff;
            margin-bottom: 1.1rem;
            box-shadow: 0 6px 18px rgba(220, 38, 38, 0.16);
        }
        .admin-header {
            background: linear-gradient(120deg, #0f172a 0%, #1d4ed8 60%, #0ea5e9 100%);
            padding: 1.3rem 1.6rem;
            border-radius: 14px;
            color: #ffffff;
            margin-bottom: 1.1rem;
            box-shadow: 0 6px 18px rgba(14, 165, 233, 0.16);
        }
        .banner-title {
            font-size: 1.7rem;
            font-weight: 800;
            margin: 0;
        }
        .banner-sub {
            font-size: 0.92rem;
            opacity: 0.92;
            margin-top: 0.25rem;
        }
        .metric-box {
            background: #ffffff;
            border-radius: 12px;
            padding: 1rem 1.15rem;
            border-left: 5px solid #dc2626;
            box-shadow: 0 3px 10px rgba(15, 23, 42, 0.06);
            margin-bottom: 0.5rem;
        }
        .metric-box.blue { border-left-color: #0284c7; }
        .metric-box.green { border-left-color: #059669; }
        .metric-box.amber { border-left-color: #d97706; }
        .metric-title {
            font-size: 0.78rem;
            font-weight: 700;
            text-transform: uppercase;
            color: #64748b;
            letter-spacing: 0.04em;
        }
        .metric-num {
            font-size: 1.8rem;
            font-weight: 800;
            color: #0f172a;
        }
        .metric-note {
            font-size: 0.78rem;
            color: #475569;
        }
    </style>
    """,
    unsafe_allow_html=True,
)


def show_metric(title: str, value, note: str = "", color_class: str = ""):
    st.markdown(
        f"""
        <div class="metric-box {color_class}">
            <div class="metric-title">{title}</div>
            <div class="metric-num">{value}</div>
            <div class="metric-note">{note}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def badge_style(val):
    s = str(val).strip().upper()
    palette = {
        "CRITICAL": "background-color: #fee2e2; color: #991b1b; font-weight: 700;",
        "HIGH": "background-color: #ffedd5; color: #9a3412; font-weight: 700;",
        "MODERATE": "background-color: #fef3c7; color: #92400e; font-weight: 600;",
        "ROUTINE": "background-color: #e0f2fe; color: #075985; font-weight: 600;",
        "FULFILLED": "background-color: #dcfce7; color: #166534; font-weight: 700;",
        "AVAILABLE": "background-color: #dcfce7; color: #166534; font-weight: 700;",
        "PARTIAL": "background-color: #fef3c7; color: #92400e; font-weight: 700;",
        "PARTIAL_FULFILLMENT": "background-color: #fef3c7; color: #92400e; font-weight: 700;",
        "PENDING": "background-color: #e0e7ff; color: #3730a3; font-weight: 700;",
        "SHORTFALL": "background-color: #ffe4e6; color: #9f1239; font-weight: 700;",
        "DISPATCHED": "background-color: #dbeafe; color: #1e40af; font-weight: 600;",
        "RESERVED": "background-color: #fae8ff; color: #86198f; font-weight: 600;",
        "DISCARDED": "background-color: #f1f5f9; color: #475569; font-weight: 600;",
    }
    return palette.get(s, "")


def colorize_df(df: pd.DataFrame, cols: list):
    present = [c for c in cols if c in df.columns]
    if not present:
        return df
    return df.style.map(badge_style, subset=present)


def get_chart_colors(columns) -> list:
    return [COMPONENT_COLOR_MAP.get(col, "#6366f1") for col in columns]


# ------------------------------------------------------------------------------
# USER / HOSPITAL PORTAL (SEPARATE MENU & INTERFACE)
# ------------------------------------------------------------------------------
def render_user_portal():
    all_reqs = load_all_requests()
    valid_inv = load_inventory()
    history = load_dispatch_history()

    known_hospitals = sorted(
        list({r["hospital_id"] for r in all_reqs} | {"HOSP_AIIMS", "HOSP_MAX", "HOSP_FORTIS", "HOSP_APOLLO", "HOSP_JIPMER"})
    )

    with st.sidebar:
        st.markdown("### 🏥 User / Hospital Menu")
        selected_hosp = st.selectbox("Select Hospital", known_hospitals + ["Other (Enter ID)"])
        if selected_hosp == "Other (Enter ID)":
            hospital_id = st.text_input("Enter Hospital ID", value="HOSP_CITY").strip().upper()
        else:
            hospital_id = selected_hosp

        if not hospital_id:
            st.error("Please enter a valid Hospital ID.")
            return

        st.success(f"Active Hospital: **{hospital_id}**")
        st.divider()
        user_menu = st.radio(
            "Hospital Sections",
            [
                "Submit Blood Request",
                "Blood Directory",
                "My Pending Requests",
                "My Blood History",
            ],
            key="user_menu_nav",
        )

    st.markdown(
        f"""
        <div class="user-header">
            <div class="banner-title">🩸 Hospital / User Portal — {hospital_id}</div>
            <div class="banner-sub">Submit Blood Demand Requests &nbsp;|&nbsp; Browse Available Stock &nbsp;|&nbsp; Track Requests & Dispatch History</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    last_req = st.session_state.get("last_submitted_req")
    if last_req and last_req.get("hospital_id") == hospital_id:
        st.success(
            f"Request **{last_req['request_id']}** submitted for **{last_req['quantity_required']} unit(s)** "
            f"of **{last_req['blood_group_required']} ({last_req['component_type']})** — Urgency: **{last_req['urgency_level']}**."
        )

    # 1. Submit Blood Request (User Demand Input)
    if user_menu == "Submit Blood Request":
        st.subheader("Submit Blood Demand Request")
        col_form, col_info = st.columns([3, 2], gap="large")

        with col_form:
            with st.form("user_demand_request_form", clear_on_submit=True):
                c1, c2 = st.columns(2)
                with c1:
                    req_bg = st.selectbox("Required Blood Group", BLOOD_GROUPS)
                    req_qty = st.number_input("Required Quantity (Units)", min_value=1, max_value=100, value=1, step=1)
                with c2:
                    req_comp = st.selectbox("Blood Component", COMPONENT_TYPES)
                    req_urgency = st.selectbox("Urgency", ["Critical", "High", "Moderate", "Routine"])

                exact_stock = sum(
                    1 for u in valid_inv
                    if u["full_group"] == req_bg and u["component_type"] == req_comp
                )
                st.caption(f"Exact-match available stock for {req_bg} ({req_comp}): **{exact_stock} unit(s)**")

                if st.form_submit_button("Submit Demand Request", type="primary", use_container_width=True):
                    try:
                        created = submit_hospital_request(
                            hospital_id=hospital_id,
                            blood_group_required=req_bg,
                            component_type=req_comp,
                            quantity_required=int(req_qty),
                            urgency_level=req_urgency,
                        )
                        st.session_state["last_submitted_req"] = created
                        st.session_state["allocation_preview"] = None
                        st.rerun()
                    except ValueError as exc:
                        st.error(str(exc))

        with col_info:
            st.markdown("#### Priority & Matching Rules")
            st.info(
                "- **Critical = 4** | **High = 3** | **Moderate = 2** | **Routine = 1**\n"
                "- Ties with equal urgency are ordered by **earlier timestamp**.\n"
                "- Exact blood group matches are checked first, followed by compatible donor groups.\n"
                "- Units with the **earliest expiry date** are chosen first."
            )

    # 2. Blood Directory
    elif user_menu == "Blood Directory":
        st.subheader("Blood Directory")
        if not valid_inv:
            st.info("No available blood stock right now.")
            return

        df_inv = pd.DataFrame(valid_inv)
        m1, m2, m3 = st.columns(3)
        with m1:
            show_metric("Available Units", len(df_inv), "Ready for dispatch", "green")
        with m2:
            show_metric("Blood Groups Available", df_inv["full_group"].nunique(), "ABO + Rh combinations", "blue")
        with m3:
            show_metric("Component Types", df_inv["component_type"].nunique(), "RBC / Plasma / Platelets", "amber")

        f1, f2 = st.columns(2)
        with f1:
            sel_bg = st.multiselect("Filter by Blood Group", BLOOD_GROUPS, default=[])
        with f2:
            sel_comp = st.multiselect("Filter by Component", COMPONENT_TYPES, default=[])

        filtered = df_inv.copy()
        if sel_bg:
            filtered = filtered[filtered["full_group"].isin(sel_bg)]
        if sel_comp:
            filtered = filtered[filtered["component_type"].isin(sel_comp)]

        summary = (
            filtered.groupby(["full_group", "component_type"], as_index=False)
            .agg(available_qty=("unit_id", "count"), earliest_expiry=("expiry_date", "min"))
            .rename(
                columns={
                    "full_group": "Blood Group",
                    "component_type": "Component Type",
                    "available_qty": "Available Quantity",
                    "earliest_expiry": "Earliest Expiry",
                }
            )
        )

        left, right = st.columns([3, 2], gap="large")
        with left:
            st.dataframe(summary, use_container_width=True, hide_index=True)
        with right:
            if not summary.empty:
                chart_data = summary.pivot(
                    index="Blood Group", columns="Component Type", values="Available Quantity"
                ).fillna(0)
                st.bar_chart(chart_data, color=get_chart_colors(chart_data.columns))

    # 3. My Pending Requests
    elif user_menu == "My Pending Requests":
        st.subheader(f"My Pending Requests — {hospital_id}")
        my_reqs = [r for r in all_reqs if r["hospital_id"] == hospital_id]
        if not my_reqs:
            st.info("No requests submitted by your hospital yet.")
            return

        rows = [
            {
                "Request ID": r["request_id"],
                "Blood Group": r["blood_group_required"],
                "Component Type": r["component_type"],
                "Original Qty": r["original_quantity"],
                "Remaining Qty": r["quantity_required"],
                "Urgency": r["urgency_level"],
                "Submitted At": r["timestamp_received"],
                "Status": r["status"],
            }
            for r in my_reqs
        ]
        st.dataframe(colorize_df(pd.DataFrame(rows), ["Urgency", "Status"]), use_container_width=True, hide_index=True)

    # 4. My Blood History
    elif user_menu == "My Blood History":
        st.subheader(f"My Blood History — {hospital_id}")
        my_hist = [h for h in history if h.get("hospital") == hospital_id]
        if not my_hist:
            st.info("No fulfilled/dispatched blood records for your hospital yet.")
            return

        df_h = pd.DataFrame(my_hist)[
            ["date", "time", "hospital", "blood_group", "units_dispatched", "donor_group_used", "component_type", "request_id"]
        ].rename(
            columns={
                "date": "Date",
                "time": "Time",
                "hospital": "Hospital",
                "blood_group": "Blood Group",
                "units_dispatched": "Units Dispatched",
                "donor_group_used": "Donor Group Used",
                "component_type": "Component Type",
                "request_id": "Request ID",
            }
        )
        st.dataframe(df_h, use_container_width=True, hide_index=True)


# ------------------------------------------------------------------------------
# ADMIN PORTAL (SEPARATE 8-SECTION MENU & INTERFACE)
# ------------------------------------------------------------------------------
def render_admin_portal():
    with st.sidebar:
        st.markdown("### 🛡️ Admin Menu")
        admin_menu = st.radio(
            "Admin Sections",
            [
                "Dashboard",
                "Manage Inventory",
                "Pending Requests",
                "Smart Allocation",
                "Allocation Preview",
                "Confirm Dispatch",
                "Dispatch History",
                "Reports",
            ],
            key="admin_menu_nav",
        )

    st.markdown(
        """
        <div class="admin-header">
            <div class="banner-title">🛡️ Admin Operations & Smart Allocation Console</div>
            <div class="banner-sub">Inventory Management &nbsp;|&nbsp; Priority Queue + EEF Allocation &nbsp;|&nbsp; Preview & Dispatch Verification</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    all_inv = load_all_inventory()
    avail_inv = [u for u in all_inv if u["status"] == "available"]
    pending_reqs = load_requests()
    history = load_dispatch_history()

    # 1. Dashboard
    if admin_menu == "Dashboard":
        st.subheader("Admin Dashboard")
        dispatched_total = sum(int(h.get("units_dispatched", 0)) for h in history)
        discarded_total = sum(1 for u in all_inv if u["status"] == "discarded")

        c1, c2, c3, c4 = st.columns(4)
        with c1:
            show_metric("Available Units", len(avail_inv), "Unexpired & ready", "green")
        with c2:
            show_metric("Pending Requests", len(pending_reqs), "In priority queue", "amber")
        with c3:
            show_metric("Units Dispatched", dispatched_total, "Confirmed dispatches", "blue")
        with c4:
            show_metric("Discarded / Expired", discarded_total, "Expired or marked discarded", "")

        g1, g2 = st.columns([3, 2], gap="large")
        with g1:
            st.markdown("#### Available Stock by Blood Group & Component")
            if avail_inv:
                inv_df = pd.DataFrame(avail_inv)
                piv = inv_df.groupby(["full_group", "component_type"])["unit_id"].count().unstack(fill_value=0)
                st.bar_chart(piv, color=get_chart_colors(piv.columns))
            else:
                st.info("No available blood units.")

        with g2:
            st.markdown("#### Pending Demand by Urgency")
            if pending_reqs:
                urg_df = (
                    pd.DataFrame(pending_reqs)
                    .groupby("urgency_level")["quantity_required"]
                    .sum()
                    .reset_index()
                    .rename(columns={"urgency_level": "Urgency", "quantity_required": "Units Needed"})
                )
                st.bar_chart(urg_df.set_index("Urgency"), color="#f59e0b")
            else:
                st.info("No pending requests.")

    # 2. Manage Inventory
    elif admin_menu == "Manage Inventory":
        st.subheader("Manage Inventory")
        with st.expander("Add Donated Blood Units", expanded=True):
            with st.form("admin_add_units_form", clear_on_submit=True):
                c1, c2, c3 = st.columns(3)
                with c1:
                    bg = st.selectbox("Blood Group", BLOOD_GROUPS)
                    comp = st.selectbox("Component Type", COMPONENT_TYPES)
                with c2:
                    col_dt = st.date_input("Collection Date", value=datetime.now().date())
                    exp_dt = st.date_input("Expiry Date", value=datetime.now().date() + timedelta(days=35))
                with c3:
                    qty = st.number_input("Quantity", min_value=1, max_value=100, value=1, step=1)
                    vol = st.number_input("Volume (mL)", min_value=50, max_value=500, value=450, step=50)
                    status = st.selectbox("Availability Status", ["available", "reserved"])

                if st.form_submit_button("Add Blood Units", type="primary"):
                    try:
                        added = add_blood_units(
                            blood_group_full=bg,
                            component_type=comp,
                            collection_date=col_dt.strftime("%Y-%m-%d"),
                            expiry_date=exp_dt.strftime("%Y-%m-%d"),
                            quantity=int(qty),
                            volume_ml=int(vol),
                            status=status,
                        )
                        st.session_state["allocation_preview"] = None
                        st.success(f"Added {len(added)} unit(s): {', '.join(u['unit_id'] for u in added)}.")
                        st.rerun()
                    except ValueError as exc:
                        st.error(str(exc))

        if all_inv:
            editable = [u for u in all_inv if u["status"] != "dispatched"]
            if editable:
                st.markdown("#### Update Unit Status")
                u1, u2, u3 = st.columns([2, 2, 1])
                with u1:
                    choice = st.selectbox(
                        "Select Unit",
                        [f"{u['unit_id']} | {u['full_group']} {u['component_type']} | {u['status']}" for u in editable],
                    )
                    uid = choice.split(" | ")[0]
                with u2:
                    new_status = st.selectbox("New Availability Status", ["available", "reserved", "discarded"])
                with u3:
                    st.write("")
                    st.write("")
                    if st.button("Update Status", use_container_width=True):
                        for u in all_inv:
                            if u["unit_id"] == uid:
                                u["status"] = new_status
                        save_inventory(all_inv)
                        st.session_state["allocation_preview"] = None
                        st.success(f"Updated unit {uid} to '{new_status}'.")
                        st.rerun()

            st.markdown("#### Inventory Table")
            inv_df = pd.DataFrame(all_inv)[
                ["unit_id", "full_group", "component_type", "collection_date", "expiry_date", "volume_ml", "status"]
            ].rename(columns={"full_group": "blood_group"})
            st.dataframe(colorize_df(inv_df, ["status"]), use_container_width=True, hide_index=True)

    # 3. Pending Requests
    elif admin_menu == "Pending Requests":
        st.subheader("Pending Requests")
        if not pending_reqs:
            st.info("No pending requests.")
            return
        ordered = sorted(pending_reqs, key=lambda r: (-r["weight"], r["ts"]))
        df_req = pd.DataFrame(ordered)[
            ["request_id", "hospital_id", "blood_group_required", "component_type", "quantity_required", "urgency_level", "timestamp_received", "status"]
        ]
        st.dataframe(colorize_df(df_req, ["urgency_level", "status"]), use_container_width=True, hide_index=True)

    # 4. Smart Allocation
    elif admin_menu == "Smart Allocation":
        st.subheader("Smart Allocation")
        st.write(
            "Ranks pending requests by urgency (**Critical = 4, High = 3, Moderate = 2, Routine = 1**) and earlier arrival timestamp, "
            "allocates exact blood group first, falls back to compatible donor groups, and selects **Earliest-Expiry-First (EEF)** units."
        )
        with st.expander("Compatibility Rules"):
            comp_df = [{"Recipient": k, "Compatible Donors": ", ".join(v)} for k, v in COMPATIBILITY_MAP.items()]
            st.dataframe(pd.DataFrame(comp_df), use_container_width=True, hide_index=True)

        if not pending_reqs:
            st.info("No pending requests available to process.")
        elif st.button("Generate Allocation Preview", type="primary"):
            preview = preview_allocation(avail_inv, pending_reqs)
            st.session_state["allocation_preview"] = preview
            st.success("Allocation preview generated! Go to **Allocation Preview** or **Confirm Dispatch** to inspect and confirm.")

    # 5. Allocation Preview
    elif admin_menu == "Allocation Preview":
        st.subheader("Allocation Preview")
        preview = st.session_state.get("allocation_preview")
        if not preview:
            st.info("No active preview. Run **Smart Allocation** first.")
            return

        preview_cols = [
            "priority_rank",
            "request_id",
            "hospital_id",
            "blood_group_required",
            "component_type",
            "required_qty",
            "units_allocated",
            "donor_group_used",
            "shortfall_qty",
            "expiry_info",
        ]
        if "urgency_score" in preview[0]:
            preview_cols.insert(5, "urgency_score")

        df_prev = pd.DataFrame(preview)[preview_cols].rename(
            columns={
                "priority_rank": "Processing Priority/Rank",
                "request_id": "Request ID",
                "hospital_id": "Hospital Name",
                "blood_group_required": "Requested Blood Group",
                "component_type": "Component Type",
                "urgency_score": "Score S",
                "required_qty": "Required Quantity",
                "units_allocated": "Allocated Quantity",
                "donor_group_used": "Donor Blood Group Used",
                "shortfall_qty": "Shortfall Quantity",
                "expiry_info": "Expiry Information of Selected Units",
            }
        )
        st.dataframe(df_prev, use_container_width=True, hide_index=True)

        if st.button("Cancel Preview"):
            st.session_state["allocation_preview"] = None
            st.warning("Preview cancelled. Inventory and pending requests were not modified.")
            st.rerun()

    # 6. Confirm Dispatch
    elif admin_menu == "Confirm Dispatch":
        st.subheader("Confirm Dispatch")
        preview = st.session_state.get("allocation_preview")
        if not preview:
            st.info("No active preview to confirm.")
            return

        preview_cols = [
            "priority_rank",
            "request_id",
            "hospital_id",
            "blood_group_required",
            "component_type",
            "required_qty",
            "units_allocated",
            "donor_group_used",
            "shortfall_qty",
            "expiry_info",
        ]
        if "urgency_score" in preview[0]:
            preview_cols.insert(5, "urgency_score")

        df_prev = pd.DataFrame(preview)[preview_cols].rename(
            columns={
                "priority_rank": "Processing Priority/Rank",
                "request_id": "Request ID",
                "hospital_id": "Hospital Name",
                "blood_group_required": "Requested Blood Group",
                "component_type": "Component Type",
                "urgency_score": "Score S",
                "required_qty": "Required Quantity",
                "units_allocated": "Allocated Quantity",
                "donor_group_used": "Donor Blood Group Used",
                "shortfall_qty": "Shortfall Quantity",
                "expiry_info": "Expiry Information of Selected Units",
            }
        )
        st.dataframe(df_prev, use_container_width=True, hide_index=True)

        b1, b2 = st.columns([1, 5])
        with b1:
            if st.button("Confirm Dispatch", type="primary", use_container_width=True):
                ok, msg, committed = confirm_dispatch(preview)
                if ok:
                    write_reports(committed)
                    st.session_state["allocation_preview"] = None
                    st.success(msg)
                else:
                    st.error(msg)
        with b2:
            if st.button("Cancel Preview"):
                st.session_state["allocation_preview"] = None
                st.warning("Preview cancelled. No changes were saved.")
                st.rerun()

    # 7. Dispatch History
    elif admin_menu == "Dispatch History":
        st.subheader("Dispatch History")
        if not history:
            st.info("No dispatches have been confirmed yet.")
            return

        df_h = pd.DataFrame(history)[
            ["date", "time", "hospital", "blood_group", "units_dispatched", "donor_group_used", "component_type", "request_id"]
        ].rename(
            columns={
                "date": "Date",
                "time": "Time",
                "hospital": "Hospital",
                "blood_group": "Blood Group",
                "units_dispatched": "Units Dispatched",
                "donor_group_used": "Donor Group Used",
                "component_type": "Component Type",
                "request_id": "Request ID",
            }
        )
        st.dataframe(df_h, use_container_width=True, hide_index=True)

    # 8. Reports
    elif admin_menu == "Reports":
        st.subheader("Reports")
        preview = st.session_state.get("allocation_preview")
        if preview:
            st.markdown("#### Current Allocation Preview Summary")
            st.code(build_report_text(preview), language="text")

        if history:
            st.markdown("#### Confirmed Dispatch History")
            df_h = pd.DataFrame(history)
            st.dataframe(df_h, use_container_width=True, hide_index=True)
            st.download_button(
                "Download Dispatch History (CSV)",
                data=df_h.to_csv(index=False),
                file_name="dispatch_history.csv",
                mime="text/csv",
                type="primary",
            )
        elif not preview:
            st.info("No dispatch data available for reports yet.")


with st.sidebar:
    st.markdown("## 🩸 Smart Blood Bank")
    interface_role = st.radio("Select Interface", ["User / Hospital", "Admin"], key="interface_switcher")
    st.divider()

if interface_role == "User / Hospital":
    render_user_portal()
else:
    render_admin_portal()