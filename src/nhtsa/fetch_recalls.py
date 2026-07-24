"""
Fetches REAL Tesla recall campaign data from NHTSA's public API.
Every recall Tesla has ever issued — campaign numbers, remedy descriptions,
dates, affected components. This is public regulatory data.
"""
import requests
import pandas as pd
import time
import os

MODELS = ['MODEL S', 'MODEL X', 'MODEL 3', 'MODEL Y', 'CYBERTRUCK']
YEARS = range(2013, 2027)

BASE_URL = "https://api.nhtsa.gov/recalls/recallsByVehicle"


def fetch_recalls():
    all_recalls = []
    for model in MODELS:
        for year in YEARS:
            try:
                r = requests.get(
                    BASE_URL,
                    params={'make': 'TESLA', 'model': model, 'modelYear': year},
                    timeout=15
                )
                if r.status_code == 200:
                    data = r.json()
                    for item in data.get('results', []):
                        item['queried_model'] = model
                        item['queried_year'] = year
                        all_recalls.append(item)
                    print(f"  {model} {year}: {data.get('Count', 0)} recalls")
                time.sleep(0.3)
            except Exception as e:
                print(f"  {model} {year}: error \u2014 {e}")
    return all_recalls


def process(recalls):
    df = pd.DataFrame(recalls)
    if df.empty:
        raise SystemExit("No data returned \u2014 check network/API.")

    print(f"\nColumns returned by API: {list(df.columns)}\n")

    df['ReportReceivedDate'] = pd.to_datetime(
        df['ReportReceivedDate'], errors='coerce', dayfirst=True
    )

    agg_dict = {
        'report_date': ('ReportReceivedDate', 'first'),
        'component': ('Component', 'first'),
        'summary': ('Summary', 'first'),
        'consequence': ('Consequence', 'first'),
        'remedy': ('Remedy', 'first'),
        'models_affected': ('queried_model', lambda x: ', '.join(sorted(set(x)))),
        'model_years_affected': ('queried_year', lambda x: f"{min(x)}\u2013{max(x)}"),
        'n_model_year_combos': ('queried_year', 'count'),
    }

    if 'PotentiallyAffected' in df.columns:
        agg_dict['potentially_affected'] = ('PotentiallyAffected', 'first')

    campaigns = df.groupby('NHTSACampaignNumber').agg(**agg_dict).reset_index()

    if 'potentially_affected' in campaigns.columns:
        campaigns['potentially_affected'] = pd.to_numeric(
            campaigns['potentially_affected'], errors='coerce'
        )
    else:
        campaigns['potentially_affected'] = pd.NA
        print("NOTE: recallsByVehicle doesn't return affected-unit counts.")
        print("We'll pull those from the campaign-detail endpoint separately.\n")

    campaigns['report_year'] = campaigns['report_date'].dt.year

    def classify_remedy(remedy):
        r = str(remedy).lower()
        if 'over-the-air' in r or 'ota' in r or 'software update' in r or 'firmware' in r:
            return 'OTA Software'
        elif 'inspect' in r and 'replace' in r:
            return 'Inspect & Replace'
        elif 'replace' in r or 'install' in r or 'rework' in r or 'tighten' in r or 'repair' in r:
            return 'Hardware Service'
        else:
            return 'Other'

    campaigns['remedy_type'] = campaigns['remedy'].apply(classify_remedy)
    campaigns = campaigns.sort_values('report_date', ascending=False)
    return campaigns


if __name__ == "__main__":
    os.makedirs('data', exist_ok=True)
    print("Fetching Tesla recall campaigns from NHTSA (public API)...")
    raw = fetch_recalls()
    campaigns = process(raw)

    campaigns.to_csv('data/tesla_recalls_nhtsa.csv', index=False)

    print(f"\n{'='*60}")
    print(f"REAL TESLA RECALL DATA \u2014 NHTSA")
    print(f"{'='*60}")
    print(f"Unique campaigns: {len(campaigns)}")
    print(f"Date range: {campaigns['report_date'].min().date()} \u2192 {campaigns['report_date'].max().date()}")
    if campaigns['potentially_affected'].notna().any():
        print(f"Total potentially affected vehicles: {campaigns['potentially_affected'].sum():,.0f}")
    print(f"\nBy remedy type:")
    print(campaigns.groupby('remedy_type').size().to_string())
    print(f"\nMost recent campaigns:")
    print(campaigns.head(8)[
        ['NHTSACampaignNumber', 'report_year', 'remedy_type', 'component']
    ].to_string(index=False))
    print(f"\nSaved: data/tesla_recalls_nhtsa.csv")