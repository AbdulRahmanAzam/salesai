"""Mock data fallback sources.

Kick in automatically when real APIs return 0 results due to credit/quota
limits.  The data is realistic but clearly labelled ``source='mock_fallback'``
so the user knows it didn't come from a live API.

Both sources are ICP-aware: they score every record against the ICP's
industries, keywords, persona titles, tech stack, and employee ranges,
then return the best matches.
"""

from __future__ import annotations

from prospecting_agent.models import Company, Contact, ICP
from prospecting_agent.sources.base import CompanySource, ContactSource

# ---------------------------------------------------------------------------
# Built-in dataset — realistic B2B companies across common verticals
# ---------------------------------------------------------------------------

_COMPANIES: list[dict] = [
    # --- DevOps / Observability / Cloud ---
    {"name": "HashiCorp", "domain": "hashicorp.com", "industry": "Cloud Infrastructure", "employee_range": "1001,5000", "location": "San Francisco, CA", "technologies": ["Go", "Terraform", "Vault", "AWS", "Kubernetes"], "description": "Cloud infrastructure automation software for multi-cloud environments."},
    {"name": "Datadog", "domain": "datadoghq.com", "industry": "Observability", "employee_range": "1001,5000", "location": "New York, NY", "technologies": ["Go", "Python", "React", "Kubernetes", "AWS"], "description": "Monitoring and security platform for cloud-scale applications."},
    {"name": "Grafana Labs", "domain": "grafana.com", "industry": "Observability", "employee_range": "501,1000", "location": "New York, NY", "technologies": ["Go", "TypeScript", "Prometheus", "Kubernetes"], "description": "Open-source observability platform for metrics, logs, and traces."},
    {"name": "PagerDuty", "domain": "pagerduty.com", "industry": "Incident Management", "employee_range": "501,1000", "location": "San Francisco, CA", "technologies": ["Ruby", "Go", "AWS", "Kubernetes"], "description": "Digital operations management platform for real-time work."},
    {"name": "LaunchDarkly", "domain": "launchdarkly.com", "industry": "DevOps", "employee_range": "201,500", "location": "Oakland, CA", "technologies": ["Go", "TypeScript", "React", "AWS"], "description": "Feature management platform for modern software delivery."},
    {"name": "Snyk", "domain": "snyk.io", "industry": "Security", "employee_range": "501,1000", "location": "Boston, MA", "technologies": ["TypeScript", "Go", "Kubernetes", "Docker"], "description": "Developer-first security platform for code, dependencies, and containers."},
    {"name": "CircleCI", "domain": "circleci.com", "industry": "CI/CD", "employee_range": "201,500", "location": "San Francisco, CA", "technologies": ["Go", "Clojure", "Docker", "Kubernetes", "AWS"], "description": "Continuous integration and delivery platform for software teams."},
    {"name": "Honeycomb", "domain": "honeycomb.io", "industry": "Observability", "employee_range": "51,200", "location": "San Francisco, CA", "technologies": ["Go", "TypeScript", "Terraform"], "description": "Observability for distributed systems. Fast debugging of complex production systems."},
    {"name": "Env0", "domain": "env0.com", "industry": "DevOps", "employee_range": "51,200", "location": "Tel Aviv, Israel", "technologies": ["Terraform", "Kubernetes", "AWS", "TypeScript"], "description": "Self-service cloud management and Infrastructure as Code automation."},
    {"name": "Spacelift", "domain": "spacelift.io", "industry": "DevOps", "employee_range": "51,200", "location": "Remote", "technologies": ["Terraform", "Pulumi", "Go", "AWS"], "description": "Sophisticated CI/CD for infrastructure-as-code."},

    # --- SaaS / Productivity / Platform ---
    {"name": "Notion", "domain": "notion.so", "industry": "SaaS", "employee_range": "201,500", "location": "San Francisco, CA", "technologies": ["TypeScript", "React", "AWS", "PostgreSQL"], "description": "All-in-one workspace for notes, docs, and project management."},
    {"name": "Linear", "domain": "linear.app", "industry": "SaaS", "employee_range": "51,200", "location": "San Francisco, CA", "technologies": ["TypeScript", "React", "GraphQL", "PostgreSQL"], "description": "Issue tracking tool designed for high-performance teams."},
    {"name": "Retool", "domain": "retool.com", "industry": "SaaS", "employee_range": "201,500", "location": "San Francisco, CA", "technologies": ["TypeScript", "React", "PostgreSQL", "Docker"], "description": "Low-code platform for building internal tools."},
    {"name": "Vercel", "domain": "vercel.com", "industry": "SaaS", "employee_range": "201,500", "location": "San Francisco, CA", "technologies": ["Next.js", "React", "TypeScript", "Go"], "description": "Frontend cloud platform for deploying web applications."},
    {"name": "Supabase", "domain": "supabase.com", "industry": "SaaS", "employee_range": "51,200", "location": "Singapore", "technologies": ["TypeScript", "PostgreSQL", "Elixir", "Go"], "description": "Open-source Firebase alternative with Postgres database."},

    # --- Fintech ---
    {"name": "Stripe", "domain": "stripe.com", "industry": "Fintech", "employee_range": "5001,10000", "location": "San Francisco, CA", "technologies": ["Ruby", "Go", "React", "AWS", "Kubernetes"], "description": "Payment infrastructure for the internet."},
    {"name": "Plaid", "domain": "plaid.com", "industry": "Fintech", "employee_range": "501,1000", "location": "San Francisco, CA", "technologies": ["Go", "Python", "React", "AWS"], "description": "Financial data connectivity platform for fintech applications."},
    {"name": "Brex", "domain": "brex.com", "industry": "Fintech", "employee_range": "501,1000", "location": "San Francisco, CA", "technologies": ["Kotlin", "TypeScript", "AWS", "Kubernetes"], "description": "Corporate credit cards and spend management for startups."},
    {"name": "Ramp", "domain": "ramp.com", "industry": "Fintech", "employee_range": "201,500", "location": "New York, NY", "technologies": ["Python", "TypeScript", "React", "AWS"], "description": "Corporate card and spend management platform."},
    {"name": "Mercury", "domain": "mercury.com", "industry": "Fintech", "employee_range": "201,500", "location": "San Francisco, CA", "technologies": ["Haskell", "TypeScript", "React", "AWS"], "description": "Banking for startups and scaling companies."},

    # --- Cybersecurity ---
    {"name": "CrowdStrike", "domain": "crowdstrike.com", "industry": "Cybersecurity", "employee_range": "5001,10000", "location": "Austin, TX", "technologies": ["Go", "Python", "AWS", "Kubernetes"], "description": "Cloud-native endpoint protection and threat intelligence."},
    {"name": "Wiz", "domain": "wiz.io", "industry": "Cybersecurity", "employee_range": "501,1000", "location": "New York, NY", "technologies": ["Go", "TypeScript", "AWS", "Azure", "Kubernetes"], "description": "Cloud security platform providing full-stack visibility."},
    {"name": "Orca Security", "domain": "orca.security", "industry": "Cybersecurity", "employee_range": "201,500", "location": "Tel Aviv, Israel", "technologies": ["Python", "Go", "AWS", "Azure"], "description": "Agentless cloud security platform."},

    # --- AI / ML ---
    {"name": "Anthropic", "domain": "anthropic.com", "industry": "AI", "employee_range": "201,500", "location": "San Francisco, CA", "technologies": ["Python", "PyTorch", "AWS", "Kubernetes"], "description": "AI safety company building reliable, interpretable AI systems."},
    {"name": "Hugging Face", "domain": "huggingface.co", "industry": "AI", "employee_range": "201,500", "location": "New York, NY", "technologies": ["Python", "PyTorch", "Rust", "TypeScript"], "description": "Open-source AI platform for NLP models and datasets."},
    {"name": "Weights & Biases", "domain": "wandb.ai", "industry": "AI", "employee_range": "201,500", "location": "San Francisco, CA", "technologies": ["Python", "Go", "React", "AWS"], "description": "ML experiment tracking and model management platform."},
    {"name": "Scale AI", "domain": "scale.com", "industry": "AI", "employee_range": "501,1000", "location": "San Francisco, CA", "technologies": ["Python", "Go", "React", "AWS", "Kubernetes"], "description": "Data platform for AI, providing high-quality training data."},
    {"name": "Replicate", "domain": "replicate.com", "industry": "AI", "employee_range": "11,50", "location": "San Francisco, CA", "technologies": ["Python", "Go", "Docker", "Kubernetes"], "description": "Run and fine-tune open-source AI models with a cloud API."},

    # --- E-commerce / Marketplace ---
    {"name": "Shopify", "domain": "shopify.com", "industry": "E-commerce", "employee_range": "5001,10000", "location": "Ottawa, Canada", "technologies": ["Ruby", "React", "Go", "Kubernetes"], "description": "Commerce platform for online and retail businesses."},
    {"name": "BigCommerce", "domain": "bigcommerce.com", "industry": "E-commerce", "employee_range": "501,1000", "location": "Austin, TX", "technologies": ["PHP", "React", "AWS", "Kubernetes"], "description": "Open SaaS e-commerce platform for fast-growing brands."},

    # --- Healthcare / Healthtech ---
    {"name": "Veracyte", "domain": "veracyte.com", "industry": "Healthcare", "employee_range": "501,1000", "location": "South San Francisco, CA", "technologies": ["Python", "AWS", "R"], "description": "Genomic diagnostics company using AI for cancer detection."},
    {"name": "Hims & Hers", "domain": "forhims.com", "industry": "Healthcare", "employee_range": "1001,5000", "location": "San Francisco, CA", "technologies": ["React", "Python", "AWS", "Kubernetes"], "description": "Telehealth platform offering personalized health and wellness."},
]

