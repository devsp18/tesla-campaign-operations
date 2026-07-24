"""
Build the SQLite data model for the Tesla campaign operations project.

Tables 1-2 hold REAL NHTSA regulatory data.
Tables 3-4 are created empty here and populated later by the rollout
simulator with MODELED output. The split is intentional.
"""

import os
import re
import sqlite3
import pandas as pd

DATA_CSV = "data/tesla_recalls_nhtsa.csv"
DB_PATH = "data/campaigns.db"

REMEDY_TAXONOMY = [
    ("OTA Software", 0, "none",
     "Fix delivered over the air. Scales to the full fleet without "
     "consuming service center capacity."),
    ("Hardware Service", 1, "parts_supply_and_bay_hours",
     "Physical part replacement. Throughput bounded by parts supply and "
     "technician bay hours."),
    ("Inspect & Replace", 1, "bay_hours",
     "Every vehicle must be inspected; only a subset needs the part. "
     "Highest capacity cost per affected vehicle."),
    ("Other", 1, "bay_hours",
     "Unclassified or mixed remedy. Treated as capacity constrained by "
     "default so the planner errs conservative."),
]

SCHEMA = """
DROP TABLE IF EXISTS rollout_schedule;
DROP TABLE IF EXISTS rollout_scenarios;
DROP TABLE IF EXISTS campaigns;
DROP TABLE IF EXISTS remedy_categories;

CREATE TABLE remedy_categories (
    remedy_type          TEXT PRIMARY KEY,
    capacity_constrained INTEGER NOT NULL,
    throughput_basis     TEXT,
    notes                TEXT
);

CREATE TABLE campaigns (
    campaign_number       TEXT PRIMARY KEY,
    report_date           TEXT,
    report_year           INTEGER,
    component             TEXT,
    summary               TEXT,
    consequence           TEXT,
    remedy                TEXT,
    remedy_type           TEXT REFERENCES remedy_categories(remedy_type),
    models_affected       TEXT,
    model_years_affected  TEXT,
    model_year_start      INTEGER,
    model_year_end        INTEGER,
    n_model_year_combos   INTEGER,
    potentially_affected  INTEGER
);

CREATE INDEX idx_campaigns_remedy ON campaigns(remedy_type);
CREATE INDEX idx_campaigns_year   ON campaigns(report_year);

CREATE TABLE rollout_scenarios (
    scenario_id        INTEGER PRIMARY KEY AUTOINCREMENT,
    scenario_name      TEXT NOT NULL,
    campaign_number    TEXT REFERENCES campaigns(campaign_number),
    affected_vehicles  INTEGER NOT NULL,
    remedy_type        TEXT REFERENCES remedy_categories(remedy_type),
    parts_per_week     INTEGER,
    slots_per_week     INTEGER,
    n_regions          INTEGER,
    strategy           TEXT,
    created_at         TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE rollout_schedule (
    scenario_id        INTEGER REFERENCES rollout_scenarios(scenario_id),
    week_number        INTEGER,
    region             TEXT,
    vehicles_invited   INTEGER,
    vehicles_completed INTEGER,
    backlog            INTEGER,
    bottleneck         TEXT,
    PRIMARY KEY (scenario_id, week_number, region)
);
"""


def parse_year_range(value):
    """'2025-2026' or '2017-2023' -> (2025, 2026). Handles en dash and hyphen."""
    if not isinstance(value, str):
        return (None, None)
    years = [int(m) for m in re.findall(r"(?:19|20)\d{2}", value)]
    if not years:
        return (None, None)
    return (min(years), max(years))


def main():
    df = pd.read_csv(DATA_CSV)

    df["potentially_affected"] = pd.to_numeric(
        df["potentially_affected"], errors="coerce"
    ).fillna(0).astype(int)

    ranges = df["model_years_affected"].apply(parse_year_range)
    df["model_year_start"] = [r[0] for r in ranges]
    df["model_year_end"] = [r[1] for r in ranges]

    campaigns = df.rename(columns={"NHTSACampaignNumber": "campaign_number"})[[
        "campaign_number", "report_date", "report_year", "component",
        "summary", "consequence", "remedy", "remedy_type",
        "models_affected", "model_years_affected",
        "model_year_start", "model_year_end",
        "n_model_year_combos", "potentially_affected",
    ]]

    os.makedirs("data", exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.executescript(SCHEMA)

    conn.executemany(
        "INSERT INTO remedy_categories VALUES (?, ?, ?, ?)", REMEDY_TAXONOMY
    )
    campaigns.to_sql("campaigns", conn, if_exists="append", index=False)
    conn.commit()

    print(f"Database written to {DB_PATH}\n")
    print(f"Campaigns loaded: {campaigns.shape[0]}")
    print(f"Total affected:   {campaigns['potentially_affected'].sum():,}\n")

    q = """
    SELECT c.remedy_type,
           rc.capacity_constrained,
           COUNT(*)                    AS campaigns,
           SUM(c.potentially_affected) AS vehicles,
           ROUND(100.0 * SUM(c.potentially_affected) /
                 (SELECT SUM(potentially_affected) FROM campaigns), 1) AS pct
    FROM campaigns c
    JOIN remedy_categories rc USING (remedy_type)
    GROUP BY c.remedy_type, rc.capacity_constrained
    ORDER BY vehicles DESC;
    """
    print(pd.read_sql(q, conn).to_string(index=False))

    unconstrained = pd.read_sql("""
        SELECT ROUND(100.0 * SUM(c.potentially_affected) /
               (SELECT SUM(potentially_affected) FROM campaigns), 1) AS pct
        FROM campaigns c
        JOIN remedy_categories rc USING (remedy_type)
        WHERE rc.capacity_constrained = 0;
    """, conn).iloc[0, 0]
    print(f"\nShare of affected vehicles reachable without service "
          f"capacity: {unconstrained}%")

    conn.close()


if __name__ == "__main__":
    main()