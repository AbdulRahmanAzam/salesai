"""
Comprehensive integration & unit test suite for the Sales Intelligence Pipeline.
Tests all components with MOCK DATA only — no real API calls.

Run: python tests/test_all.py
"""
from __future__ import annotations

import json
import os
import sys
import tempfile
import time
from dataclasses import asdict
from pathlib import Path

# Ensure src/ is importable
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

# Force mock fallback and disable real API keys for testing
os.environ["ENABLE_MOCK_FALLBACK"] = "true"
os.environ.setdefault("APOLLO_API_KEY", "")
os.environ.setdefault("HUNTER_API_KEY", "")
os.environ.setdefault("SERPER_API_KEY", "")
os.environ.setdefault("GOOGLE_CSE_API_KEY", "")
os.environ.setdefault("GOOGLE_CSE_CX", "")
os.environ.setdefault("GITHUB_TOKEN", "")
os.environ.setdefault("PRODUCTHUNT_TOKEN", "")
os.environ.setdefault("OPENCORPORATES_API_TOKEN", "")
os.environ.setdefault("PROSPECTING_LLM_API_KEY", "")
os.environ.setdefault("PROSPECTING_LLM_BASE_URL", "https://inference.do-ai.run/v1")
os.environ.setdefault("PROSPECTING_LLM_MODEL", "openai-gpt-oss-120b")

# ──────────────── Test Framework ────────────────

passed = 0
failed = 0
errors: list[str] = []


def test(name: str):
    """Decorator that runs a test function and tracks pass/fail."""
    def wrapper(fn):
        global passed, failed
        try:
            fn()
            passed += 1
            print(f"  [PASS] {name}")
        except Exception as exc:
            failed += 1
            errors.append(f"{name}: {exc}")
            print(f"  [FAIL] {name} — {exc}")
    return wrapper


def assert_eq(a, b, msg=""):
    if a != b:
        raise AssertionError(f"Expected {a!r} == {b!r}" + (f" ({msg})" if msg else ""))


def assert_true(val, msg=""):
    if not val:
        raise AssertionError(f"Expected truthy, got {val!r}" + (f" ({msg})" if msg else ""))


def assert_gt(a, b, msg=""):
    if not (a > b):
        raise AssertionError(f"Expected {a} > {b}" + (f" ({msg})" if msg else ""))


def assert_gte(a, b, msg=""):
    if not (a >= b):
        raise AssertionError(f"Expected {a} >= {b}" + (f" ({msg})" if msg else ""))


def assert_in(item, collection, msg=""):
    if item not in collection:
        raise AssertionError(f"Expected {item!r} in collection" + (f" ({msg})" if msg else ""))


def assert_isinstance(obj, cls, msg=""):
    if not isinstance(obj, cls):
        raise AssertionError(f"Expected {type(obj).__name__} to be {cls.__name__}" + (f" ({msg})" if msg else ""))


# ════════════════════════════════════════════════
# SECTION 1: DATA MODELS
# ════════════════════════════════════════════════
print("\n═══ 1. DATA MODELS ═══")

from prospecting_agent.models import ICP, Company, Contact, ProspectDraft


@test("ICP creation with defaults")
def _():
    icp = ICP(product_name="TestProd", product_pitch="A test pitch")
    assert_eq(icp.product_name, "TestProd")
    assert_eq(icp.max_companies, 75)
    assert_eq(icp.max_contacts, 200)
    assert_eq(icp.industries, [])
    assert_eq(icp.tech_stack, [])


@test("ICP creation with full fields")
def _():
    icp = ICP(
        product_name="DevOps Platform",
        product_pitch="Reduce MTTR",
        industries=["SaaS", "Fintech"],
        employee_ranges=["11,50", "51,200"],
        locations=["United States"],
        persona_titles=["CTO", "VP Engineering"],
        tech_stack=["kubernetes", "terraform"],
        keywords=["incident response", "platform engineering"],
    )
    assert_eq(len(icp.industries), 2)
    assert_eq(len(icp.persona_titles), 2)
    assert_in("kubernetes", icp.tech_stack)


@test("Company key() deduplication by domain")
def _():
    c1 = Company(name="Datadog", domain="datadog.com")
    c2 = Company(name="DATADOG Inc", domain="DATADOG.COM")
    assert_eq(c1.key(), c2.key())


@test("Company key() fallback to name")
def _():
    c = Company(name="Mystery Corp", domain=None)
    assert_eq(c.key(), "mystery corp")


@test("Contact key() format")
def _():
    c = Contact(full_name="John Doe", title="CTO", company_name="Acme", company_domain="acme.com")
    assert_eq(c.key(), "john doe|acme.com")


@test("Contact key() fallback to company_name")
def _():
    c = Contact(full_name="Jane", title="CEO", company_name="Foo Corp", company_domain=None)
    assert_eq(c.key(), "jane|foo corp")