# ---------------------------------------------------------------------------
# Built-in contacts — diverse personas across companies above
# ---------------------------------------------------------------------------

_CONTACTS: list[dict] = [
    # --- C-Suite / VP ---
    {"full_name": "Mitchell Hashimoto", "title": "Co-founder & CTO", "company_name": "HashiCorp", "company_domain": "hashicorp.com", "email": "mitchell@hashicorp.com", "linkedin_url": "https://linkedin.com/in/mitchellh", "confidence": 0.90},
    {"full_name": "Charity Majors", "title": "CTO", "company_name": "Honeycomb", "company_domain": "honeycomb.io", "email": "charity@honeycomb.io", "linkedin_url": "https://linkedin.com/in/charity-majors", "confidence": 0.92},
    {"full_name": "Olivier Pomel", "title": "CEO", "company_name": "Datadog", "company_domain": "datadoghq.com", "email": "olivier@datadoghq.com", "linkedin_url": "https://linkedin.com/in/olivierpomel", "confidence": 0.88},
    {"full_name": "Raj Dutt", "title": "CEO & Co-founder", "company_name": "Grafana Labs", "company_domain": "grafana.com", "email": "raj@grafana.com", "linkedin_url": "https://linkedin.com/in/rajdutt", "confidence": 0.85},
    {"full_name": "Jennifer Tejada", "title": "CEO", "company_name": "PagerDuty", "company_domain": "pagerduty.com", "email": "jennifer@pagerduty.com", "linkedin_url": "https://linkedin.com/in/jennifertejada", "confidence": 0.87},
    {"full_name": "Patrick Collison", "title": "CEO", "company_name": "Stripe", "company_domain": "stripe.com", "email": "patrick@stripe.com", "linkedin_url": "https://linkedin.com/in/patrickcollison", "confidence": 0.80},
    {"full_name": "Ivan Zhao", "title": "CEO & Co-founder", "company_name": "Notion", "company_domain": "notion.so", "email": "ivan@notion.so", "linkedin_url": "https://linkedin.com/in/ivanzhao", "confidence": 0.82},
    {"full_name": "Guillermo Rauch", "title": "CEO", "company_name": "Vercel", "company_domain": "vercel.com", "email": "guillermo@vercel.com", "linkedin_url": "https://linkedin.com/in/guillermo-rauch", "confidence": 0.85},
    {"full_name": "Dario Amodei", "title": "CEO", "company_name": "Anthropic", "company_domain": "anthropic.com", "email": "dario@anthropic.com", "linkedin_url": "https://linkedin.com/in/darioamodei", "confidence": 0.75},
    {"full_name": "Alexander Wang", "title": "CEO", "company_name": "Scale AI", "company_domain": "scale.com", "email": "alex@scale.com", "linkedin_url": "https://linkedin.com/in/alexanderwang", "confidence": 0.80},
    {"full_name": "George Kurtz", "title": "CEO", "company_name": "CrowdStrike", "company_domain": "crowdstrike.com", "email": "george@crowdstrike.com", "linkedin_url": "https://linkedin.com/in/georgekurtz", "confidence": 0.82},
    {"full_name": "Assaf Rappaport", "title": "CEO & Co-founder", "company_name": "Wiz", "company_domain": "wiz.io", "email": "assaf@wiz.io", "linkedin_url": "https://linkedin.com/in/assafrappaport", "confidence": 0.88},

    # --- VP Engineering / Head of Platform ---
    {"full_name": "Sarah Chen", "title": "VP Engineering", "company_name": "Datadog", "company_domain": "datadoghq.com", "email": "s.chen@datadoghq.com", "linkedin_url": "https://linkedin.com/in/sarah-chen-eng", "confidence": 0.80},
    {"full_name": "Marcus Johnson", "title": "VP Engineering", "company_name": "PagerDuty", "company_domain": "pagerduty.com", "email": "m.johnson@pagerduty.com", "linkedin_url": "https://linkedin.com/in/marcus-johnson-eng", "confidence": 0.78},
    {"full_name": "Emily Rodriguez", "title": "Head of Platform", "company_name": "LaunchDarkly", "company_domain": "launchdarkly.com", "email": "e.rodriguez@launchdarkly.com", "linkedin_url": "https://linkedin.com/in/emily-rodriguez-platform", "confidence": 0.76},
    {"full_name": "Alex Rivera", "title": "Head of Platform", "company_name": "Vercel", "company_domain": "vercel.com", "email": "a.rivera@vercel.com", "linkedin_url": "https://linkedin.com/in/alexrivera-platform", "confidence": 0.78},
    {"full_name": "Priya Patel", "title": "VP Engineering", "company_name": "Stripe", "company_domain": "stripe.com", "email": "priya@stripe.com", "linkedin_url": "https://linkedin.com/in/priya-patel-eng", "confidence": 0.82},
    {"full_name": "James Liu", "title": "Head of Platform", "company_name": "Brex", "company_domain": "brex.com", "email": "j.liu@brex.com", "linkedin_url": "https://linkedin.com/in/james-liu-platform", "confidence": 0.74},
    {"full_name": "Rachel Kim", "title": "VP Engineering", "company_name": "Linear", "company_domain": "linear.app", "email": "rachel@linear.app", "linkedin_url": "https://linkedin.com/in/rachel-kim-eng", "confidence": 0.76},
    {"full_name": "Daniel Fischer", "title": "VP Engineering", "company_name": "Wiz", "company_domain": "wiz.io", "email": "d.fischer@wiz.io", "linkedin_url": "https://linkedin.com/in/daniel-fischer-eng", "confidence": 0.80},

    # --- DevOps Manager / SRE / Platform Engineering ---
    {"full_name": "Kevin Park", "title": "DevOps Manager", "company_name": "HashiCorp", "company_domain": "hashicorp.com", "email": "k.park@hashicorp.com", "linkedin_url": "https://linkedin.com/in/kevin-park-devops", "confidence": 0.75},
    {"full_name": "Lisa Wang", "title": "SRE Lead", "company_name": "Grafana Labs", "company_domain": "grafana.com", "email": "l.wang@grafana.com", "linkedin_url": "https://linkedin.com/in/lisa-wang-sre", "confidence": 0.73},
    {"full_name": "Carlos Mendez", "title": "DevOps Manager", "company_name": "CircleCI", "company_domain": "circleci.com", "email": "c.mendez@circleci.com", "linkedin_url": "https://linkedin.com/in/carlos-mendez-devops", "confidence": 0.72},
    {"full_name": "Aisha Okafor", "title": "Platform Engineer Lead", "company_name": "Snyk", "company_domain": "snyk.io", "email": "a.okafor@snyk.io", "linkedin_url": "https://linkedin.com/in/aisha-okafor-platform", "confidence": 0.70},
    {"full_name": "Tom Anderson", "title": "SRE Manager", "company_name": "Datadog", "company_domain": "datadoghq.com", "email": "t.anderson@datadoghq.com", "linkedin_url": "https://linkedin.com/in/tom-anderson-sre", "confidence": 0.74},
    {"full_name": "Megan Lee", "title": "DevOps Lead", "company_name": "Env0", "company_domain": "env0.com", "email": "m.lee@env0.com", "linkedin_url": "https://linkedin.com/in/megan-lee-devops", "confidence": 0.71},
    {"full_name": "Ryan Cooper", "title": "Platform Engineering Manager", "company_name": "Spacelift", "company_domain": "spacelift.io", "email": "r.cooper@spacelift.io", "linkedin_url": "https://linkedin.com/in/ryan-cooper-platform", "confidence": 0.70},
    {"full_name": "Nina Sharma", "title": "DevOps Manager", "company_name": "Ramp", "company_domain": "ramp.com", "email": "n.sharma@ramp.com", "linkedin_url": "https://linkedin.com/in/nina-sharma-devops", "confidence": 0.72},
    {"full_name": "David Kim", "title": "SRE Lead", "company_name": "Plaid", "company_domain": "plaid.com", "email": "d.kim@plaid.com", "linkedin_url": "https://linkedin.com/in/david-kim-sre", "confidence": 0.73},
    {"full_name": "Sandra Reeves", "title": "DevOps Manager", "company_name": "Mercury", "company_domain": "mercury.com", "email": "s.reeves@mercury.com", "linkedin_url": "https://linkedin.com/in/sandra-reeves-devops", "confidence": 0.70},

    # --- Engineering Manager / Director ---
    {"full_name": "Chris Taylor", "title": "Engineering Director", "company_name": "Shopify", "company_domain": "shopify.com", "email": "c.taylor@shopify.com", "linkedin_url": "https://linkedin.com/in/chris-taylor-eng", "confidence": 0.80},
    {"full_name": "Yuki Tanaka", "title": "Engineering Manager", "company_name": "Supabase", "company_domain": "supabase.com", "email": "y.tanaka@supabase.com", "linkedin_url": "https://linkedin.com/in/yuki-tanaka-eng", "confidence": 0.72},
    {"full_name": "Amy Brooks", "title": "Engineering Director", "company_name": "CrowdStrike", "company_domain": "crowdstrike.com", "email": "a.brooks@crowdstrike.com", "linkedin_url": "https://linkedin.com/in/amy-brooks-eng", "confidence": 0.78},
    {"full_name": "Ben Foster", "title": "Engineering Manager", "company_name": "Retool", "company_domain": "retool.com", "email": "b.foster@retool.com", "linkedin_url": "https://linkedin.com/in/ben-foster-eng", "confidence": 0.74},
    {"full_name": "Lukas Weber", "title": "ML Engineering Lead", "company_name": "Weights & Biases", "company_domain": "wandb.ai", "email": "l.weber@wandb.ai", "linkedin_url": "https://linkedin.com/in/lukas-weber-ml", "confidence": 0.73},
    {"full_name": "Fatima Al-Rashidi", "title": "Engineering Manager", "company_name": "Anthropic", "company_domain": "anthropic.com", "email": "f.alrashidi@anthropic.com", "linkedin_url": "https://linkedin.com/in/fatima-alrashidi-eng", "confidence": 0.72},
    {"full_name": "Jason Nguyen", "title": "Engineering Manager", "company_name": "Orca Security", "company_domain": "orca.security", "email": "j.nguyen@orca.security", "linkedin_url": "https://linkedin.com/in/jason-nguyen-eng", "confidence": 0.70},
    {"full_name": "Sophie Martin", "title": "Engineering Director", "company_name": "Hugging Face", "company_domain": "huggingface.co", "email": "s.martin@huggingface.co", "linkedin_url": "https://linkedin.com/in/sophie-martin-eng", "confidence": 0.76},
]


