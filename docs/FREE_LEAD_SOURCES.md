# Free/Freemium Lead Source Map (2026, API-First)

This document focuses on free or low-cost sources suitable for a student
hackathon, with Cloudflare-resistant collection patterns.

## Tier 1: Best core stack for your prospecting agent

1. Apollo API (credit-based)

- Why: strongest B2B people/company matching in one place.
- Use for: company search, people search, enrichment.
- Cost model: uses credits, but free/freemium plans can be enough for demo.
- Note: prioritize high-intent filters to save credits.

1. OpenCorporates API

- Why: legal entity and company verification data.
- Use for: validating real companies, industry hints, legal status.
- Free mode: open-data plan available with license conditions.

1. GitHub Search API

- Why: founder/dev-tool/startup discovery by org and repo activity.
- Use for: identifying technical ICP matches and developer-first companies.
- Free mode: unauthenticated + authenticated usage (higher practical limits with token).

1. Hacker News Firebase API

- Why: high-signal early-stage launch/activity source.
- Use for: detecting active or recently visible startups by keyword and link domain.
- Free mode: public API.

## Tier 2: High-value add-ons (mostly free/freemium)

1. Product Hunt GraphQL API

- Use for: new product launches matching ICP category keywords.
- Access: developer app/token flow.
- Great for: fresh outbound lists.

1. Greenhouse Job Board API

- Use for: intent signals from hiring patterns (public job boards).
- Key point: public GET endpoints for job board data.
- Great for: "hiring for X role" signals.

1. Lever Postings API

- Use for: public hiring signals from companies using Lever.
- Great for: enrich account-level intent and timing.

1. BuiltWith Free API

- Use for: lightweight technographic lookup.
- Great for: quick domain -> technology group checks.
- Caution: free endpoint is limited, use selectively.

1. Wappalyzer (free/freemium)

- Use for: domain-level tech discovery.
- Caution: free quota is small, reserve for high-priority domains.

## Tier 3: Useful but lower reliability or more manual setup

1. Startup directories (YC directory pages, indie directories)

- Good for breadth, weaker consistency.
- Prefer official pages/APIs and manual CSV import when no API is available.

1. Community sources (Reddit, niche forums)

- Good for idea discovery and timing signals.
- Use only official APIs where possible.

## Cloudflare and anti-bot reality: what actually works

## Do this

1. API-first architecture

- Prefer official APIs over HTML scraping.
- Treat scraping as fallback only.

1. Multi-source fallback chain

- If Source A blocks, move to Source B automatically.
- Keep provenance metadata (source, timestamp, URL).

1. Queue raw candidates, enrich later

- First collect company/domain candidates from free endpoints.
- Then spend Apollo credits only on top-scored candidates.

1. Add manual import lane

- Support CSV upload from user-provided exports where sites have strong anti-bot.

## Avoid this

1. Bypassing anti-bot protections aggressively.
2. Headless scraping against sites that disallow it in Terms.
3. Single-source dependency (fragile and expensive).

## Credit optimization strategy for your 900 Apollo credits

1. Start with free-source candidate pool.
2. Score companies before Apollo enrichment.
3. Enrich only top bucket (for example top 20-30%).
4. Request minimal fields first; fetch deeper details on demand.
5. Cache all successful enrichments locally to avoid repeat credit spend.

## Suggested field schema for lead quality

- company_name
- domain
- source
- source_url
- location
- industry
- employee_range
- technologies[]
- hiring_signals[]
- person_name
- person_title
- person_email
- person_linkedin
- confidence_score
- review_status

## Compliance and safety checklist

1. Respect source Terms and API policy.
2. Maintain attribution where required (especially open-data sources).
3. Keep outreach as reviewed drafts only in this stage.
4. Store consent/opt-out handling in downstream outreach stage.

## Final recommendation for hackathon demo

For best demo quality under zero budget, run this stack:

- Discovery: GitHub + Hacker News + OpenCorporates
- Enrichment and contacts: Apollo credits
- Queue: manual review CSV/JSON output

That gives you a reliable end-to-end prospecting story without paid enterprise
subscriptions or brittle scraping against Cloudflare-protected sites.