@test("ProspectDraft serialization")
def _():
    contact = Contact(full_name="Test User", title="CTO", company_name="TestCo", company_domain="test.com")
    company = Company(name="TestCo", domain="test.com")
    draft = ProspectDraft(contact=contact, company=company, score=75.0, reasons=["Title match"])
    record = draft.to_record()
    assert_eq(record["score"], 75.0)
    assert_eq(record["contact"]["full_name"], "Test User")
    assert_eq(record["company"]["domain"], "test.com")
    assert_eq(record["status"], "review_required")
    assert_true(record["generated_at"])


@test("ProspectDraft with None company")
def _():
    contact = Contact(full_name="No Company", title="Freelancer", company_name="Unknown", company_domain=None)
    draft = ProspectDraft(contact=contact, company=None, score=10.0, reasons=["Weak match"])
    record = draft.to_record()
    assert_eq(record["company"], None)


# ════════════════════════════════════════════════
# SECTION 2: CONFIGURATION
# ════════════════════════════════════════════════
print("\n═══ 2. CONFIGURATION ═══")

from prospecting_agent.config import Settings, get_settings


@test("Settings loads from environment")
def _():
    s = get_settings()
    assert_isinstance(s, Settings)
    assert_true(s.enable_mock_fallback, "mock fallback should be enabled")


@test("Settings types are correct")
def _():
    s = get_settings()
    assert_isinstance(s.http_timeout_seconds, int)
    assert_isinstance(s.max_source_results, int)
    assert_isinstance(s.enable_mock_fallback, bool)


@test("Settings LLM defaults")
def _():
    s = get_settings()
    assert_true(s.llm_base_url)
    assert_true(s.llm_model)


# ════════════════════════════════════════════════
# SECTION 3: MOCK DATA SOURCES
# ════════════════════════════════════════════════
print("\n═══ 3. MOCK DATA SOURCES ═══")

from prospecting_agent.sources.mock_data import MockCompanySource, MockContactSource


@test("MockCompanySource returns companies")
def _():
    icp = ICP(product_name="Test", product_pitch="Test", industries=["SaaS"])
    source = MockCompanySource()
    assert_eq(source.name, "mock_fallback")
    companies = source.find_companies(icp)
    assert_gt(len(companies), 0, "should return at least some companies")
    for c in companies:
        assert_isinstance(c, Company)
        assert_eq(c.source, "mock_fallback")
        assert_true(c.name)
        assert_true(c.domain)


@test("MockCompanySource ICP filtering — SaaS+Fintech")
def _():
    icp = ICP(
        product_name="Test",
        product_pitch="Test",
        industries=["SaaS", "Fintech"],
        keywords=["payments", "infrastructure"],
        persona_titles=["CTO"],
    )
    companies = MockCompanySource().find_companies(icp)
    assert_gt(len(companies), 5, "should find multiple matching companies")
    # Companies should be ICP-relevant
    domains = [c.domain for c in companies]
    # Stripe and Plaid are Fintech companies that should match
    assert_true(
        any("stripe" in d or "plaid" in d or "brex" in d for d in domains),
        "should find at least one fintech company",
    )


@test("MockCompanySource respects exclude_domains")
def _():
    icp = ICP(
        product_name="Test",
        product_pitch="Test",
        industries=["SaaS"],
        exclude_domains=["stripe.com", "datadog.com"],
    )
    companies = MockCompanySource().find_companies(icp)
    domains = {c.domain for c in companies}
    assert_true("stripe.com" not in domains, "stripe.com should be excluded")
    assert_true("datadog.com" not in domains, "datadog.com should be excluded")


@test("MockContactSource returns contacts")
def _():
    icp = ICP(product_name="Test", product_pitch="Test", persona_titles=["CTO", "VP Engineering"])
    companies = [Company(name="Stripe", domain="stripe.com"), Company(name="Datadog", domain="datadog.com")]
    source = MockContactSource()
    assert_eq(source.name, "mock_fallback")
    contacts = source.find_contacts(icp, companies)
    assert_gt(len(contacts), 0, "should return contacts")
    for c in contacts:
        assert_isinstance(c, Contact)
        assert_eq(c.source, "mock_fallback")
        assert_true(c.full_name)
        assert_true(c.title)


@test("MockContactSource ICP scoring — DevOps titles rank higher")
def _():
    icp = ICP(
        product_name="DevOps Platform",
        product_pitch="Reduce MTTR",
        persona_titles=["DevOps Manager", "SRE Lead"],
        keywords=["incident response", "observability"],
    )
    companies = [Company(name="Datadog", domain="datadog.com")]
    contacts = MockContactSource().find_contacts(icp, companies)
    # DevOps/SRE titles should be present in results
    titles = [c.title.lower() for c in contacts if c.title]
    assert_true(
        any("devops" in t or "sre" in t for t in titles),
        "should have DevOps/SRE contacts",
    )