# ---------------------------------------------------------------------------
# Helpers — ICP-aware relevance scoring
# ---------------------------------------------------------------------------

def _score_company(company: dict, icp: ICP) -> float:
    """Return 0-100 relevance score for a mock company against the ICP."""
    score = 0.0
    ind = (company.get("industry") or "").lower()
    techs = [t.lower() for t in company.get("technologies", [])]
    desc = (company.get("description") or "").lower()
    loc = (company.get("location") or "").lower()
    emp = company.get("employee_range", "")

    # Industry match
    for icp_ind in icp.industries:
        if icp_ind.lower() in ind or ind in icp_ind.lower():
            score += 30
            break

    # Keyword match (in description or industry)
    kw_hits = 0
    for kw in icp.keywords:
        if kw.lower() in desc or kw.lower() in ind:
            kw_hits += 1
    score += min(25, kw_hits * 8)

    # Tech stack overlap
    tech_hits = 0
    for icp_tech in icp.tech_stack:
        if icp_tech.lower() in techs:
            tech_hits += 1
    score += min(20, tech_hits * 5)

    # Employee range match
    if emp and icp.employee_ranges:
        for er in icp.employee_ranges:
            if emp == er:
                score += 10
                break

    # Location match
    if loc and icp.locations:
        for icp_loc in icp.locations:
            if icp_loc.lower() in loc:
                score += 10
                break

    # Baseline — give every company a small score so we always have fallback
    score += 5
    return min(100.0, score)


