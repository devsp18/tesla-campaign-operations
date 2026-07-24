"""
Second pass: for each real Tesla campaign number we found, pull the
PotentiallyAffected unit count from NHTSA's campaign-detail endpoint.
"""
import requests
import pandas as pd
import time

DETAIL_URL = "https://api.nhtsa.gov/recalls/campaignNumber"

def fetch_details(campaign_numbers):
    results = []
    for i, campaign in enumerate(campaign_numbers):
        try:
            r = requests.get(DETAIL_URL, params={'campaignNumber': campaign}, timeout=15)
            if r.status_code == 200:
                data = r.json().get('results', [])
                if data:
                    row = data[0]
                    results.append({
                        'NHTSACampaignNumber': campaign,
                        'potentially_affected': row.get('PotentialNumberofUnitsAffected'),
                        'manufacturer': row.get('Manufacturer'),
                    })
                    affected = row.get('PotentialNumberofUnitsAffected', 'n/a')
                    print(f"  {campaign}: {affected} units")
            time.sleep(0.3)
        except Exception as e:
            print(f"  {campaign}: error \u2014 {e}")
        if (i + 1) % 15 == 0:
            print(f"  ...{i+1}/{len(campaign_numbers)} done")
    return pd.DataFrame(results)


if __name__ == "__main__":
    campaigns_df = pd.read_csv('data/tesla_recalls_nhtsa.csv')
    campaigns_df = campaigns_df.drop(columns=['potentially_affected'], errors='ignore')
    campaign_numbers = campaigns_df['NHTSACampaignNumber'].astype(str).tolist()

    print(f"Fetching affected-unit counts for {len(campaign_numbers)} real Tesla campaigns...\n")
    details = fetch_details(campaign_numbers)

    merged = campaigns_df.merge(
    details[['NHTSACampaignNumber', 'potentially_affected']],
    on='NHTSACampaignNumber', how='left'
)
    merged['potentially_affected'] = pd.to_numeric(
        merged['potentially_affected'], errors='coerce'
    )
    merged.to_csv('data/tesla_recalls_nhtsa.csv', index=False)

    print(f"\n{'='*60}")
    print("UPDATED WITH AFFECTED VEHICLE COUNTS")
    print(f"{'='*60}")
    print(f"Campaigns with unit counts: {merged['potentially_affected'].notna().sum()} / {len(merged)}")
    print(f"Total potentially affected vehicles: {merged['potentially_affected'].sum():,.0f}")
    print(f"\nBy remedy type:")
    print(merged.groupby('remedy_type').agg(
        campaigns=('NHTSACampaignNumber', 'count'),
        vehicles=('potentially_affected', 'sum')
    ).to_string())
    print(f"\nLargest campaigns:")
    print(merged.nlargest(8, 'potentially_affected')[
        ['NHTSACampaignNumber', 'report_year', 'remedy_type', 'component', 'potentially_affected']
    ].to_string(index=False))