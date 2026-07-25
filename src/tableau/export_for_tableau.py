"""
Export campaigns.db to flat CSVs for Tableau Public.

Tableau Public cannot connect to a live SQLite file, so this writes two
denormalized CSVs to data/tableau/ instead of shipping the .db:

  campaigns_with_remedy.csv       campaigns JOIN remedy_categories
  rollout_schedule_with_scenarios.csv   rollout_schedule JOIN rollout_scenarios

Both joins are done here rather than left for Tableau's relationship
model, so the workbook opens against two simple flat tables with no
joins to configure in Tableau Desktop.

REAL data: campaigns_with_remedy.csv (every column traces to the public
NHTSA record). MODELED data: rollout_schedule_with_scenarios.csv (every
row is scenario output from src/simulator/rollout.py, not observed Tesla
performance). Keep that boundary visible in the workbook: do not blend
the two files into one sheet.
"""

import os
import sqlite3

import pandas as pd

DB_PATH = "data/campaigns.db"
OUT_DIR = "data/tableau"


def export_campaigns(conn):
    df = pd.read_sql(
        """
        SELECT c.campaign_number, c.report_date, c.report_year, c.component,
               c.summary, c.consequence, c.remedy, c.remedy_type,
               c.models_affected, c.model_years_affected,
               c.model_year_start, c.model_year_end,
               c.n_model_year_combos, c.potentially_affected,
               rc.capacity_constrained, rc.throughput_basis, rc.notes AS remedy_notes
        FROM campaigns c
        JOIN remedy_categories rc USING (remedy_type)
        ORDER BY c.potentially_affected DESC;
        """,
        conn,
    )
    df["capacity_constrained"] = df["capacity_constrained"].map({1: "Yes", 0: "No"})
    out_path = os.path.join(OUT_DIR, "campaigns_with_remedy.csv")
    df.to_csv(out_path, index=False)
    return df, out_path


def export_rollout_schedule(conn):
    df = pd.read_sql(
        """
        SELECT s.scenario_id, sc.scenario_name, sc.campaign_number,
               sc.affected_vehicles, sc.remedy_type, sc.parts_per_week,
               sc.slots_per_week, sc.n_regions, sc.strategy, sc.created_at,
               s.week_number, s.region, s.vehicles_invited,
               s.vehicles_completed, s.backlog, s.bottleneck
        FROM rollout_schedule s
        JOIN rollout_scenarios sc USING (scenario_id)
        ORDER BY sc.scenario_id, s.week_number, s.region;
        """,
        conn,
    )
    out_path = os.path.join(OUT_DIR, "rollout_schedule_with_scenarios.csv")
    df.to_csv(out_path, index=False)
    return df, out_path


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)

    campaigns_df, campaigns_path = export_campaigns(conn)
    schedule_df, schedule_path = export_rollout_schedule(conn)

    conn.close()

    print(f"Wrote {campaigns_path}")
    print(f"  {len(campaigns_df)} campaigns, "
          f"{campaigns_df['potentially_affected'].sum():,} vehicles")
    print(f"  remedy types: {sorted(campaigns_df['remedy_type'].unique())}")

    print(f"\nWrote {schedule_path}")
    if schedule_df.empty:
        print("  0 rows. Run src/simulator/rollout.py to save at least one "
              "scenario before building the Rollout Schedule sheet, or the "
              "Rollout Schedule sheet will have nothing to plot.")
    else:
        n_scenarios = schedule_df["scenario_id"].nunique()
        print(f"  {len(schedule_df)} rows across {n_scenarios} scenario(s)")
        for name, sub in schedule_df.groupby("scenario_name"):
            weeks = sub["week_number"].max()
            print(f"    {name}: {weeks} weeks, strategy={sub['strategy'].iloc[0]}")


if __name__ == "__main__":
    main()
