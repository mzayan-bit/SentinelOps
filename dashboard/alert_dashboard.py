"""
SentinelOps — Alert Investigation Dashboard
==============================================
Streamlit dashboard for browsing, filtering, and investigating
security alerts.

Usage::

    streamlit run dashboard/alert_dashboard.py
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

# ---------------------------------------------------------------------------
# Add project root to path so imports work when run via `streamlit run`
# ---------------------------------------------------------------------------
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from app.models.alert import AlertStatus, AlertType, Severity
from app.services.alert_service import AlertService

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
SEVERITY_COLORS: dict[str, str] = {
    "Low": "#10b981",
    "Medium": "#f59e0b",
    "High": "#f97316",
    "Critical": "#ef4444",
}

STATUS_COLORS: dict[str, str] = {
    "New": "#6366f1",
    "Investigating": "#f59e0b",
    "Confirmed": "#ef4444",
    "False Positive": "#94a3b8",
    "Resolved": "#10b981",
}

COLOR_PALETTE = [
    "#6366f1", "#f43f5e", "#10b981", "#f59e0b",
    "#3b82f6", "#8b5cf6", "#ec4899", "#14b8a6",
]


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------
@st.cache_data(ttl=5)
def load_alerts() -> list[dict[str, Any]]:
    """Load all alerts from the service and return as dicts."""
    service = AlertService()
    alerts = service.list_alerts()
    return [a.to_dict() for a in alerts]


def _generate_demo_alerts() -> None:
    """Seed a handful of demo alerts for first-run experience."""
    from app.models.alert import AlertCreate

    service = AlertService()
    if service.stats().total > 0:
        return

    demos = [
        AlertCreate(
            camera_id="CAM-01", alert_type=AlertType.NO_HELMET,
            severity=Severity.HIGH, confidence=0.92,
            notes="Worker near scaffolding without head protection.",
        ),
        AlertCreate(
            camera_id="CAM-02", alert_type=AlertType.NO_VEST,
            severity=Severity.MEDIUM, confidence=0.87,
            notes="Person in loading dock area without reflective vest.",
        ),
        AlertCreate(
            camera_id="CAM-03", alert_type=AlertType.RESTRICTED_AREA_ENTRY,
            severity=Severity.CRITICAL, confidence=0.95,
            notes="Unauthorised entry detected in server room corridor.",
        ),
        AlertCreate(
            camera_id="CAM-01", alert_type=AlertType.LOITERING,
            severity=Severity.LOW, confidence=0.68,
            notes="Individual stationary near perimeter fence for >5 min.",
        ),
        AlertCreate(
            camera_id="CAM-04", alert_type=AlertType.CROWD_FORMATION,
            severity=Severity.MEDIUM, confidence=0.78,
            notes="Group of 6+ detected in emergency exit corridor.",
        ),
        AlertCreate(
            camera_id="CAM-02", alert_type=AlertType.PERSON_DETECTED,
            severity=Severity.LOW, confidence=0.91,
            notes="Person detected outside operating hours.",
        ),
        AlertCreate(
            camera_id="CAM-05", alert_type=AlertType.SUSPICIOUS_ACTIVITY,
            severity=Severity.HIGH, confidence=0.82,
            notes="Unusual movement pattern near storage facility.",
        ),
        AlertCreate(
            camera_id="CAM-03", alert_type=AlertType.UNKNOWN_OBJECT,
            severity=Severity.CRITICAL, confidence=0.88,
            notes="Unidentified object left near entrance gate.",
        ),
    ]
    for d in demos:
        service.create(d)


# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------
def main() -> None:
    st.set_page_config(
        page_title="SentinelOps — Alert Investigation",
        page_icon="🚨",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    # -- CSS ---------------------------------------------------------------
    st.markdown(
        """
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
        html, body, [class*="st-"] { font-family: 'Inter', sans-serif; }
        .block-container { padding-top: 2rem; }
        h1,h2,h3 { font-weight: 700 !important; }
        </style>
        """,
        unsafe_allow_html=True,
    )

    # Seed demo data
    _generate_demo_alerts()

    # -- Header ------------------------------------------------------------
    st.markdown(
        """
        <div style="text-align:center; padding: 1rem 0 0.5rem 0;">
            <h1 style="margin:0; font-size:2.2rem;">🚨 SentinelOps — Alert Investigation</h1>
            <p style="color:#94a3b8; margin-top:0.3rem;">Real-time security alert monitoring & investigation</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    alerts_data = load_alerts()

    if not alerts_data:
        st.info("No alerts found. The system will display alerts once they are generated.")
        return

    df = pd.DataFrame(alerts_data)
    df["timestamp"] = pd.to_datetime(df["timestamp"])

    # -- Sidebar filters ---------------------------------------------------
    with st.sidebar:
        st.header("🔍 Filters")

        sel_severity = st.multiselect(
            "Severity", [s.value for s in Severity],
            default=[s.value for s in Severity],
        )
        sel_status = st.multiselect(
            "Status", [s.value for s in AlertStatus],
            default=[s.value for s in AlertStatus],
        )
        sel_type = st.multiselect(
            "Alert Type", [t.value for t in AlertType],
            default=[t.value for t in AlertType],
        )
        cameras = sorted(df["camera_id"].unique().tolist())
        sel_cameras = st.multiselect("Camera", cameras, default=cameras)

        st.divider()
        st.caption("Alerts auto-refresh every 5 seconds.")

    # Apply filters
    mask = (
        df["severity"].isin(sel_severity)
        & df["status"].isin(sel_status)
        & df["alert_type"].isin(sel_type)
        & df["camera_id"].isin(sel_cameras)
    )
    filtered = df[mask].copy()

    # -- KPI cards ---------------------------------------------------------
    cols = st.columns(4)
    total = len(filtered)
    critical = len(filtered[filtered["severity"] == "Critical"])
    new_count = len(filtered[filtered["status"] == "New"])
    resolved = len(filtered[filtered["status"] == "Resolved"])

    with cols[0]:
        st.metric("📊 Total Alerts", total)
    with cols[1]:
        st.metric("🔴 Critical", critical)
    with cols[2]:
        st.metric("🆕 New / Unhandled", new_count)
    with cols[3]:
        st.metric("✅ Resolved", resolved)

    st.divider()

    # -- Tabs --------------------------------------------------------------
    tab_timeline, tab_charts, tab_investigate = st.tabs(
        ["📅 Alert Timeline", "📊 Analytics", "🔍 Investigation"]
    )

    # ── Timeline ──────────────────────────────────────────────────────────
    with tab_timeline:
        st.subheader("Alert Timeline")
        for _, row in filtered.iterrows():
            sev = row["severity"]
            color = SEVERITY_COLORS.get(sev, "#6366f1")
            st_color = STATUS_COLORS.get(row["status"], "#64748b")

            st.markdown(
                f"""
                <div style="
                    border-left: 4px solid {color};
                    background: #1e293b;
                    padding: 12px 16px;
                    border-radius: 8px;
                    margin-bottom: 8px;
                ">
                    <div style="display:flex; justify-content:space-between; align-items:center;">
                        <span style="font-weight:600; font-size:1rem;">
                            {row['alert_type']}
                        </span>
                        <span style="
                            background:{st_color}22;
                            color:{st_color};
                            padding:2px 10px;
                            border-radius:12px;
                            font-size:0.8rem;
                            font-weight:500;
                        ">{row['status']}</span>
                    </div>
                    <div style="color:#94a3b8; font-size:0.85rem; margin-top:4px;">
                        🎥 {row['camera_id']}  •  ⏰ {row['timestamp']}  •
                        <span style="color:{color}; font-weight:600;">⚠️ {sev}</span>  •
                        Confidence: {row['confidence']:.0%}
                    </div>
                    <div style="color:#cbd5e1; font-size:0.85rem; margin-top:6px;">
                        {row.get('notes', '')}
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

    # ── Analytics ─────────────────────────────────────────────────────────
    with tab_charts:
        c1, c2 = st.columns(2)

        with c1:
            sev_counts = filtered["severity"].value_counts()
            fig_sev = px.pie(
                names=sev_counts.index,
                values=sev_counts.values,
                color=sev_counts.index,
                color_discrete_map=SEVERITY_COLORS,
                title="By Severity",
                hole=0.45,
            )
            fig_sev.update_layout(
                template="plotly_dark",
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                font=dict(family="Inter"),
                margin=dict(t=50, b=20),
            )
            st.plotly_chart(fig_sev, use_container_width=True)

        with c2:
            stat_counts = filtered["status"].value_counts()
            fig_stat = px.pie(
                names=stat_counts.index,
                values=stat_counts.values,
                color=stat_counts.index,
                color_discrete_map=STATUS_COLORS,
                title="By Status",
                hole=0.45,
            )
            fig_stat.update_layout(
                template="plotly_dark",
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                font=dict(family="Inter"),
                margin=dict(t=50, b=20),
            )
            st.plotly_chart(fig_stat, use_container_width=True)

        # Alert type bar chart
        type_counts = filtered["alert_type"].value_counts()
        fig_type = px.bar(
            x=type_counts.index,
            y=type_counts.values,
            color=type_counts.index,
            color_discrete_sequence=COLOR_PALETTE,
            title="Alerts by Type",
            labels={"x": "Alert Type", "y": "Count"},
        )
        fig_type.update_layout(
            template="plotly_dark",
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font=dict(family="Inter"),
            showlegend=False,
            margin=dict(t=50, b=30),
        )
        st.plotly_chart(fig_type, use_container_width=True)

        # Camera distribution
        cam_counts = filtered["camera_id"].value_counts()
        fig_cam = px.bar(
            x=cam_counts.index,
            y=cam_counts.values,
            color=cam_counts.index,
            color_discrete_sequence=COLOR_PALETTE,
            title="Alerts by Camera",
            labels={"x": "Camera", "y": "Count"},
        )
        fig_cam.update_layout(
            template="plotly_dark",
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font=dict(family="Inter"),
            showlegend=False,
            margin=dict(t=50, b=30),
        )
        st.plotly_chart(fig_cam, use_container_width=True)

    # ── Investigation ─────────────────────────────────────────────────────
    with tab_investigate:
        st.subheader("🔍 Alert Investigation Panel")

        alert_ids = filtered["alert_id"].tolist()
        if not alert_ids:
            st.info("No alerts match the current filters.")
        else:
            selected_id = st.selectbox("Select alert to investigate", alert_ids)
            row = filtered[filtered["alert_id"] == selected_id].iloc[0]

            sev_color = SEVERITY_COLORS.get(row["severity"], "#6366f1")

            # -- Metadata panel
            m1, m2 = st.columns(2)
            with m1:
                st.markdown("#### 📋 Event Metadata")
                st.markdown(f"**Alert ID:** `{row['alert_id']}`")
                st.markdown(f"**Type:** {row['alert_type']}")
                st.markdown(f"**Camera:** {row['camera_id']}")
                st.markdown(f"**Timestamp:** {row['timestamp']}")
                st.markdown(
                    f"**Severity:** <span style='color:{sev_color}; font-weight:700;'>{row['severity']}</span>",
                    unsafe_allow_html=True,
                )
                st.markdown(f"**Confidence:** {row['confidence']:.1%}")
                st.markdown(f"**Status:** {row['status']}")
                if row.get("assigned_to"):
                    st.markdown(f"**Assigned To:** {row['assigned_to']}")

            with m2:
                st.markdown("#### 🖼️ Evidence")
                if row.get("image_path") and Path(row["image_path"]).exists():
                    st.image(row["image_path"], caption="Evidence Image", use_container_width=True)
                else:
                    st.info("No evidence image available for this alert.")

                if row.get("video_clip_path") and Path(row["video_clip_path"]).exists():
                    st.video(row["video_clip_path"])
                else:
                    st.info("No evidence video available for this alert.")

            # -- Investigation notes
            st.markdown("#### 📝 Investigation Notes")
            notes = row.get("notes", "")
            st.text_area("Notes", value=notes, height=150, disabled=True, key="inv_notes")

    # -- Footer ------------------------------------------------------------
    st.divider()
    st.markdown(
        "<p style='text-align:center; color:#64748b; font-size:0.85rem;'>"
        "SentinelOps © 2026 — Alert Investigation Dashboard"
        "</p>",
        unsafe_allow_html=True,
    )


if __name__ == "__main__":
    main()
