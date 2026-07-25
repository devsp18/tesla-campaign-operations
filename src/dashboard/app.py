"""
Tesla Service Campaign Operations: Campaign Rollout Planning and
Compliance Forecasting.

Campaign inventory, affected-vehicle counts, and remedy types are real
data from the public NHTSA recall database. Weekly capacity inputs and
all resulting rollout schedules are a modeled scenario.
"""

import datetime as dt
import sqlite3
import sys
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

sys.path.append(str(Path(__file__).resolve().parents[1]))
from simulator.rollout import simulate  # noqa: E402
from simulator.compliance import deadlines_with_status  # noqa: E402
from export.launch_plan import build_launch_plan_pdf  # noqa: E402

DB_PATH = str(Path(__file__).resolve().parents[2] / "data" / "campaigns.db")

st.set_page_config(
    page_title="Campaign Rollout Planning and Compliance Forecasting",
    page_icon="⚡", layout="wide", initial_sidebar_state="expanded")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Oswald:wght@500;600;700&family=Inter:wght@200;300;400;500;600&family=JetBrains+Mono:wght@300;400;500&display=swap');

* { font-family: 'Inter', sans-serif; }

.stApp { background: #faf9f6; }

section[data-testid="stSidebar"] {
    background: #f2f1ec !important;
    border-right: 1px solid #e4e2dc !important;
}
section[data-testid="stSidebar"] label,
section[data-testid="stSidebar"] p,
section[data-testid="stSidebar"] span { color: #111 !important; }

/* input fields must stay light */
section[data-testid="stSidebar"] input,
.stNumberInput input, .stTextInput input {
    background: #ffffff !important;
    color: #111111 !important;
    border: 1px solid #e0ded8 !important;
    border-radius: 3px !important;
    font-family: 'JetBrains Mono', monospace !important;
    font-size: 12px !important;
}
.stNumberInput button {
    background: #ffffff !important;
    color: #666 !important;
    border: 1px solid #e0ded8 !important;
}
div[data-testid="stNumberInputContainer"] { background: #ffffff !important; }

#MainMenu, footer, header { visibility: hidden; }
.block-container { padding-top: 2rem; max-width: 1500px; }

.main-header { border-bottom: 1px solid #e4e2dc; padding-bottom: 28px;
               margin-bottom: 36px; }

.tesla-wordmark {
    font-family: 'JetBrains Mono', monospace;
    font-size: 11px; font-weight: 500; color: #cc0000;
    letter-spacing: 5px; text-transform: uppercase; margin-bottom: 14px;
}

.header-title {
    font-family: 'Oswald', sans-serif;
    font-size: 52px; font-weight: 700; color: #0a0a0a;
    letter-spacing: -1px; line-height: 1.02; text-transform: uppercase;
    margin-bottom: 18px;
}

.header-subtitle {
    font-family: 'JetBrains Mono', monospace;
    font-size: 12px; font-weight: 300; color: #9a978f; letter-spacing: 0.5px;
}

.rail { text-align: right; padding-top: 46px; }
.rail-row {
    font-family: 'JetBrains Mono', monospace;
    font-size: 12px; letter-spacing: 1px; color: #9a978f;
    margin-bottom: 9px;
}
.rail-row b { color: #0a0a0a; font-weight: 500; margin-left: 22px; }

.kpi-card { padding: 26px 0 22px 0; }
.kpi-label {
    font-family: 'JetBrains Mono', monospace;
    font-size: 10px; font-weight: 400; color: #9a978f;
    text-transform: uppercase; letter-spacing: 2.5px; margin-bottom: 12px;
}
.kpi-value {
    font-family: 'Oswald', sans-serif;
    font-size: 46px; font-weight: 600; color: #0a0a0a;
    letter-spacing: -1px; line-height: 1;
}
.kpi-unit { font-family:'Oswald',sans-serif; font-size: 18px;
            font-weight: 400; color: #8a877f; }
.kpi-delta {
    font-family: 'JetBrains Mono', monospace;
    font-size: 11px; font-weight: 300; color: #b0ada5; margin-top: 10px;
}

.section-label {
    font-family: 'JetBrains Mono', monospace;
    font-size: 10px; font-weight: 400; color: #9a978f;
    text-transform: uppercase; letter-spacing: 3px;
    margin-bottom: 18px; padding-bottom: 10px;
    border-bottom: 1px solid #ece9e2;
}

.finding-card {
    background: #ffffff; border: 1px solid #ece9e2;
    border-top: 3px solid #0a0a0a;
    padding: 22px 26px; margin-bottom: 14px;
}
.finding-card.accent-red { border-top-color: #cc0000; }
.finding-card.accent-green { border-top-color: #1a7a3c; }
.finding-label {
    font-family: 'JetBrains Mono', monospace;
    font-size: 10px; font-weight: 400; color: #9a978f;
    text-transform: uppercase; letter-spacing: 2px; margin-bottom: 10px;
}
.finding-number {
    font-family: 'Oswald', sans-serif;
    font-size: 40px; font-weight: 600; color: #cc0000;
    letter-spacing: -1px; line-height: 1;
}
.finding-number.ink { color: #0a0a0a; }
.finding-desc { font-size: 13px; font-weight: 300; color: #6b6862;
                margin-top: 10px; line-height: 1.65; }

.row-item {
    display: flex; justify-content: space-between; align-items: center;
    padding: 13px 0; border-bottom: 1px solid #ece9e2;
}
.row-name { font-size: 13px; font-weight: 300; color: #222; }
.row-mono { font-family:'JetBrains Mono',monospace; font-size:12px;
            color:#0a0a0a; }
.row-right { display: flex; align-items: center; gap: 14px; }
.status-badge {
    font-family: 'JetBrains Mono', monospace;
    font-size: 9px; font-weight: 500; letter-spacing: 1.5px;
    text-transform: uppercase; padding: 3px 9px; border-radius: 2px;
    white-space: nowrap;
}
.badge-good { background:#f0faf0; color:#006622; border:1px solid #d0ead0; }
.badge-risk { background:#fff0f0; color:#cc0000; border:1px solid #f0d0d0; }
.badge-avg  { background:#f5f4f0; color:#666;    border:1px solid #e4e2dc; }

.stTabs [data-baseweb="tab-list"] {
    gap: 0; background: transparent; border-bottom: 1px solid #e4e2dc;
}
.stTabs [data-baseweb="tab"] {
    background: transparent; color: #9a978f;
    font-family: 'JetBrains Mono', monospace;
    font-size: 11px; font-weight: 400; letter-spacing: 2px;
    text-transform: uppercase; padding: 12px 22px;
    border: none; border-bottom: 2px solid transparent;
}
.stTabs [aria-selected="true"] {
    color: #0a0a0a !important; border-bottom: 2px solid #cc0000 !important;
    background: transparent !important;
}

.stSelectbox > div > div {
    background: #ffffff !important; border: 1px solid #e0ded8 !important;
    border-radius: 3px !important; color: #111 !important;
    font-family: 'JetBrains Mono', monospace !important;
    font-size: 12px !important;
}
hr { border-color: #e4e2dc !important; }
p { color: #6b6862; font-weight: 300; }

[data-baseweb="popover"], [data-baseweb="menu"] {
    background: #ffffff !important; border: 1px solid #e4e2dc !important; }
[data-baseweb="option"], li[role="option"] {
    background: #ffffff !important; color: #111 !important;
    font-family: 'JetBrains Mono', monospace !important;
    font-size: 12px !important; }
[data-baseweb="option"]:hover { background: #f5f4f0 !important; }
</style>
""", unsafe_allow_html=True)

PLOT_THEME = dict(
    template='plotly_white',
    paper_bgcolor='rgba(0,0,0,0)',
    plot_bgcolor='rgba(0,0,0,0)',
    font=dict(family='JetBrains Mono', color='#6b6862', size=11),
)

AXIS_FONT = dict(family='JetBrains Mono', color='#6b6862', size=11)
TITLE_FONT = dict(family='JetBrains Mono', color='#8a877f', size=10)
LEGEND = dict(orientation="h", y=1.08, x=0,
              font=dict(family='JetBrains Mono', color='#0a0a0a', size=11),
              bgcolor='rgba(0,0,0,0)')

INK, GREY, RED, MID = '#0a0a0a', '#d6d3cb', '#cc0000', '#8a877f'


@st.cache_data
def load_campaigns():
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql("""
        SELECT c.campaign_number, c.report_date, c.report_year, c.component,
               c.remedy_type, c.potentially_affected, c.models_affected,
               c.summary, rc.capacity_constrained
        FROM campaigns c JOIN remedy_categories rc USING (remedy_type)
        ORDER BY c.potentially_affected DESC;
    """, conn)
    conn.close()
    return df


@st.cache_data
def load_saved():
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql("""
        SELECT scenario_name, affected_vehicles, parts_per_week,
               slots_per_week, n_regions, strategy, created_at
        FROM rollout_scenarios ORDER BY scenario_id DESC;""", conn)
    conn.close()
    return df


def kpi(label, value, unit="", sub=""):
    st.markdown(f"""<div class='kpi-card'>
        <div class='kpi-label'>{label}</div>
        <div class='kpi-value'>{value}<span class='kpi-unit'>{unit}</span></div>
        <div class='kpi-delta'>{sub}</div></div>""", unsafe_allow_html=True)


def finding(label, number, desc, accent="", ink=False):
    st.markdown(f"""<div class='finding-card {accent}'>
        <div class='finding-label'>{label}</div>
        <div class='finding-number {"ink" if ink else ""}'>{number}</div>
        <div class='finding-desc'>{desc}</div></div>""",
                unsafe_allow_html=True)


def section(t):
    st.markdown(f"<div class='section-label'>{t}</div>",
                unsafe_allow_html=True)


campaigns = load_campaigns()
total = int(campaigns.potentially_affected.sum())
ota = int(campaigns.loc[campaigns.capacity_constrained == 0,
                        "potentially_affected"].sum())
constrained_units = total - ota
ota_share = 100 * ota / total

# ─────────────────────────────────────────────────────── header
h1, h2 = st.columns([2.1, 1])
with h1:
    st.markdown("""
    <div class='tesla-wordmark'>TESLA · SERVICE CAMPAIGN OPERATIONS</div>
    <div class='header-title'>CAMPAIGN ROLLOUT<br>PLANNING &amp;
    COMPLIANCE<br>FORECASTING</div>
    <div class='header-subtitle'>
        NHTSA recall data &nbsp;·&nbsp; Capacity modeling &nbsp;·&nbsp;
        Rollout sequencing &nbsp;·&nbsp; 2013&ndash;2026
    </div>""", unsafe_allow_html=True)
with h2:
    st.markdown("""<div class='rail'>
        <div class='rail-row'>SOURCE <b>NHTSA</b></div>
        <div class='rail-row'>FILINGS <b>2013&ndash;2026</b></div>
        <div class='rail-row'>REMEDY CLASSES <b>4</b></div>
        <div class='rail-row'>MODEL <b>CAPACITY CONSTRAINED</b></div>
        <div class='rail-row'>SCOPE <b>US MARKET</b></div>
    </div>""", unsafe_allow_html=True)

st.markdown("<div style='border-bottom:1px solid #e4e2dc;"
            "margin:24px 0 0 0;'></div>", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────── sidebar
constrained = campaigns[campaigns.capacity_constrained == 1].copy()
labels = {f"{r.campaign_number} · {r.potentially_affected:,} vehicles":
          r.campaign_number for r in constrained.itertuples()}

with st.sidebar:
    st.markdown("<div style='font-family:Inter,sans-serif;font-size:22px;"
                "font-weight:600;color:#0a0a0a;letter-spacing:9px;"
                "margin-bottom:2px;'>TESLA</div>", unsafe_allow_html=True)
    st.markdown("<p style='font-family:JetBrains Mono,monospace;"
                "font-size:11px;color:#9a978f;margin-top:-6px;'>"
                "Service Campaign Planner</p>", unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True)
    section("CAMPAIGN")
    choice = st.selectbox("Campaign", list(labels.keys()),
                          label_visibility="collapsed")
    row = campaigns[campaigns.campaign_number == labels[choice]].iloc[0]
    st.markdown("<br>", unsafe_allow_html=True)
    section("WEEKLY CAPACITY")
    parts = st.number_input("Parts per week", 500, 100000, 8000, 500)
    slots = st.number_input("Service slots per week", 500, 100000, 12000, 500)
    regions = st.slider("Regions", 1, 10, 5)
    st.markdown("<p style='font-family:JetBrains Mono,monospace;"
                "font-size:10px;color:#b0ada5;line-height:1.7;'>"
                "Only capacity constrained campaigns are listed. OTA "
                "campaigns complete on release and need no sequencing.</p>",
                unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True)
    section("COMPLIANCE CALENDAR")
    _filed = dt.date.fromisoformat(row.report_date)
    notification_date = st.date_input(
        "Owner notification date", value=_filed + dt.timedelta(days=60))
    st.markdown("<p style='font-family:JetBrains Mono,monospace;"
                "font-size:10px;color:#b0ada5;line-height:1.7;'>"
                "Defaults to 60 days after filing, the legal deadline under "
                "49 CFR 577.7(a)(1). Adjust to a planned notification date "
                "to see the six 49 CFR 573.7(a) quarterly completion report "
                "deadlines the rollout has to clear.</p>",
                unsafe_allow_html=True)

# ─────────────────────────────────────────────────────── simulate
frames = []
for strategy in ("notify_all", "capacity_matched"):
    d = pd.DataFrame(simulate(int(row.potentially_affected), 1,
                              parts, slots, regions, strategy))
    d["strategy"] = strategy
    frames.append(d)
sched = pd.concat(frames)

weekly = (sched.groupby(["strategy", "week_number"])
          .agg(backlog=("backlog", "sum"),
               completed=("vehicles_completed", "sum")).reset_index())
weekly["cumulative"] = weekly.groupby("strategy")["completed"].cumsum()

weeks = int(weekly.week_number.max())
peak_all = int(weekly.loc[weekly.strategy == "notify_all", "backlog"].max())
peak_phased = int(weekly.loc[weekly.strategy == "capacity_matched",
                             "backlog"].max())
binding = "PARTS" if parts <= slots else "SLOTS"
throughput = min(parts, slots)

# Wave schedule, shared by the Regional Sequencing tab and the launch plan
# export: full capacity applied to one region at a time.
affected = int(row.potentially_affected)
per_region = affected // regions
remainder = affected - per_region * regions
region_sizes = [per_region] * regions
region_sizes[0] += remainder

waves, cursor = [], 0
for i, size in enumerate(region_sizes):
    dur = -(-size // throughput)
    waves.append({
        "region": f"REGION {i + 1}",
        "start": cursor + 1,
        "end": cursor + dur,
        "weeks": dur,
        "vehicles": size,
    })
    cursor += dur
wave_df = pd.DataFrame(waves)
par_dur = -(-max(region_sizes) // max(throughput // regions, 1))

k = st.columns(5)
with k[0]:
    kpi("CAMPAIGNS", f"{len(campaigns)}", "", "NHTSA filings 2013–2026")
with k[1]:
    kpi("VEHICLES AFFECTED", f"{total/1e6:.1f}", "M", "Cumulative, all filings")
with k[2]:
    kpi("REACHABLE VIA OTA", f"{ota_share:.1f}", "%", "No service capacity")
with k[3]:
    kpi("REQUIRES SERVICE", f"{constrained_units/1000:.0f}", "K",
        "Parts and bay hour bound")
with k[4]:
    kpi("MODELED THROUGHPUT", f"{throughput/1000:.1f}", "K/wk",
        f"{binding.lower()} is binding")

st.markdown("<br>", unsafe_allow_html=True)
tab1, tab2, tab3, tab4, tab5 = st.tabs(
    ["Portfolio Mix", "Rollout Planner", "Regional Sequencing",
     "Constraint Analysis", "Campaign Register"])

# ─────────────────────────────────────────────────────── tab 1
with tab1:
    mix = (campaigns.groupby("remedy_type")
           .agg(n=("campaign_number", "count"),
                vehicles=("potentially_affected", "sum"))
           .reset_index().sort_values("vehicles"))

    L, R = st.columns([1.45, 1])
    with L:
        section("CAMPAIGNS FILED, BY REMEDY TYPE")
        f = go.Figure(go.Bar(
            y=mix.remedy_type, x=mix.n, orientation='h',
            marker_color=[INK if t == "OTA Software" else GREY
                          for t in mix.remedy_type],
            text=mix.n, textposition='outside',
            textfont=dict(size=11, color='#6b6862',
                          family='JetBrains Mono')))
        f.update_layout(**PLOT_THEME, height=250, showlegend=False,
                        margin=dict(l=0, r=50, t=6, b=6),
                        xaxis=dict(showgrid=False, visible=False),
                        yaxis=dict(title=None, tickfont=AXIS_FONT))
        st.plotly_chart(f, use_container_width=True)

        section("VEHICLES REACHED, BY REMEDY TYPE · LOG SCALE")
        f2 = go.Figure(go.Bar(
            y=mix.remedy_type, x=mix.vehicles, orientation='h',
            marker_color=[RED if t == "OTA Software" else INK
                          for t in mix.remedy_type],
            text=[f"{v:,.0f}" for v in mix.vehicles], textposition='outside',
            textfont=dict(size=11, color='#6b6862',
                          family='JetBrains Mono')))
        f2.update_layout(**PLOT_THEME, height=250, showlegend=False,
                         margin=dict(l=0, r=110, t=6, b=6),
                         xaxis=dict(type="log", showgrid=False, visible=False),
                         yaxis=dict(title=None, tickfont=AXIS_FONT))
        st.plotly_chart(f2, use_container_width=True)

    with R:
        section("WHAT THE DATA SHOWS")
        n_ota = int(mix.loc[mix.remedy_type == 'OTA Software', 'n'].iloc[0])
        n_hw = int(mix.loc[mix.remedy_type == 'Hardware Service', 'n'].iloc[0])
        finding("FLEET REACH VIA SOFTWARE", f"{ota_share:.1f}%",
                "Of all potentially affected vehicles, this share is "
                "remedied over the air with no service center involvement.",
                accent="accent-red")
        finding("FILING VOLUME · SOFTWARE VS HARDWARE", f"{n_ota} vs {n_hw}",
                "Nearly identical. The difference is not how often each "
                "occurs, but how many vehicles each can reach.", ink=True)
        finding("MEDIAN HARDWARE CAMPAIGN",
                f"{int(constrained.potentially_affected.median()):,}",
                "Hardware campaign size is bounded by what parts supply and "
                "technician hours can absorb.", ink=True)

    st.markdown("<br>", unsafe_allow_html=True)
    section("INTERPRETATION")
    st.markdown("<p style='font-size:14px;line-height:1.8;max-width:1000px;'>"
                "Software and hardware campaigns are filed at roughly the "
                "same rate, yet software reaches an order of magnitude more "
                "vehicles. The constraint is not engineering or regulatory. "
                "It is physical throughput: parts on hand and technician "
                "hours available. Every hardware campaign is therefore a "
                "sequencing problem before it is anything else.</p>",
                unsafe_allow_html=True)

# ─────────────────────────────────────────────────────── tab 2
with tab2:
    section(f"{row.campaign_number} · {row.component}")
    c = st.columns(4)
    with c[0]:
        kpi("WEEKS TO COMPLETE", f"{weeks}", "", "Identical, both strategies")
    with c[1]:
        kpi("BINDING CONSTRAINT", binding, "", f"{throughput:,} per week")
    with c[2]:
        kpi("PEAK QUEUE · NOTIFY ALL", f"{peak_all/1000:.0f}", "K",
            "Owners waiting, worst week")
    with c[3]:
        kpi("PEAK QUEUE · PHASED", f"{peak_phased:,}", "",
            f"{peak_all - peak_phased:,} fewer waiting")

    st.markdown("<br>", unsafe_allow_html=True)
    section("OWNERS WAITING FOR SERVICE, BY WEEK")
    f = go.Figure()
    for s, col, nm in [("notify_all", RED, "Notify all at once"),
                       ("capacity_matched", INK, "Capacity matched")]:
        d = weekly[weekly.strategy == s]
        f.add_trace(go.Scatter(
            x=d.week_number, y=d.backlog, mode='lines', name=nm,
            line=dict(color=col, width=2.5),
            fill='tozeroy' if s == "notify_all" else None,
            fillcolor='rgba(204,0,0,0.05)'))
    f.update_layout(**PLOT_THEME, height=340,
                    margin=dict(l=10, r=10, t=40, b=40),
                    legend=LEGEND,
                    xaxis=dict(title=dict(text="WEEK", font=TITLE_FONT),
                               showgrid=False, tickfont=AXIS_FONT),
                    yaxis=dict(title=dict(text="VEHICLES IN QUEUE",
                                          font=TITLE_FONT),
                               gridcolor='#ece9e2', zeroline=False,
                               tickfont=AXIS_FONT))
    st.plotly_chart(f, use_container_width=True)

    section("CUMULATIVE REPAIRS COMPLETED · WITH QUARTERLY REPORTING DEADLINES")

    weekly_cumulative = dict(zip(
        weekly.loc[weekly.strategy == "capacity_matched", "week_number"],
        weekly.loc[weekly.strategy == "capacity_matched", "cumulative"]))
    total_affected = int(row.potentially_affected)
    deadlines = deadlines_with_status(notification_date, weekly_cumulative,
                                      total_affected)

    f = go.Figure()
    for s, col, nm, dash, w in [
            ("notify_all", RED, "Notify all at once", 'solid', 2.5),
            ("capacity_matched", INK, "Capacity matched", 'dot', 3.5)]:
        d = weekly[weekly.strategy == s]
        f.add_trace(go.Scatter(x=d.week_number, y=d.cumulative, mode='lines',
                               name=nm,
                               line=dict(color=col, width=w, dash=dash)))
    for i, dl in enumerate(deadlines, start=1):
        wk = dl["week"]
        if 0 <= wk <= max(weeks, 1):
            vcolor = INK if dl["complete"] else RED
            f.add_vline(
                x=wk, line=dict(color=vcolor, width=1.5, dash="dash"),
                annotation_text=f"Q{i}",
                annotation_font=dict(color=vcolor, size=10,
                                     family='JetBrains Mono'))
    f.update_layout(**PLOT_THEME, height=300,
                    margin=dict(l=10, r=10, t=40, b=40),
                    legend=LEGEND,
                    xaxis=dict(title=dict(text="WEEK", font=TITLE_FONT),
                               showgrid=False, tickfont=AXIS_FONT),
                    yaxis=dict(title=dict(text="VEHICLES REPAIRED",
                                          font=TITLE_FONT),
                               gridcolor='#ece9e2', zeroline=False,
                               tickfont=AXIS_FONT))
    st.plotly_chart(f, use_container_width=True)

    st.markdown(
        "<p style='font-family:JetBrains Mono,monospace;font-size:10px;"
        "color:#b0ada5;'>Q1&ndash;Q6 mark the 49 CFR 573.7(a) quarterly "
        "completion report deadlines computed from the owner notification "
        "date in the sidebar. INK = complete by that week. RED = in "
        "progress, below 100% complete at that week. 573.7(a) requires "
        "filing a report every quarter regardless of completion rate, so "
        "in-progress is not a compliance risk, it is the expected state "
        "of an active campaign. Completion-over-time here is modeled, "
        "not observed. NHTSA does not publish it at campaign level.</p>",
        unsafe_allow_html=True)

    n_complete = sum(1 for d in deadlines if d["complete"])
    for i, dl in enumerate(deadlines, start=1):
        cls = "badge-good" if dl["complete"] else "badge-risk"
        label = ("Complete" if dl["complete"]
                 else f"In progress: {dl['pct_complete']*100:.0f}% complete at deadline")
        in_window = "inside rollout window" if 0 <= dl["week"] <= weeks \
            else "outside plotted range"
        st.markdown(f"""<div class='row-item'>
            <div class='row-name'>Q{i} &nbsp;·&nbsp;
            <span class='row-mono'>{dl['due_date'].isoformat()}</span>
            &nbsp;·&nbsp; week {dl['week']:.0f} &nbsp;·&nbsp;
            <span style='color:#8a877f;'>{in_window}</span></div>
            <div class='row-right'>
              <span class='status-badge {cls}'>{label}</span>
            </div></div>""", unsafe_allow_html=True)
    st.markdown(
        f"<p style='font-family:JetBrains Mono,monospace;font-size:10px;"
        f"color:#b0ada5;margin-top:8px;'>{n_complete} of 6 quarterly "
        f"deadlines already show full completion under this capacity "
        f"scenario. The rest still require filing a report showing "
        f"partial completion, which 49 CFR 573.7(a) requires regardless "
        f"of completion rate.</p>", unsafe_allow_html=True)

    st.markdown(f"""<div class='finding-card accent-red'>
        <div class='finding-label'>THE RESULT</div>
        <div class='finding-desc' style='font-size:14px;'>
        Both strategies finish in <b>{weeks} weeks</b>. The completion curves
        are identical, because throughput is fixed by {binding.lower()} at
        {throughput:,} vehicles per week and notifying more owners does not
        create capacity. What sequencing changes is the queue:
        <b>{peak_all:,}</b> owners waiting at peak versus
        <b>{peak_phased:,}</b>. Same completion date, materially different
        experience for owners and materially different load on service
        centers.</div></div>""", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    section("EXPORT")
    st.markdown(
        "<p style='font-size:13px;line-height:1.7;max-width:800px;'>"
        "One-page summary for this campaign and capacity scenario: wave "
        "order, weekly invitation volumes, regional gates, the completion "
        "trajectory, and which quarterly deadlines fall inside the rollout "
        "window.</p>", unsafe_allow_html=True)
    pdf_bytes = build_launch_plan_pdf(
        campaign_number=row.campaign_number,
        component=row.component,
        remedy_type=row.remedy_type,
        affected_vehicles=total_affected,
        parts_per_week=parts,
        slots_per_week=slots,
        regions=regions,
        strategy_label="Capacity matched (phased)",
        weeks_to_complete=weeks,
        binding_constraint=binding,
        throughput=throughput,
        peak_backlog_phased=peak_phased,
        notification_date=notification_date,
        waves=waves,
        deadlines=deadlines,
    )
    st.download_button(
        "Download phased launch plan (PDF)",
        data=pdf_bytes,
        file_name=f"{row.campaign_number}_phased_launch_plan.pdf",
        mime="application/pdf",
    )

# ─────────────────────────────────────────────────────── tab 3
with tab3:
    section("WAVE SEQUENCING · FULL CAPACITY, ONE REGION AT A TIME")

    f = go.Figure()
    for w in waves:
        f.add_trace(go.Bar(
            y=[w["region"]], x=[w["weeks"]], base=[w["start"] - 1],
            orientation='h', marker_color=INK, showlegend=False,
            width=0.45,
            hovertemplate=(f"{w['region']}<br>Weeks {w['start']}–{w['end']}"
                           f"<br>{w['vehicles']:,} vehicles<extra></extra>")))
        f.add_trace(go.Bar(
            y=[w["region"]], x=[par_dur], base=[0], orientation='h',
            marker_color='rgba(204,0,0,0.13)', showlegend=False, width=0.16,
            hoverinfo='skip'))
    f.update_layout(**PLOT_THEME, height=300, barmode='overlay',
                    margin=dict(l=10, r=10, t=20, b=40),
                    xaxis=dict(title=dict(text="WEEK", font=TITLE_FONT),
                               showgrid=True, gridcolor='#ece9e2',
                               tickfont=AXIS_FONT),
                    yaxis=dict(title=None, tickfont=AXIS_FONT,
                               autorange="reversed"))
    st.plotly_chart(f, use_container_width=True)

    st.markdown(
        "<p style='font-family:JetBrains Mono,monospace;font-size:10px;"
        "color:#b0ada5;'>SOLID = wave sequencing &nbsp;·&nbsp; "
        "SHADED = parallel rollout, every region open the full duration"
        "</p>", unsafe_allow_html=True)

    first_done = waves[0]["end"]
    a, b, c = st.columns(3)
    with a:
        kpi("FIRST REGION CLEARED", f"{first_done}", " wk",
            f"Parallel rollout clears none until week {par_dur}")
    with b:
        kpi("NATIONAL COMPLETION", f"{waves[-1]['end']}", " wk",
            "Unchanged. Total capacity is identical")
    with c:
        pulled = par_dur - first_done
        kpi("EARLIEST OWNERS SERVED", f"{pulled}", " wk earlier",
            f"{waves[0]['vehicles']:,} vehicles in the first wave")

    st.markdown("<br>", unsafe_allow_html=True)
    L, R = st.columns([1, 1])
    with L:
        finding("THE SEQUENCING TRADEOFF", f"{first_done} vs {par_dur}",
                "Splitting capacity across all regions means no region "
                "finishes early. Concentrating it clears regions one at a "
                "time. National completion is identical either way, so the "
                "choice is about who gets served first, not how fast the "
                "campaign closes.", accent="accent-red")
    with R:
        finding("HOW REGIONS WOULD BE ORDERED", "SEVERITY FIRST",
                "This model splits vehicles evenly for illustration. In "
                "practice the ordering would follow defect exposure, climate "
                "or usage factors that accelerate the failure mode, and "
                "regional service density. Those inputs are not in the "
                "public NHTSA record.", ink=True)

    st.markdown("<br>", unsafe_allow_html=True)
    section("DERIVED RISK FLAGS · CURRENT SCENARIO")

    cm = sched[sched.strategy == "capacity_matched"]
    constrained_weeks = int(cm[cm.bottleneck.notna()].week_number.nunique())
    peak_week = int(weekly.loc[
        weekly.strategy == "notify_all", "backlog"].idxmax()) + 1
    burden = affected / throughput
    headroom = abs(parts - slots)

    flags = []
    if constrained_weeks >= weeks * 0.9:
        flags.append((
            "CAPACITY SATURATED", "badge-risk",
            f"{binding.title()} is the binding constraint in "
            f"{constrained_weeks} of {weeks} weeks. There is no slack "
            f"anywhere in the schedule."))
    if headroom / max(parts, slots) > 0.3:
        idle = "service slots" if slots > parts else "parts supply"
        flags.append((
            "IDLE CAPACITY", "badge-risk",
            f"{headroom:,} units per week of {idle} go unused because the "
            f"other input binds first. Investment here returns nothing."))
    else:
        flags.append((
            "INPUTS BALANCED", "badge-good",
            f"Parts and slots are within {100*headroom/max(parts,slots):.0f}% "
            f"of each other. Neither input is badly oversupplied."))
    if burden > 26:
        flags.append((
            "EXTENDED DURATION", "badge-risk",
            f"At {throughput:,} per week this campaign runs "
            f"{burden/4.3:.0f} months. Long campaigns accumulate owner "
            f"attrition and parts revision risk."))
    flags.append((
        "PEAK QUEUE WEEK", "badge-avg",
        f"Under notify-all, owners waiting peaks at {peak_all:,} in week "
        f"{peak_week}. Phasing holds this at {peak_phased:,} throughout."))

    for label, cls, text in flags:
        st.markdown(f"""<div class='row-item'>
            <div class='row-name' style='max-width:78%;'>{text}</div>
            <div class='row-right'>
              <span class='status-badge {cls}'>{label}</span>
            </div></div>""", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    section(f"CAPACITY BURDEN · WEEKS REQUIRED AT {throughput:,}/WEEK")

    burden_df = constrained.head(10).copy()
    burden_df["weeks_req"] = (
        burden_df.potentially_affected / throughput).apply(
        lambda x: int(-(-x // 1)))
    burden_df = burden_df.sort_values("weeks_req")

    f = go.Figure(go.Bar(
        y=burden_df.campaign_number, x=burden_df.weeks_req, orientation='h',
        marker_color=[RED if cn == row.campaign_number else GREY
                      for cn in burden_df.campaign_number],
        text=burden_df.weeks_req, textposition='outside',
        textfont=dict(size=11, color='#6b6862', family='JetBrains Mono')))
    f.update_layout(**PLOT_THEME, height=340, showlegend=False,
                    margin=dict(l=10, r=50, t=10, b=40),
                    xaxis=dict(title=dict(text="WEEKS TO COMPLETE",
                                          font=TITLE_FONT),
                               showgrid=False, tickfont=AXIS_FONT),
                    yaxis=dict(title=None, tickfont=AXIS_FONT))
    st.plotly_chart(f, use_container_width=True)

    st.markdown(
        "<p style='font-size:13px;line-height:1.75;max-width:1000px;'>"
        "Ranking by capacity burden rather than vehicle count answers a "
        "different question: not which campaign is largest, but which will "
        "occupy service capacity longest at a given throughput. Two "
        "campaigns of similar size can differ substantially once remedy "
        "type is accounted for. The currently selected campaign is "
        "highlighted.</p>", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────── tab 4
with tab4:
    section("SENSITIVITY · WEEKS TO COMPLETE ACROSS CAPACITY LEVELS")
    grid = []
    for p in [4000, 8000, 12000, 16000, 20000]:
        for s in [4000, 8000, 12000, 16000, 20000]:
            d = simulate(int(row.potentially_affected), 1, p, s,
                         regions, "capacity_matched")
            grid.append({"parts": p, "slots": s,
                         "weeks": max(x["week_number"] for x in d)})
    pivot = pd.DataFrame(grid).pivot(index="slots", columns="parts",
                                     values="weeks")
    f = go.Figure(go.Heatmap(
        z=pivot.values,
        x=[f"{c//1000}K" for c in pivot.columns],
        y=[f"{i//1000}K" for i in pivot.index],
        colorscale=[[0, '#0a0a0a'], [1, '#f2f1ec']],
        text=pivot.values, texttemplate="%{text}",
        textfont=dict(size=12, family='JetBrains Mono'), showscale=False))
    f.update_layout(**PLOT_THEME, height=380,
                    margin=dict(l=10, r=10, t=10, b=40),
                    xaxis=dict(title=dict(text="PARTS PER WEEK",
                                          font=TITLE_FONT),
                               tickfont=AXIS_FONT),
                    yaxis=dict(title=dict(text="SERVICE SLOTS PER WEEK",
                                          font=TITLE_FONT),
                               tickfont=AXIS_FONT))
    st.plotly_chart(f, use_container_width=True)

    a, b = st.columns(2)
    with a:
        finding("WHY THE GRID IS SYMMETRIC", "MIN(P, S)",
                "Weeks to complete depends only on the smaller of the two "
                "inputs. Doubling parts while slots stay fixed changes "
                "nothing. This is the single most important planning fact "
                "in the model.", accent="accent-red")
    with b:
        finding("PRACTICAL IMPLICATION", "ONE LEVER",
                "Capacity investment only pays off when it targets the "
                "binding constraint. Identifying which of the two binds, "
                "per region and per week, is the prerequisite to any "
                "acceleration effort.", ink=True)

    st.markdown("<br>", unsafe_allow_html=True)
    section("REGIONS CONSTRAINED, BY WEEK · CURRENT SCENARIO")
    bt = (sched[sched.strategy == "capacity_matched"]
          .groupby(["week_number", "bottleneck"]).size()
          .reset_index(name="regions"))
    if not bt.empty:
        f = go.Figure(go.Bar(x=bt.week_number, y=bt.regions,
                             marker_color=RED if binding == "PARTS" else INK))
        f.update_layout(**PLOT_THEME, height=210,
                        margin=dict(l=10, r=10, t=10, b=40),
                        xaxis=dict(title=dict(text="WEEK", font=TITLE_FONT),
                                   showgrid=False, tickfont=AXIS_FONT),
                        yaxis=dict(title=dict(text="REGIONS",
                                              font=TITLE_FONT),
                                   gridcolor='#ece9e2', tickfont=AXIS_FONT))
        st.plotly_chart(f, use_container_width=True)

# ─────────────────────────────────────────────────────── tab 5
with tab5:
    section("CAMPAIGN REGISTER · TOP 25 BY VEHICLES AFFECTED")
    for r in campaigns.head(25).itertuples():
        if r.capacity_constrained == 0:
            badge, cls = "OTA", "badge-good"
        elif r.remedy_type == "Inspect & Replace":
            badge, cls = "INSPECT", "badge-risk"
        else:
            badge, cls = "SERVICE", "badge-avg"
        st.markdown(f"""<div class='row-item'>
            <div class='row-name'><span class='row-mono'>
            {r.campaign_number}</span> &nbsp;·&nbsp;
            <span style='color:#8a877f;'>{r.component[:54]}</span></div>
            <div class='row-right'>
              <span class='row-mono'>{r.potentially_affected:,}</span>
              <span class='status-badge {cls}'>{badge}</span>
            </div></div>""", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    section("SAVED SCENARIOS")
    saved = load_saved()
    if saved.empty:
        st.markdown("<p style='font-size:12px;'>No scenarios saved. Run "
                    "src/simulator/rollout.py to persist one.</p>",
                    unsafe_allow_html=True)
    else:
        st.dataframe(saved, use_container_width=True, hide_index=True)

st.markdown("<br><hr>", unsafe_allow_html=True)
st.markdown(
    "<p style='font-family:JetBrains Mono,monospace;font-size:10px;"
    "color:#b0ada5;line-height:1.8;'>Campaign inventory, affected-vehicle "
    "counts, and remedy classifications are real data from the public NHTSA "
    "recall database — 86 Tesla campaigns, 2013–2026. Weekly capacity inputs "
    "and all rollout schedules are a modeled scenario. NHTSA does not publish "
    "completion-over-time at campaign level, so no curve here should be read "
    "as observed Tesla performance.</p>", unsafe_allow_html=True)