@test("MockContactSource provides emails and LinkedIn")
def _():
    icp = ICP(product_name="Test", product_pitch="Test")
    contacts = MockContactSource().find_contacts(icp, [])
    with_email = sum(1 for c in contacts if c.email)
    with_linkedin = sum(1 for c in contacts if c.linkedin_url)
    assert_gt(with_email, 0, "should have contacts with emails")
    assert_gt(with_linkedin, 0, "should have contacts with LinkedIn")


# ════════════════════════════════════════════════
# SECTION 4: SCORING ENGINE
# ════════════════════════════════════════════════
print("\n═══ 4. SCORING ENGINE ═══")

from prospecting_agent.scoring import score_contact


@test("Score: persona title match yields +30")
def _():
    icp = ICP(product_name="Test", product_pitch="Test", persona_titles=["CTO"])
    contact = Contact(full_name="A B", title="CTO", company_name="X", company_domain="x.com")
    score, reasons = score_contact(contact, icp)
    assert_true(any("Persona title" in r for r in reasons))
    assert_gte(score, 30)


@test("Score: keyword match in company description")
def _():
    icp = ICP(product_name="Test", product_pitch="Test", keywords=["incident response"])
    company = Company(name="X", domain="x.com", description="We provide incident response tools")
    contact = Contact(full_name="A B", title="Engineer", company_name="X", company_domain="x.com")
    score, reasons = score_contact(contact, icp, company)
    assert_true(any("keyword" in r.lower() for r in reasons))


@test("Score: email available yields +15")
def _():
    icp = ICP(product_name="Test", product_pitch="Test")
    contact = Contact(full_name="A B", title="Dev", company_name="X", company_domain="x.com", email="a@x.com")
    score, reasons = score_contact(contact, icp)
    assert_true(any("Email" in r for r in reasons))
    assert_gte(score, 15)


@test("Score: LinkedIn profile yields +10")
def _():
    icp = ICP(product_name="Test", product_pitch="Test")
    contact = Contact(
        full_name="A B", title="Dev", company_name="X", company_domain="x.com",
        linkedin_url="https://linkedin.com/in/ab",
    )
    score, reasons = score_contact(contact, icp)
    assert_true(any("LinkedIn" in r for r in reasons))


@test("Score: guessed LinkedIn yields only +3")
def _():
    icp = ICP(product_name="Test", product_pitch="Test")
    contact = Contact(
        full_name="A B", title="Dev", company_name="X", company_domain="x.com",
        linkedin_url="https://linkedin.com/in/a-b",
        signals=["LinkedIn URL guessed from name (unverified)"],
    )
    score, reasons = score_contact(contact, icp)
    assert_true(any("guessed" in r.lower() for r in reasons))


@test("Score: tech stack overlap")
def _():
    icp = ICP(product_name="Test", product_pitch="Test", tech_stack=["kubernetes", "terraform"])
    company = Company(name="X", domain="x.com", technologies=["kubernetes", "docker", "terraform"])
    contact = Contact(full_name="A B", title="Dev", company_name="X", company_domain="x.com")
    score, reasons = score_contact(contact, icp, company)
    assert_true(any("Tech overlap" in r for r in reasons))


@test("Score: multi-source verification bonus")
def _():
    icp = ICP(product_name="Test", product_pitch="Test")
    contact = Contact(
        full_name="A B", title="Dev", company_name="X", company_domain="x.com",
        source="apollo+hunter+webscraper",
    )
    score, reasons = score_contact(contact, icp)
    assert_true(any("3 sources" in r for r in reasons))
    assert_gte(score, 18)


@test("Score: high confidence boost")
def _():
    icp = ICP(product_name="Test", product_pitch="Test")
    contact = Contact(
        full_name="A B", title="Dev", company_name="X", company_domain="x.com",
        confidence=0.95,
    )
    score, reasons = score_contact(contact, icp)
    assert_true(any("confidence" in r.lower() for r in reasons))


@test("Score: employee range match")
def _():
    icp = ICP(product_name="Test", product_pitch="Test", employee_ranges=["51,200"])
    company = Company(name="X", domain="x.com", employee_range="51,200")
    contact = Contact(full_name="A B", title="Dev", company_name="X", company_domain="x.com")
    score, reasons = score_contact(contact, icp, company)
    assert_true(any("size" in r.lower() for r in reasons))


@test("Score: ideal lead (CTO + email + LinkedIn + keywords + tech)")
def _():
    icp = ICP(
        product_name="DevOps Platform",
        product_pitch="MTTR reduction",
        persona_titles=["CTO"],
        keywords=["observability"],
        tech_stack=["kubernetes"],
        employee_ranges=["51,200"],
    )
    company = Company(
        name="GoodCo", domain="good.com",
        description="We do observability",
        technologies=["kubernetes", "terraform"],
        employee_range="51,200",
    )
    contact = Contact(
        full_name="Jane Doe", title="CTO", company_name="GoodCo", company_domain="good.com",
        email="jane@good.com",
        linkedin_url="https://linkedin.com/in/janedoe",
        confidence=0.95,
        source="apollo+hunter",
    )
    score, reasons = score_contact(contact, icp, company)
    assert_gte(score, 70, "ideal lead should score 70+")
    assert_gte(len(reasons), 5, "should have multiple match reasons")


