"""
Capacity-constrained rollout simulator.

MODELED OUTPUT. Campaign sizes and remedy types are real NHTSA data;
the weekly parts supply, service slot capacity, and resulting schedules
are a scenario model, not observed Tesla data. NHTSA does not publish
completion-over-time at campaign level.
"""

import argparse
import sqlite3
import pandas as pd

DB_PATH = "data/campaigns.db"
MAX_WEEKS = 260


def get_campaign(conn, campaign_number):
    row = pd.read_sql(
        """
        SELECT c.campaign_number, c.potentially_affected, c.remedy_type,
               rc.capacity_constrained
        FROM campaigns c
        JOIN remedy_categories rc USING (remedy_type)
        WHERE c.campaign_number = ?;
        """,
        conn, params=(campaign_number,)
    )
    if row.empty:
        raise SystemExit(f"Campaign {campaign_number} not found in database.")
    return row.iloc[0]


def simulate(affected, capacity_constrained, parts_per_week,
             slots_per_week, n_regions, strategy):
    """Return a list of weekly per-region rows."""
    regions = [f"R{i + 1}" for i in range(n_regions)]
    per_region = affected // n_regions
    remainder = affected - per_region * n_regions

    # Unserved but not yet invited
    pending = {r: per_region for r in regions}
    pending[regions[0]] += remainder
    # Invited and waiting for service
    backlog = {r: 0 for r in regions}

    parts_share = parts_per_week / n_regions
    slots_share = slots_per_week / n_regions

    rows = []
    week = 0
    while (sum(pending.values()) + sum(backlog.values())) > 0 and week < MAX_WEEKS:
        week += 1
        for r in regions:
            if not capacity_constrained:
                # OTA: the whole fleet is remedied on release
                invited = completed = pending[r]
                pending[r] = 0
                bottleneck = None
            else:
                capacity = int(min(parts_share, slots_share))

                if strategy == "notify_all":
                    invited = pending[r]          # everyone, week 1
                else:
                    invited = min(pending[r], capacity)

                pending[r] -= invited
                backlog[r] += invited

                completed = min(capacity, backlog[r])
                backlog[r] -= completed

                if backlog[r] == 0 and completed == 0:
                    bottleneck = None
                elif parts_share <= slots_share:
                    bottleneck = "parts"
                else:
                    bottleneck = "slots"

            rows.append({
                "week_number": week,
                "region": r,
                "vehicles_invited": int(invited),
                "vehicles_completed": int(completed),
                "backlog": int(backlog[r]),
                "bottleneck": bottleneck,
            })
    return rows


def save_scenario(conn, name, campaign, parts, slots, n_regions,
                  strategy, rows):
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO rollout_scenarios
            (scenario_name, campaign_number, affected_vehicles, remedy_type,
             parts_per_week, slots_per_week, n_regions, strategy)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?);
        """,
        (name, campaign["campaign_number"],
         int(campaign["potentially_affected"]), campaign["remedy_type"],
         parts, slots, n_regions, strategy)
    )
    scenario_id = cur.lastrowid
    df = pd.DataFrame(rows)
    df.insert(0, "scenario_id", scenario_id)
    df.to_sql("rollout_schedule", conn, if_exists="append", index=False)
    conn.commit()
    return scenario_id, df


def summarize(label, df):
    weeks = int(df["week_number"].max())
    peak = int(df.groupby("week_number")["backlog"].sum().max())
    binding = df.loc[df["bottleneck"].notna(), "bottleneck"]
    top = binding.value_counts().idxmax() if not binding.empty else "none"
    print(f"  {label:<18} weeks to complete: {weeks:>4}   "
          f"peak backlog: {peak:>10,}   binding constraint: {top}")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--campaign", default="24V554000",
                   help="NHTSA campaign number to model")
    p.add_argument("--parts-per-week", type=int, default=20000)
    p.add_argument("--slots-per-week", type=int, default=15000)
    p.add_argument("--regions", type=int, default=5)
    args = p.parse_args()

    conn = sqlite3.connect(DB_PATH)
    campaign = get_campaign(conn, args.campaign)

    print(f"\nCampaign {campaign['campaign_number']}  "
          f"({campaign['remedy_type']})")
    print(f"Affected vehicles: {int(campaign['potentially_affected']):,}")
    print(f"Capacity: {args.parts_per_week:,} parts/wk, "
          f"{args.slots_per_week:,} slots/wk across {args.regions} regions\n")

    for strategy in ("notify_all", "capacity_matched"):
        rows = simulate(
            int(campaign["potentially_affected"]),
            int(campaign["capacity_constrained"]),
            args.parts_per_week, args.slots_per_week,
            args.regions, strategy
        )
        name = f"{campaign['campaign_number']}_{strategy}"
        sid, df = save_scenario(conn, name, campaign, args.parts_per_week,
                                args.slots_per_week, args.regions,
                                strategy, rows)
        summarize(strategy, df)

    print(f"\nScenarios written to rollout_scenarios / rollout_schedule.")
    conn.close()


if __name__ == "__main__":
    main()