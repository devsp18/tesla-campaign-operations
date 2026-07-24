# Campaign Rollout Intelligence

Tesla service campaign rollout planning under parts and service-capacity constraints, built on the public NHTSA recall database.

## The problem

When a fix is identified for hundreds of thousands of vehicles, you cannot notify every owner at once. Parts supply, service center capacity, and technician availability are all finite, and every campaign has to be sequenced around them. Sequencing decides who gets served when, and how large the owner queue grows before the campaign closes. This project models that constraint against Tesla's own service campaign history: given a campaign's affected-vehicle count and a weekly capacity budget, how long does completion take, and what does the queue look like along the way?

## Data sources and the real vs. modeled boundary

**Real** — 86 Tesla campaigns from the public NHTSA recall database, 2013 to 2026, 13,439,275 potentially affected vehicles. Campaign numbers, report dates, components, summaries, remedy text, remedy classification, and affected-vehicle counts all come from NHTSA.

**Modeled** — every weekly capacity input (parts per week, service slots per week, region count) and every rollout schedule, backlog curve, completion curve, and wave timeline derived from them.

NHTSA does not publish completion-over-time at the campaign level, so no curve in this project represents observed Tesla performance. The boundary is enforced structurally in the database: `campaigns` and `remedy_categories` hold real NHTSA data, `rollout_scenarios` and `rollout_schedule` hold modeled output.

## Findings

| Remedy Type | Capacity Constrained | Campaigns | Vehicles | Share |
|---|---|---|---|---|
| OTA Software | No | 33 | 12,474,059 | 92.8% |
| Hardware Service | Yes | 34 | 703,331 | 5.2% |
| Other | Yes | 9 | 230,213 | 1.7% |
| Inspect & Replace | Yes | 10 | 31,672 | 0.2% |

Total: 86 campaigns, 13,439,275 vehicles, 2013 to 2026.

Software and hardware campaigns are filed at nearly the same rate, 33 vs 34, but software reaches roughly 18x more vehicles per campaign (12.47M vs 703K). Hardware campaign size is bounded by what parts supply and technician hours can absorb, not by engineering or regulatory factors. Phasing a rollout does not make a campaign finish faster: throughput is fixed by whichever of parts or service slots binds first. What phasing changes is the size of the owner queue, not the completion date.

## Live demo

**[satyam-tesla-campaign-operations.streamlit.app](https://satyam-tesla-campaign-operations.streamlit.app/)**

Screenshots coming soon.

## What the dashboard shows

1. **Portfolio Mix** — Answers whether software and hardware campaigns are filed at similar rates. Shows campaign counts and vehicles reached by remedy type, with finding cards on OTA share and median hardware campaign size.
2. **Rollout Planner** — Answers whether phasing a rollout changes when it finishes. Plots backlog and cumulative repairs for a notify-all vs a capacity-matched strategy against the selected campaign's real vehicle count.
3. **Regional Sequencing** — Answers whether a campaign should serve one region at a time or all regions in parallel. Compares a wave Gantt against parallel rollout and ranks campaigns by capacity burden.
4. **Constraint Analysis** — Answers which input, parts or service slots, is actually limiting completion time. A 5x5 sensitivity heatmap shows weeks to complete across capacity combinations.
5. **Campaign Register** — Answers what the full campaign inventory looks like at a glance. Lists the top 25 campaigns by vehicles affected with remedy badges, plus any saved simulator scenarios.

## Repository structure

```
tesla-campaign-operations/
├── data/
│   ├── tesla_recalls_nhtsa.csv      # 86 real campaigns, fetched from NHTSA
│   └── campaigns.db                 # SQLite, built from the CSV
├── src/
│   ├── nhtsa/
│   │   ├── fetch_recalls.py         # pulls campaign list
│   │   └── fetch_affected_counts.py # pulls per-campaign affected units
│   ├── database/
│   │   └── build_db.py              # builds campaigns.db, prints verification
│   ├── simulator/
│   │   └── rollout.py               # capacity-constrained rollout simulator
│   └── dashboard/
│       └── app.py                   # Streamlit dashboard, 5 tabs
├── requirements.txt
├── LICENSE
└── .gitignore
```

## Reproducing the results

```bash
python3.11 -m venv venv && source venv/bin/activate
pip install -r requirements.txt

python3.11 src/nhtsa/fetch_recalls.py           # pull campaign list
python3.11 src/nhtsa/fetch_affected_counts.py   # pull affected unit counts
python3.11 src/database/build_db.py             # build campaigns.db
python3.11 src/simulator/rollout.py --campaign 21V00D000 \
    --parts-per-week 8000 --slots-per-week 12000 --regions 5
streamlit run src/dashboard/app.py
```

`data/campaigns.db` is committed, so you can skip straight to the dashboard without re-fetching from NHTSA.

## Model assumptions

- Vehicles are split evenly across regions. Real allocation would follow registration density.
- Weekly throughput per region is `min(parts_share, slots_share, backlog)`.
- Remedy type `Other` is treated as capacity constrained by default so the planner errs conservative and never overpromises throughput.
- OTA campaigns complete on release, matching observed NHTSA behavior.
- Region ordering in the wave view is illustrative. Real ordering would follow defect exposure, climate or usage factors that accelerate the failure mode, and regional service density. Those inputs are not in the public record.

## License

MIT, see [LICENSE](LICENSE).