@test("Score: weak lead with no match")
def _():
    icp = ICP(
        product_name="AI Tool",
        product_pitch="AI inference",
        persona_titles=["Data Scientist"],
        keywords=["machine learning"],
    )
    contact = Contact(
        full_name="Bob", title="Receptionist", company_name="Gym", company_domain="gym.com",
        source="unknown",
    )
    score, reasons = score_contact(contact, icp)
    assert_true(score < 30, "weak lead should score below 30")


@test("Score: never exceeds 100")
def _():
    icp = ICP(
        product_name="P", product_pitch="P",
        persona_titles=["CTO"],
        keywords=["a", "b", "c", "d", "e", "f"],
        tech_stack=["k8s", "tf", "docker"],
        employee_ranges=["51,200"],
    )
    company = Company(
        name="X", domain="x.com",
        description="a b c d e f",
        technologies=["k8s", "tf", "docker"],
        employee_range="51,200",
    )
    contact = Contact(
        full_name="A B", title="CTO", company_name="X", company_domain="x.com",
        email="a@x.com", linkedin_url="https://linkedin.com/in/ab",
        confidence=0.99, source="apollo+hunter+webscraper",
        signals=["recent activity verified"],
    )
    score, _ = score_contact(contact, icp, company)
    assert_true(score <= 100, f"score should not exceed 100, got {score}")


# ════════════════════════════════════════════════
# SECTION 5: EVENT EMITTER
# ════════════════════════════════════════════════
print("\n═══ 5. EVENT EMITTER ═══")

import io
from event_emitter import emit_event, emit_step, emit_item, emit_summary, emit_error, make_callback


@test("emit_event writes JSON to stderr")
def _():
    old_stderr = sys.stderr
    buf = io.StringIO()
    sys.stderr = buf
    try:
        emit_event("test_event", data={"foo": "bar"}, extra=42)
    finally:
        sys.stderr = old_stderr
    line = buf.getvalue().strip()
    parsed = json.loads(line)
    assert_eq(parsed["event"], "test_event")
    assert_eq(parsed["foo"], "bar")
    assert_eq(parsed["extra"], 42)


@test("emit_step format")
def _():
    old_stderr = sys.stderr
    buf = io.StringIO()
    sys.stderr = buf
    try:
        emit_step(0, "running", "Searching...")
    finally:
        sys.stderr = old_stderr
    parsed = json.loads(buf.getvalue().strip())
    assert_eq(parsed["event"], "step")
    assert_eq(parsed["index"], 0)
    assert_eq(parsed["status"], "running")
    assert_eq(parsed["label"], "Searching...")


@test("emit_item with dataclass")
def _():
    contact = Contact(full_name="Test", title="CTO", company_name="Co", company_domain="co.com")
    draft = ProspectDraft(contact=contact, company=None, score=50.0, reasons=["test"])
    old_stderr = sys.stderr
    buf = io.StringIO()
    sys.stderr = buf
    try:
        emit_item(draft)
    finally:
        sys.stderr = old_stderr
    parsed = json.loads(buf.getvalue().strip())
    assert_eq(parsed["event"], "item")
    assert_eq(parsed["contact"]["full_name"], "Test")
    assert_eq(parsed["score"], 50.0)


@test("emit_summary format")
def _():
    old_stderr = sys.stderr
    buf = io.StringIO()
    sys.stderr = buf
    try:
        emit_summary({"companies": 10, "contacts": 5, "drafts": 3})
    finally:
        sys.stderr = old_stderr
    parsed = json.loads(buf.getvalue().strip())
    assert_eq(parsed["event"], "summary")
    assert_eq(parsed["companies"], 10)


@test("emit_error format")
def _():
    old_stderr = sys.stderr
    buf = io.StringIO()
    sys.stderr = buf
    try:
        emit_error("Something went wrong")
    finally:
        sys.stderr = old_stderr
    parsed = json.loads(buf.getvalue().strip())
    assert_eq(parsed["event"], "error")
    assert_eq(parsed["message"], "Something went wrong")


@test("make_callback returns None when disabled")
def _():
    cb = make_callback(False)
    assert_eq(cb, None)


@test("make_callback returns callable when enabled")
def _():
    cb = make_callback(True)
    assert_true(callable(cb))


# ════════════════════════════════════════════════
# SECTION 6: PIPELINE HELPERS
# ════════════════════════════════════════════════
print("\n═══ 6. PIPELINE HELPERS ═══")

