"""
One-page phased launch plan export.

Takes the currently selected campaign, capacity scenario, and wave
schedule from the dashboard and renders a single-page PDF summary: wave
order, weekly invitation volumes, regional gates, the completion
trajectory, and which 49 CFR 573.7(a) quarterly deadlines fall inside the
rollout window.

Uses fpdf2 with core (non-embedded) fonts, so the export has no font
files to bundle and no system rendering dependency, which keeps the
Streamlit Community Cloud build simple. Colors match the dashboard's
palette; typefaces are a plain proxy for the dashboard's Oswald / JetBrains
Mono system rather than the same fonts, since embedding them is not worth
the added build weight for a one-page export.

MODELED OUTPUT. Every wave, invitation volume, and completion figure in
this export comes from the capacity scenario set in the sidebar, not
observed Tesla data.
"""

from __future__ import annotations

import datetime as dt

from fpdf import FPDF

INK = (10, 10, 10)
RED = (204, 0, 0)
MID = (138, 135, 127)
GREY = (228, 226, 220)
WHITE = (255, 255, 255)


def _header(pdf: FPDF, campaign_number: str, component: str) -> None:
    pdf.set_fill_color(*INK)
    pdf.rect(0, 0, pdf.w, 22, style="F")
    pdf.set_xy(12, 6)
    pdf.set_text_color(*RED)
    pdf.set_font("Courier", "B", 9)
    pdf.cell(0, 5, "TESLA - SERVICE CAMPAIGN OPERATIONS", ln=1)
    pdf.set_xy(12, 12)
    pdf.set_text_color(*WHITE)
    pdf.set_font("Helvetica", "B", 16)
    pdf.cell(0, 8, "PHASED LAUNCH PLAN", ln=1)

    pdf.set_xy(12, 26)
    pdf.set_text_color(*INK)
    pdf.set_font("Helvetica", "B", 13)
    pdf.cell(0, 7, f"{campaign_number}  |  {component}"[:90], ln=1)


def _section_label(pdf: FPDF, text: str, y: float) -> None:
    pdf.set_xy(12, y)
    pdf.set_text_color(*MID)
    pdf.set_font("Courier", "", 8)
    pdf.cell(0, 5, text.upper(), ln=1)
    pdf.set_draw_color(*GREY)
    pdf.line(12, y + 5.5, pdf.w - 12, y + 5.5)


def _kv_row(pdf: FPDF, items: list[tuple[str, str]], y: float, col_w: float) -> None:
    x = 12
    for label, value in items:
        pdf.set_xy(x, y)
        pdf.set_text_color(*MID)
        pdf.set_font("Courier", "", 7)
        pdf.cell(col_w, 4, label.upper(), ln=0)
        pdf.set_xy(x, y + 4.2)
        pdf.set_text_color(*INK)
        pdf.set_font("Helvetica", "B", 11)
        pdf.cell(col_w, 6, str(value), ln=0)
        x += col_w


