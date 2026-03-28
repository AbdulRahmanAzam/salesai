import sys, json, time
sys.path.insert(0, 'src')
from prospecting_agent.config import get_settings
from prospecting_agent.models import ICP
from prospecting_agent.pipeline import run_prospecting
from pathlib import Path

icp = ICP(
    product_name='Test DevOps Tool',
    product_pitch='Platform engineering for Kubernetes teams',
    industries=['SaaS'],
    persona_titles=['CTO', 'VP Engineering'],
    keywords=['kubernetes', 'devops'],
    tech_stack=['kubernetes'],
    max_companies=5,
    max_contacts=10,
)
settings = get_settings()
start = time.time()
result = run_prospecting(icp, settings, Path('output/test'), max_leads=5, use_llm_scoring=False)
elapsed = time.time() - start
print(f'Pipeline completed in {elapsed:.1f}s')
print(f'Companies: {result["companies"]}')
print(f'Contacts: {result["contacts"]}')
print(f'Drafts: {result["drafts"]}')