from prospecting_agent.pipeline import (
    _run_with_timeout,
    _collect_companies,
    _collect_contacts,
    _build_drafts,
    _merge_company,
    _merge_contact,
    _fuzzy_name_match,
    _build_company_sources,
    _build_contact_sources,
)


@test("_run_with_timeout: completes within timeout")
def _():
    def fast():
        return [1, 2, 3]
    result = _run_with_timeout(fast, timeout=5, label="test")
    assert_eq(result, [1, 2, 3])


@test("_run_with_timeout: returns [] on timeout")
def _():
    def slow():
        time.sleep(10)
        return [1]
    result = _run_with_timeout(slow, timeout=1, label="slow_test")
    assert_eq(result, [])


@test("_run_with_timeout: propagates exceptions")
def _():
    def bad():
        raise ValueError("boom")
    try:
        _run_with_timeout(bad, timeout=5, label="bad_test")
        raise AssertionError("Should have raised ValueError")
    except ValueError as e:
        assert_eq(str(e), "boom")


@test("_fuzzy_name_match: exact match")
def _():
    assert_true(_fuzzy_name_match("john doe", "john doe"))


@test("_fuzzy_name_match: initial match")
def _():
    assert_true(_fuzzy_name_match("j doe", "john doe"))


@test("_fuzzy_name_match: different last names don't match")
def _():
    assert_true(not _fuzzy_name_match("john doe", "john smith"))


@test("_merge_company: combines fields")
def _():
    a = Company(name="Short", domain="x.com", location="US", technologies=["k8s"])
    b = Company(name="Longer Name", domain=None, industry="SaaS", technologies=["docker"])
    merged = _merge_company(a, b)
    assert_eq(merged.name, "Longer Name")
    assert_eq(merged.domain, "x.com")
    assert_eq(merged.location, "US")
    assert_eq(merged.industry, "SaaS")
    assert_in("k8s", merged.technologies)
    assert_in("docker", merged.technologies)
    assert_true("+" in merged.source, "source should be combined")


@test("_merge_contact: combines fields")
def _():
    a = Contact(full_name="John", title="CTO", company_name="X", company_domain="x.com", email="j@x.com")
    b = Contact(full_name="John Doe", title=None, company_name="X Corp", company_domain=None,
                linkedin_url="https://linkedin.com/in/johndoe", confidence=0.9)
    merged = _merge_contact(a, b)
    assert_eq(merged.full_name, "John Doe")
    assert_eq(merged.title, "CTO")
    assert_eq(merged.email, "j@x.com")
    assert_eq(merged.linkedin_url, "https://linkedin.com/in/johndoe")
    assert_eq(merged.confidence, 0.9)


@test("_build_company_sources: includes mock when enabled")
def _():
    from prospecting_agent.http_client import HttpClient
    s = get_settings()
    s.enable_mock_fallback = True
    s.apollo_api_key = ""
    s.serper_api_key = ""
    s.google_cse_cx = ""
    s.producthunt_token = ""
    icp = ICP(product_name="T", product_pitch="T")
    sources = _build_company_sources(HttpClient(timeout_seconds=5), s, icp)
    names = [src.name for src in sources]
    assert_in("mock_fallback", names, "mock source should be in chain")


@test("_build_contact_sources: includes mock when enabled")
def _():
    from prospecting_agent.http_client import HttpClient
    s = get_settings()
    s.enable_mock_fallback = True
    s.apollo_api_key = ""
    s.hunter_api_key = ""
    s.serper_api_key = ""
    s.llm_api_key = ""
    sources = _build_contact_sources(HttpClient(timeout_seconds=5), s)
    names = [src.name for src in sources]
    assert_in("mock_fallback", names, "mock source should be in chain")


@test("_collect_companies: with mock source only")
def _():
    icp = ICP(
        product_name="Test", product_pitch="Test",
        industries=["SaaS"], max_companies=20,
    )
    companies = _collect_companies(icp, [MockCompanySource()])
    assert_gt(len(companies), 0, "should collect companies from mock")
    assert_true(len(companies) <= 20, "should respect max_companies")
    for c in companies:
        assert_isinstance(c, Company)


@test("_collect_contacts: with mock source only")
def _():
    icp = ICP(
        product_name="Test", product_pitch="Test",
        persona_titles=["CTO"], max_contacts=50,
    )
    companies = [Company(name="Stripe", domain="stripe.com")]
    contacts = _collect_contacts(icp, companies, [MockContactSource()])
    assert_gt(len(contacts), 0, "should collect contacts from mock")
    for c in contacts:
        assert_isinstance(c, Contact)