def build_launch_plan_pdf(
    *,
    campaign_number: str,
    component: str,
    remedy_type: str,
    affected_vehicles: int,
    parts_per_week: int,
    slots_per_week: int,
    regions: int,
    strategy_label: str,
    weeks_to_complete: int,
    binding_constraint: str,
    throughput: int,
    peak_backlog_phased: int,
    notification_date: dt.date,
    waves: list[dict],
    deadlines: list[dict],
) -> bytes:
    """Returns the PDF file as bytes, ready for st.download_button."""
    pdf = FPDF(orientation="P", unit="mm", format="Letter")
    pdf.set_auto_page_break(False)
    pdf.add_page()

    _header(pdf, campaign_number, component)

    y = 38
    _section_label(pdf, "Campaign and Scenario", y)
    y += 8
    _kv_row(pdf, [
        ("Remedy Type", remedy_type),
        ("Affected Vehicles", f"{affected_vehicles:,}"),
        ("Regions", str(regions)),
    ], y, col_w=62)
    y += 12
    _kv_row(pdf, [
        ("Parts / Week", f"{parts_per_week:,}"),
        ("Service Slots / Week", f"{slots_per_week:,}"),
        ("Binding Constraint", f"{binding_constraint} ({throughput:,}/wk)"),
    ], y, col_w=62)
    y += 12
    _kv_row(pdf, [
        ("Strategy", strategy_label),
        ("Weeks To Complete", str(weeks_to_complete)),
        ("Peak Backlog (Phased)", f"{peak_backlog_phased:,}"),
    ], y, col_w=62)
    y += 12
    _kv_row(pdf, [
        ("Owner Notification Date", notification_date.isoformat()),
        ("", ""),
        ("", ""),
    ], y, col_w=62)

    y += 14
    _section_label(pdf, "Wave Order and Regional Gates", y)
    y += 7
    headers = ["Region", "Start Wk", "End Wk", "Duration", "Vehicles", "Invitations/Wk"]
    widths = [30, 22, 22, 24, 32, 40]
    pdf.set_xy(12, y)
    pdf.set_fill_color(*INK)
    pdf.set_text_color(*WHITE)
    pdf.set_font("Courier", "B", 7.5)
    for h, w in zip(headers, widths):
        pdf.cell(w, 6, h.upper(), border=0, fill=True, align="L")
    y += 6
    pdf.set_font("Helvetica", "", 8.5)
    for i, w_row in enumerate(waves):
        pdf.set_xy(12, y)
        pdf.set_text_color(*INK)
        fill = (245, 244, 240) if i % 2 else (255, 255, 255)
        pdf.set_fill_color(*fill)
        per_week = w_row["vehicles"] // max(w_row["weeks"], 1)
        cells = [
            w_row["region"], str(w_row["start"]), str(w_row["end"]),
            f"{w_row['weeks']} wk", f"{w_row['vehicles']:,}", f"{per_week:,}",
        ]
        for val, cw in zip(cells, widths):
            pdf.cell(cw, 5.5, val, border=0, fill=True, align="L")
        y += 5.5

    y += 8
    _section_label(pdf, "Completion Trajectory and Reporting Checkpoints", y)
    y += 7
    headers2 = ["Quarter", "Due Date", "Rollout Week", "Status"]
    widths2 = [24, 34, 34, 40]
    pdf.set_xy(12, y)
    pdf.set_fill_color(*INK)
    pdf.set_text_color(*WHITE)
    pdf.set_font("Courier", "B", 7.5)
    for h, w in zip(headers2, widths2):
        pdf.cell(w, 6, h.upper(), border=0, fill=True, align="L")
    y += 6
    pdf.set_font("Helvetica", "", 8.5)
    for i, dl in enumerate(deadlines, start=1):
        pdf.set_xy(12, y)
        fill = (245, 244, 240) if i % 2 else (255, 255, 255)
        pdf.set_fill_color(*fill)
        status = "Cleared" if dl["cleared"] else "At risk: below 100%"
        status_color = INK if dl["cleared"] else RED
        wk_label = f"{dl['week']:.0f}" if dl["week"] >= 0 else "before start"
        cells = [f"Q{i}", dl["due_date"].isoformat(), wk_label]
        for val, cw in zip(cells, widths2[:3]):
            pdf.set_text_color(*INK)
            pdf.cell(cw, 5.5, val, border=0, fill=True, align="L")
        pdf.set_text_color(*status_color)
        pdf.cell(widths2[3], 5.5, status, border=0, fill=True, align="L")
        y += 5.5

    y += 6
    pdf.set_xy(12, y)
    n_cleared = sum(1 for d in deadlines if d["cleared"])
    pdf.set_text_color(*MID)
    pdf.set_font("Courier", "", 7.5)
    pdf.multi_cell(
        pdf.w - 24, 4,
        f"{n_cleared} of 6 quarterly completion report deadlines show full "
        f"completion under this scenario. 49 CFR 573.7(a): six consecutive "
        f"quarters or completion on all affected vehicles, whichever comes "
        f"first, starting the quarter owner notification is sent.",
    )

    pdf.set_xy(12, pdf.h - 18)
    pdf.set_draw_color(*GREY)
    pdf.line(12, pdf.h - 20, pdf.w - 12, pdf.h - 20)
    pdf.set_text_color(*MID)
    pdf.set_font("Courier", "", 6.5)
    pdf.multi_cell(
        pdf.w - 24, 3.4,
        "Campaign identity and affected-vehicle count are real NHTSA data. "
        "Wave order, invitation volumes, and the completion trajectory are "
        "a modeled scenario from the capacity inputs set in the dashboard, "
        "not observed Tesla data. "
        f"Generated {dt.date.today().isoformat()}.",
    )

    return bytes(pdf.output())
