# Hunter.io Domain Search Script

This folder contains a standalone script for collecting lead candidates from
Hunter's `domain-search` API endpoint.

## Why this exists

- Works as a quick prospecting stage for your end-to-end sales intelligence pipeline.
- Produces review artifacts only (`JSON` + `CSV`), not an auto-sender.
- Uses official API access (Cloudflare-safe compared to browser scraping).

## Setup

From project root:

```powershell
pip install -r requirements.txt
```

Set your Hunter key in env (recommended):

```powershell
$env:HUNTER_API_KEY="YOUR_KEY"
```

## Usage

Single domain:

```powershell
python tools/hunter_io/hunter_domain_search.py --domain stripe.com
```

Multiple domains via repeated flags:

```powershell
python tools/hunter_io/hunter_domain_search.py --domain stripe.com --domain notion.so --domain hubspot.com
```

Domains from file (one domain per line):

```powershell
python tools/hunter_io/hunter_domain_search.py --domains-file tools/hunter_io/domains.txt
```

With role filters:

```powershell
python tools/hunter_io/hunter_domain_search.py --domains-file tools/hunter_io/domains.txt --department engineering --seniority executive --per-domain-limit 50
```

Outputs are written to:

- `output/hunter/hunter_leads.json`
- `output/hunter/hunter_leads.csv`
- `output/hunter/hunter_domains.json` (domain-level metadata)
- `output/hunter/hunter_raw_responses.json` (raw Hunter API payload snapshots)

## Build a website/logo service shortlist

After collecting leads, generate a focused shortlist of likely decision-makers
for offers like website development and logo/branding:

```powershell
python tools/hunter_io/hunter_service_shortlist.py
```

Optional custom keywords and threshold:

```powershell
python tools/hunter_io/hunter_service_shortlist.py --title-keyword "creative" --title-keyword "brand" --min-confidence 90
```

Shortlist outputs:

- `output/hunter/hunter_web_logo_targets.json`
- `output/hunter/hunter_web_logo_targets.csv`

## Notes for hackathon usage

- Keep this as a reviewed queue source, not an outreach sender.
- Cache output and avoid re-querying the same domains to preserve free quota.
- Never commit real API keys to git; use env vars or local `.env`.