@test("_build_drafts: scores and sorts by score descending")
def _():
    icp = ICP(
        product_name="DevOps", product_pitch="MTTR",
        persona_titles=["CTO"],
        keywords=["observability"],
    )
    contacts = [
        Contact(full_name="Best Lead", title="CTO", company_name="A", company_domain="a.com",
                email="best@a.com", linkedin_url="https://linkedin.com/in/best"),
        Contact(full_name="Weak Lead", title="Intern", company_name="B", company_domain="b.com"),
    ]
    company_index = {
        "a.com": Company(name="A", domain="a.com", description="observability"),
        "b.com": Company(name="B", domain="b.com"),
    }
    drafts = _build_drafts(icp, contacts, company_index, llm_scorer=None)
    assert_eq(len(drafts), 2)
    assert_gte(drafts[0].score, drafts[1].score, "should be sorted by score desc")
    assert_eq(drafts[0].contact.full_name, "Best Lead")


# ════════════════════════════════════════════════
# SECTION 7: ENRICHMENT (MOCK — no API calls)
# ════════════════════════════════════════════════
print("\n═══ 7. ENRICHMENT ═══")

from prospecting_agent.enrichment import ContactEnricher
from prospecting_agent.http_client import HttpClient


@test("ContactEnricher: guesses LinkedIn URL")
def _():
    enricher = ContactEnricher(http=HttpClient(timeout_seconds=5))
    contact = Contact(full_name="John Doe", title="CTO", company_name="X", company_domain="x.com")
    enriched = enricher.enrich(contact)
    assert_true(enriched.linkedin_url, "should guess LinkedIn URL")
    assert_in("linkedin.com/in/john-doe", enriched.linkedin_url)
    assert_true(any("guessed" in s.lower() for s in enriched.signals))


@test("ContactEnricher: skips email lookup without Hunter key")
def _():
    enricher = ContactEnricher(http=HttpClient(timeout_seconds=5), hunter_api_key=None)
    contact = Contact(full_name="No Email", title="Dev", company_name="X", company_domain="x.com")
    enriched = enricher.enrich(contact)
    assert_eq(enriched.email, None, "should not have email without Hunter key")


@test("ContactEnricher: preserves existing LinkedIn")
def _():
    enricher = ContactEnricher(http=HttpClient(timeout_seconds=5))
    contact = Contact(
        full_name="Has LinkedIn", title="CTO", company_name="X", company_domain="x.com",
        linkedin_url="https://linkedin.com/in/existing-profile",
    )
    enriched = enricher.enrich(contact)
    assert_eq(enriched.linkedin_url, "https://linkedin.com/in/existing-profile")


# ════════════════════════════════════════════════
# SECTION 8: FULL PIPELINE (MOCK ONLY)
# ════════════════════════════════════════════════
print("\n═══ 8. FULL PIPELINE (MOCK) ═══")

from prospecting_agent.pipeline import run_prospecting


@test("Full pipeline: mock-only produces leads")
def _():
    icp = ICP(
        product_name="DevOps Platform",
        product_pitch="Engineering teams reduce MTTR with alert intelligence",
        industries=["SaaS", "Fintech"],
        employee_ranges=["11,50", "51,200", "201,500"],
        persona_titles=["CTO", "VP Engineering", "DevOps Manager"],
        tech_stack=["kubernetes", "datadog", "aws"],
        keywords=["incident response", "platform engineering"],
        max_companies=20,
        max_contacts=50,
    )
    settings = get_settings()
    # Disable ALL real APIs
    settings.apollo_api_key = ""
    settings.hunter_api_key = ""
    settings.serper_api_key = ""
    settings.google_cse_api_key = ""
    settings.google_cse_cx = ""
    settings.github_token = ""
    settings.producthunt_token = ""
    settings.opencorporates_api_token = ""
    settings.llm_api_key = ""
    settings.enable_mock_fallback = True

    with tempfile.TemporaryDirectory() as tmpdir:
        summary = run_prospecting(
            icp, settings, Path(tmpdir),
            max_leads=5, use_llm_scoring=False,
        )
        assert_gt(summary["companies"], 0, "should find companies")
        assert_gt(summary["contacts"], 0, "should find contacts")
        assert_gt(summary["drafts"], 0, "should produce drafts")
        assert_true(summary["drafts"] <= 5, "should respect max_leads")

        # Check output files exist
        assert_true(Path(tmpdir, "prospect_queue.json").exists(), "queue JSON should exist")
        assert_true(Path(tmpdir, "prospect_queue.csv").exists(), "queue CSV should exist")
        assert_true(Path(tmpdir, "companies.json").exists(), "companies JSON should exist")

        # Verify JSON output content
        queue = json.loads(Path(tmpdir, "prospect_queue.json").read_text())
        assert_eq(len(queue), summary["drafts"])
        for lead in queue:
            assert_true(lead["score"] > 0, "lead should have positive score")
            assert_true(lead["contact"]["full_name"], "lead needs contact name")
            assert_eq(lead["status"], "review_required")