def _score_contact(contact: dict, icp: ICP) -> float:
    """Return 0-100 relevance score for a mock contact against the ICP."""
    score = 0.0
    title = (contact.get("title") or "").lower()

    # Persona title match
    for pt in icp.persona_titles:
        pt_lower = pt.lower()
        # "CTO" in "Co-founder & CTO", "DevOps Manager" in "DevOps Manager"
        if pt_lower in title or any(w in title for w in pt_lower.split()):
            score += 40
            break

    # Keyword in title
    for kw in icp.keywords:
        if kw.lower() in title:
            score += 10
            break

    # Has email/LinkedIn → higher quality
    if contact.get("email"):
        score += 10
    if contact.get("linkedin_url"):
        score += 10

    score += 5  # baseline
    return min(100.0, score)


# ---------------------------------------------------------------------------
# Public source classes
# ---------------------------------------------------------------------------

class MockCompanySource(CompanySource):
    """Returns ICP-relevant companies from the built-in dataset."""

    name = "mock_fallback"

    def find_companies(self, icp: ICP) -> list[Company]:
        scored = []
        excludes = {d.lower() for d in (icp.exclude_domains or [])}

        for rec in _COMPANIES:
            domain = (rec.get("domain") or "").lower()
            if domain in excludes:
                continue
            relevance = _score_company(rec, icp)
            scored.append((relevance, rec))

        # Sort by relevance descending, take up to max_companies
        scored.sort(key=lambda t: t[0], reverse=True)
        limit = min(icp.max_companies, len(scored))
        results: list[Company] = []

        for relevance, rec in scored[:limit]:
            if relevance < 10:  # skip totally irrelevant
                continue
            results.append(Company(
                name=rec["name"],
                domain=rec.get("domain"),
                industry=rec.get("industry"),
                employee_range=rec.get("employee_range"),
                location=rec.get("location"),
                description=rec.get("description"),
                technologies=rec.get("technologies", []),
                source="mock_fallback",
                notes=[f"Mock fallback data (ICP relevance: {relevance:.0f}/100)"],
            ))
        print(f"  [mock] Returning {len(results)} companies from built-in dataset")
        return results


