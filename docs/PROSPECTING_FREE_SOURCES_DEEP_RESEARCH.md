# Prospecting Agent Deep Research (Free Sources, 2026)

This guide is optimized for student hackathon constraints:

- No paid data subscriptions required.
- API-first where possible.
- Queue generation only (human-reviewed outreach drafts).
- Avoid brittle scraping against anti-bot systems.

## 1) Recommended architecture for free prospecting

Use a 4-step funnel to maximize quality with low quota:

1. Discovery (free/public APIs): collect company/domain candidates.
2. Qualification (cheap signals): score by ICP fit before enrichment.
3. Contact enrichment (limited quota): query contact APIs only for top candidates.
4. Output queue: JSON/CSV review queue with provenance and confidence.

Practical reason: your expensive/limited API calls are used only on high-likelihood targets.

## 2) Best free lead sources by data type

## A) Company discovery and startup signals

1. GitHub Search API (free)
- What you get: organizations, repos, topics, activity.
- ICP fit: dev tools, SaaS, technical startups.
- Access: official API token optional (higher limits with token).
- Source value: strong tech-stack intent clues from repos/topics.

2. Hacker News Firebase API (free/public)
- What you get: launch posts, Show HN, comment threads, outbound links.
- ICP fit: early-stage teams and new product activity.
- Access: public API.
- Source value: strong recency/intent signal.

3. Product Hunt (developer API / GraphQL)
- What you get: newly launched products, categories, makers.
- ICP fit: fresh startup pipeline.
- Access: developer app/token.
- Source value: launch timing and category intent.

4. OpenCorporates API (open-data friendly)
- What you get: legal entity records, jurisdiction, status.
- ICP fit: company verification and legal normalization.
- Access: free/open usage tier under policy constraints.
- Source value: trust and dedup accuracy.

5. Crunchbase alternative public datasets (community/open lists)
- What you get: startup names/domains from curated open lists.
- ICP fit: broad discovery input.
- Access: varies by list license.
- Source value: useful seed list; must validate freshness.

## B) Hiring and intent signals

1. Greenhouse Job Board API (public endpoints)
- What you get: job postings for companies using Greenhouse.
- Signal: hiring for sales ops, SDR, RevOps, data engineering, AI.
- Why useful: active hiring implies budget and growth timing.

2. Lever Postings API (public job feeds)
- What you get: open roles and metadata.
- Signal: role mix indicates maturity and GTM motion.

3. YC jobs/startup pages (public pages, sometimes structured JSON)
- What you get: startup profiles, jobs, descriptions.
- Signal: stage and team growth.

## C) Technographic data (free/freemium constrained)

1. BuiltWith free tier
- What you get: domain-level technology clues.
- Constraint: limited calls.
- Best practice: run only on top-ranked domains.

2. Wappalyzer free tier
- What you get: additional technology fingerprints.
- Constraint: low free quota.
- Best practice: use as secondary validator, not first-pass scanner.

3. Public DNS + security headers + known SaaS subdomains (self-derived)
- What you get: indirect stack hints (for example `*.myshopify.com`, `cdn.segment.com`).
- Access: free through your own HTTP/DNS checks.
- Best practice: confidence-weighted inference, not hard truth.

## D) Contact discovery and verification

1. Hunter domain-search (official API)
- What you get: role-linked business emails by domain, confidence score.
- Constraint: free quota limits.
- Best practice: only run after company-level scoring.

2. Apollo freemium credits
- What you get: rich people/company search.
- Constraint: credit-based.
- Best practice: reserve for final contact fill or missing fields only.

3. Company team pages + LinkedIn company page links (manual/assisted)
- What you get: role and org context.
- Constraint: scraping restrictions on some platforms.
- Best practice: use official APIs where available and manual review for sensitive sources.

## 3) Cloudflare and anti-bot: what to do in practice

## Do this (recommended)

1. Official API first
- If the site has API/docs, use API only.

2. Passive public data ingestion
- Use JSON feeds, sitemap URLs, RSS, or public endpoints before HTML parsing.

3. Respectful HTTP collection
- Low request rate, retries with backoff, identify user-agent.

4. Build fallback ladders
- Example ladder:
  - Primary: API endpoint.
  - Secondary: alternate source API for same signal.
  - Tertiary: manual import CSV.

5. Track provenance
- For every field: source, URL, timestamp, extraction method.

## Do not do this

1. Bypass protections or attack anti-bot controls.
2. Aggressive headless scraping where ToS disallows automation.
3. High-volume scraping from a single domain in a short window.

## 4) Free-source execution plan for your prospecting agent

## Stage 1: Build candidate companies (free)

- GitHub org search by ICP keywords and tech terms.
- Hacker News search over story titles/links by same keywords.
- Product Hunt category/keyword pull (if token available).
- OpenCorporates verification merge for legal identity.

Output: deduped company/domain pool with source counts.

## Stage 2: Add intent and fit scoring (free)

Scoring signals:
- Keyword/industry match score.
- Recent activity score (HN/Product Hunt recency).
- Hiring-intent score (Greenhouse/Lever roles).
- Tech-fit score (BuiltWith/Wappalyzer if available).

Output: ranked company list with reasons.

## Stage 3: Contact enrichment (quota-limited)

- Query Hunter for top N domains only.
- Use Apollo only when Hunter misses target persona fields.
- Cache each successful domain/person response.

Output: contact candidates linked to scored companies.

## Stage 4: Review queue

- Export `prospect_queue.json` and `prospect_queue.csv`.
- Keep `review_required` default status.
- Include personalization hints but no message sending.

## 5) Data model fields you should store

Minimum for strong personalization later:

- company_name
- company_domain
- company_location
- company_industry
- company_size_hint
- technologies_detected[]
- hiring_signals[]
- activity_signals[]
- contact_name
- contact_title
- contact_email
- contact_linkedin
- source_list[]
- confidence_score
- review_status
- evidence[] (URL + snippet + timestamp)

## 6) Source reliability ranking (for demo quality)

Highest confidence:
- Official API responses with structured schema.

Medium confidence:
- Public structured feeds and consistent company pages.

Lower confidence:
- Inferred technology signals and community lists without verification.

Rule: require at least one high-confidence source before lead enters top outreach queue.

## 7) Hackathon-safe compliance checklist

1. Reviewed queue only, no auto-send.
2. Respect each source Terms and robots policy.
3. Keep attribution for open datasets.
4. Store opt-out and compliance fields in later outreach stage.
5. Use role relevance for personalization quality (not only first-name insertion).

## 8) Immediate practical stack (free-first)

Use this stack first:

1. Discovery: GitHub + Hacker News + Product Hunt (if token) + OpenCorporates.
2. Intent: Greenhouse + Lever hiring signals.
3. Contacts: Hunter first, Apollo fallback.
4. Output: ranked review queue with evidence trails.

This gives a convincing end-to-end prospecting story for a startup-sales intelligence demo without paid enterprise subscriptions.