@test("Full pipeline: SSE events emitted with progress callback")
def _():
    icp = ICP(
        product_name="Test Tool",
        product_pitch="A test",
        industries=["SaaS"],
        persona_titles=["CTO"],
        max_companies=10,
        max_contacts=20,
    )
    settings = get_settings()
    settings.apollo_api_key = ""
    settings.hunter_api_key = ""
    settings.serper_api_key = ""
    settings.google_cse_api_key = ""
    settings.google_cse_cx = ""
    settings.github_token = ""
    settings.producthunt_token = ""
    settings.opencorporates_api_token = ""
    settings.llm_api_key = ""
    settings.enable_mock_fallback = True

    events: list[dict] = []
    old_stderr = sys.stderr
    sys.stderr = io.StringIO()  # Capture stderr to parse events

    try:
        cb = make_callback(True)
        with tempfile.TemporaryDirectory() as tmpdir:
            summary = run_prospecting(
                icp, settings, Path(tmpdir),
                max_leads=3, use_llm_scoring=False,
                progress=cb,
            )
    finally:
        captured = sys.stderr.getvalue()
        sys.stderr = old_stderr

    # Parse JSON events from stderr
    for line in captured.strip().split("\n"):
        line = line.strip()
        if not line:
            continue
        try:
            events.append(json.loads(line))
        except json.JSONDecodeError:
            pass

    event_types = [e.get("event") for e in events]
    assert_in("step", event_types, "should emit step events")
    assert_in("item", event_types, "should emit item events")
    assert_in("summary", event_types, "should emit summary event")

    step_events = [e for e in events if e["event"] == "step"]
    item_events = [e for e in events if e["event"] == "item"]
    assert_gte(len(step_events), 8, "should have at least 8 step events (5 phases × running+done)")
    assert_gt(len(item_events), 0, "should emit individual lead items")
    assert_true(len(item_events) <= 3, "should respect max_leads for item events")


@test("Full pipeline: CSV output is valid")
def _():
    icp = ICP(
        product_name="Test", product_pitch="Test",
        industries=["SaaS"], persona_titles=["CTO"],
        max_companies=10, max_contacts=20,
    )
    settings = get_settings()
    settings.apollo_api_key = ""
    settings.hunter_api_key = ""
    settings.serper_api_key = ""
    settings.google_cse_api_key = ""
    settings.google_cse_cx = ""
    settings.github_token = ""
    settings.producthunt_token = ""
    settings.opencorporates_api_token = ""
    settings.llm_api_key = ""
    settings.enable_mock_fallback = True

    with tempfile.TemporaryDirectory() as tmpdir:
        run_prospecting(icp, settings, Path(tmpdir), max_leads=3, use_llm_scoring=False)
        csv_path = Path(tmpdir, "prospect_queue.csv")
        assert_true(csv_path.exists())
        import csv as csvmod
        with open(csv_path, encoding="utf-8") as f:
            reader = csvmod.DictReader(f)
            rows = list(reader)
        assert_gt(len(rows), 0, "CSV should have rows")
        assert_in("score", rows[0], "CSV should have score column")
        assert_in("full_name", rows[0], "CSV should have full_name column")
        assert_in("email", rows[0], "CSV should have email column")


# ════════════════════════════════════════════════
# SECTION 9: RESEARCH AGENT MODELS
# ════════════════════════════════════════════════
print("\n═══ 9. RESEARCH AGENT MODELS ═══")

from research_agent.models import (
    NewsItem, ActivityItem, CompanyProfile, PersonProfile, ResearchDossier,
)


@test("ResearchDossier creation")
def _():
    d = ResearchDossier(
        prospect_score=80.0,
        prospect_reasons=["Title match"],
        contact_name="Jane Doe",
        contact_title="CTO",
        contact_company="TestCo",
        contact_email="jane@testco.com",
        contact_linkedin="https://linkedin.com/in/janedoe",
        company_profile=CompanyProfile(
            name="TestCo", domain="testco.com",
            description="A test company",
        ),
        person_profile=PersonProfile(full_name="Jane Doe"),
        talking_points=["Recent funding round"],
        pain_points=["Scaling infrastructure"],
        relevance_summary="Strong fit for DevOps tools",
        research_confidence=0.8,
    )
    assert_eq(d.contact_name, "Jane Doe")
    assert_eq(d.research_confidence, 0.8)
    assert_gt(len(d.talking_points), 0)


@test("CompanyProfile defaults")
def _():
    cp = CompanyProfile(name="X", domain="x.com")
    assert_eq(cp.description, None)
    assert_eq(cp.technologies, [])
    assert_eq(cp.competitors, [])
    assert_eq(cp.recent_news, [])


@test("PersonProfile defaults")
def _():
    pp = PersonProfile(full_name="Test Person")
    assert_eq(pp.skills, [])
    assert_eq(pp.recent_activity, [])


# ════════════════════════════════════════════════
# SECTION 10: PERSONALISATION AGENT MODELS
# ════════════════════════════════════════════════
print("\n═══ 10. PERSONALISATION AGENT MODELS ═══")