class MockContactSource(ContactSource):
    """Returns ICP-relevant contacts from the built-in dataset."""

    name = "mock_fallback"

    def find_contacts(self, icp: ICP, companies: list[Company]) -> list[Contact]:
        # Build set of company domains we have
        company_domains = {c.domain.lower() for c in companies if c.domain}

        scored = []
        for rec in _CONTACTS:
            domain = (rec.get("company_domain") or "").lower()
            relevance = _score_contact(rec, icp)
            # Bonus if contact's company is in our company list
            if domain in company_domains:
                relevance += 20
            scored.append((relevance, rec))

        scored.sort(key=lambda t: t[0], reverse=True)
        limit = min(icp.max_contacts, len(scored))
        results: list[Contact] = []

        for relevance, rec in scored[:limit]:
            if relevance < 15:  # skip very low relevance
                continue
            results.append(Contact(
                full_name=rec["full_name"],
                title=rec.get("title"),
                company_name=rec["company_name"],
                company_domain=rec.get("company_domain"),
                email=rec.get("email"),
                linkedin_url=rec.get("linkedin_url"),
                source="mock_fallback",
                confidence=rec.get("confidence", 0.5),
                signals=["Mock fallback — API credits exhausted"],
                research_notes=[f"From built-in dataset (ICP relevance: {relevance:.0f}/100). Verify before outreach."],
            ))
        print(f"  [mock] Returning {len(results)} contacts from built-in dataset")
        return results