from personalisation_agent.models import OutreachDraft, PersonalisationResult


@test("OutreachDraft creation")
def _():
    draft = OutreachDraft(
        contact_name="Jane Doe",
        contact_title="CTO",
        contact_company="TestCo",
        contact_email="jane@testco.com",
        contact_linkedin="https://linkedin.com/in/janedoe",
        subject="Quick question about your infra",
        body="Hi Jane, I noticed TestCo is scaling...",
        personalization_score=75,
        personalization_signals=["Referenced recent funding"],
    )
    assert_eq(draft.contact_name, "Jane Doe")
    assert_eq(draft.personalization_score, 75)
    assert_eq(draft.status, "draft")


@test("PersonalisationResult creation")
def _():
    draft = OutreachDraft(
        contact_name="X", contact_title="Y", contact_company="Z",
        contact_email="x@z.com", contact_linkedin="https://linkedin.com/in/x",
        subject="Hi", body="Body",
        personalization_score=50, personalization_signals=[],
    )
    result = PersonalisationResult(
        draft=draft, dossier_used="dossier_1",
        icp_product="TestProd", icp_pitch="TestPitch",
    )
    assert_eq(result.icp_product, "TestProd")


# ════════════════════════════════════════════════
# SECTION 11: HTTP CLIENT
# ════════════════════════════════════════════════
print("\n═══ 11. HTTP CLIENT ═══")


@test("HttpClient initialization")
def _():
    client = HttpClient(timeout_seconds=10)
    assert_eq(client.timeout_seconds, 10)


@test("HttpClient has default timeout")
def _():
    client = HttpClient()
    assert_eq(client.timeout_seconds, 30)


# ════════════════════════════════════════════════
# SECTION 12: SERVER HEALTH CHECK (if running)
# ════════════════════════════════════════════════
print("\n═══ 12. SERVER INTEGRATION ═══")

import urllib.request
import urllib.error


@test("Express /api/health responds OK")
def _():
    try:
        req = urllib.request.Request("http://localhost:4000/api/health")
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode())
            assert_eq(data["status"], "ok")
            assert_eq(data["mongo"], "connected")
    except urllib.error.URLError:
        raise AssertionError("Express server not running on port 4000")


@test("Express /api/config/status responds with key status")
def _():
    try:
        req = urllib.request.Request("http://localhost:4000/api/config/status")
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode())
            assert_in("apollo", data)
            assert_in("hunter", data)
            assert_in("prospecting_llm", data)
    except urllib.error.URLError:
        raise AssertionError("Express server not running on port 4000")


@test("Express /api/prospecting/sessions responds (GET)")
def _():
    try:
        req = urllib.request.Request("http://localhost:4000/api/prospecting/sessions")
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode())
            assert_isinstance(data, list, "sessions should be a list")
    except urllib.error.URLError:
        raise AssertionError("Express server not running on port 4000")


@test("Express /api/research/sessions responds (GET)")
def _():
    try:
        req = urllib.request.Request("http://localhost:4000/api/research/sessions")
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode())
            assert_isinstance(data, list)
    except urllib.error.URLError:
        raise AssertionError("Express server not running on port 4000")


@test("Express /api/outreach/sessions responds (GET)")
def _():
    try:
        req = urllib.request.Request("http://localhost:4000/api/outreach/sessions")
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode())
            assert_isinstance(data, list)
    except urllib.error.URLError:
        raise AssertionError("Express server not running on port 4000")


@test("Express /api/tracking/sessions responds (GET)")
def _():
    try:
        req = urllib.request.Request("http://localhost:4000/api/tracking/sessions")
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode())
            assert_isinstance(data, list)
    except urllib.error.URLError:
        raise AssertionError("Express server not running on port 4000")


@test("Express /api/dashboard/summary responds")
def _():
    try:
        req = urllib.request.Request("http://localhost:4000/api/dashboard/summary")
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode())
            assert_isinstance(data, dict)
    except urllib.error.URLError:
        raise AssertionError("Express server not running on port 4000")


@test("Frontend responds on port 5173")
def _():
    try:
        req = urllib.request.Request("http://localhost:5173/")
        with urllib.request.urlopen(req, timeout=5) as resp:
            html = resp.read().decode()
            assert_true(len(html) > 100, "should return HTML content")
    except urllib.error.URLError:
        raise AssertionError("Vite frontend not running on port 5173")


# ════════════════════════════════════════════════
# RESULTS
# ════════════════════════════════════════════════
print("\n" + "═" * 50)
print(f"RESULTS: {passed} passed, {failed} failed out of {passed + failed} tests")
print("═" * 50)

if errors:
    print("\nFailed tests:")
    for e in errors:
        print(f"  ✗ {e}")
    print()

sys.exit(1 if failed > 0 else 0)
