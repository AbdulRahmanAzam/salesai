from __future__ import annotations

import re

from prospecting_agent.http_client import HttpClient
from prospecting_agent.models import Company, ICP
from prospecting_agent.sources.base import CompanySource

_DOMAIN_RE = re.compile(r"https?://([^/]+)")


class HackerNewsSource(CompanySource):
    name = "hackernews"

    def __init__(self, http: HttpClient):
        self.http = http

    def find_companies(self, icp: ICP) -> list[Company]:
        # Build diverse search queries from ICP data
        queries: list[str] = []
        if icp.keywords:
            # Use individual keywords and pairs for broader coverage
            queries.append(" ".join(icp.keywords[:3]))
            for kw in icp.keywords[:3]:
                queries.append(kw)
        if icp.industries:
            queries.append(" ".join(icp.industries[:2]))
        if icp.search_queries:
            queries.extend(icp.search_queries[:3])
        if icp.product_name and icp.product_name not in queries:
            queries.append(icp.product_name)
        if not queries:
            queries.append(icp.product_name)
        # Deduplicate while preserving order
        seen_q: set[str] = set()
        unique_queries: list[str] = []
        for q in queries:
            ql = q.lower().strip()
            if ql not in seen_q:
                seen_q.add(ql)
                unique_queries.append(q)

        companies: list[Company] = []
        seen_domains: set[str] = set()

        for query in unique_queries:
            # Use HN Algolia search API (searches all stories, not just top 200)
            try:
                data = self.http.get(
                    "https://hn.algolia.com/api/v1/search",
                    params={
                        "query": query,
                        "tags": "story",
                        "hitsPerPage": min(20, icp.max_companies),
                    },
                )
            except Exception as exc:
                print(f"  [warn] HN Algolia search failed for '{query}': {exc}")
                continue

            for hit in data.get("hits", []):
                url = hit.get("url")
                domain = _extract_domain(url)
                if not domain or domain in seen_domains:
                    continue
                # Skip big aggregator domains (not real companies)
                if domain in _SKIP_DOMAINS:
                    continue
                seen_domains.add(domain)
                title = hit.get("title") or domain.split(".")[0].capitalize()
                companies.append(
                    Company(
                        name=domain.split(".")[0].capitalize(),
                        domain=domain,
                        source=self.name,
                        source_url=url,
                        notes=[f"HN Algolia search match: '{title}'."],
                    )
                )
                if len(companies) >= icp.max_companies:
                    return companies

        return companies


_SKIP_DOMAINS = {
    # Code hosting / social
    "github.com", "gitlab.com", "bitbucket.org",
    "youtube.com", "medium.com", "twitter.com", "x.com",
    "reddit.com", "facebook.com", "fb.com", "instagram.com", "linkedin.com",
    "pinterest.com", "tiktok.com", "discord.com", "slack.com",
    "whatsapp.com", "telegram.org", "snapchat.com", "threads.net",
    # Reference / academic
    "wikipedia.org", "arxiv.org", "stackexchange.com", "stackoverflow.com",
    "usenix.org", "acm.org", "ieee.org", "researchgate.net",
    # Tech news & aggregators
    "news.ycombinator.com", "ycombinator.com",
    "techcrunch.com", "theverge.com", "arstechnica.com", "wired.com",
    "thenextweb.com", "venturebeat.com", "zdnet.com", "cnet.com",
    "engadget.com", "gizmodo.com", "mashable.com", "lifehacker.com",
    "theregister.co.uk", "infoworld.com", "phoronix.com",
    "thenewstack.io", "businesswire.com", "techrepublic.com",
    "softwareengineeringdaily.com", "thechangelog.com",
    "sdtimes.com", "infoq.com", "siliconangle.com",
    # General news / media
    "bbc.com", "bbc.co.uk", "nytimes.com", "washingtonpost.com",
    "theguardian.com", "bloomberg.com", "reuters.com", "cnn.com",
    "wsj.com", "ft.com", "economist.com", "forbes.com", "fortune.com",
    "businessinsider.com", "insider.com", "cnbc.com", "apnews.com",
    "npr.org", "vice.com", "vox.com", "theatlantic.com",
    "newyorker.com", "time.com", "usatoday.com", "latimes.com",
    "futurezone.at", "derstandard.at", "heise.de", "golem.de",
    "spiegel.de", "lemonde.fr", "elpais.com", "undark.org",
    # Google properties
    "google.com", "sre.google", "cloud.google.com", "research.google",
    "docs.google.com", "drive.google.com", "blog.google",
    # Big tech / mega-corps (too large to prospect)
    "apple.com", "microsoft.com", "amazon.com", "aws.amazon.com",
    "azure.microsoft.com", "netflix.com", "airbnb.com", "uber.com",
    "meta.com", "fb.com", "spotify.com", "salesforce.com",
    "oracle.com", "ibm.com", "intel.com", "cisco.com", "vmware.com",
    "adobe.com", "nvidia.com", "qualcomm.com", "samsung.com",
    "hpe.com", "dell.com", "hp.com", "lenovo.com",
    "twitter.com", "paypal.com", "stripe.com", "snap.com",
    "dropbox.com", "shopify.com", "square.com", "block.xyz",
    "heroku.com", "twitch.tv", "lyft.com", "doordash.com",
    # VC / investor firms (not prospects)
    "a16z.com", "ycombinator.com", "sequoiacap.com", "accel.com",
    "greylock.com", "benchmark.com", "kpcb.com", "indexventures.com",
    "lightspeedvp.com", "firstround.com", "foundersatwork.com",
    # Blogs / publishing platforms
    "substack.com", "wordpress.com", "blogspot.com", "tumblr.com",
    "ghost.org", "hashnode.dev", "dev.to", "towardsdatascience.com",
    # Personal blogs / individual sites (not companies)
    "danluu.com", "iximiuz.com", "chadxz.dev", "zwischenzugs.com",
    "kevinslin.com", "mikeperham.com", "willemterharmsel.nl",
    "cyber-economics.com", "remotehabits.com", "phabricator.org",
    "martinfowler.com", "joelonsoftware.com", "paulgraham.com",
    "jvns.ca", "rachelbythebay.com", "xeiaso.net", "fasterthanli.me",
    "matklad.github.io", "krebsonsecurity.com",
    # Mozilla / open-source foundations (not B2B prospects)
    "mozilla.org", "apache.org", "linuxfoundation.org", "fsf.org",
    "eclipse.org", "cncf.io", "openssl.org", "kernel.org",
    # Conferences / events
    "fosdem.org", "kubecon.io", "qconsf.com", "strangeloop.io",
    # Review / comparison / directory sites
    "getapp.com", "g2.com", "capterra.com", "trustradius.com",
    "producthunt.com", "alternativeto.net",
    # Dev-resource / tutorial sites
    "devops.com", "howtoforge.com", "digitalocean.com",
    "freecodecamp.org", "w3schools.com", "tutorialspoint.com",
    "geeksforgeeks.org", "baeldung.com", "realpython.com",
    # Generic hosting / platform domains (not real companies)
    "github.io", "githubusercontent.com", "herokuapp.com",
    "netlify.app", "vercel.app", "cloudflare.com",
    "readthedocs.io", "readthedocs.org", "gitbook.io",
    "pages.dev", "fly.dev", "railway.app", "render.com",
    # Paste / hosting / document sharing
    "pastebin.com", "imgur.com", "archive.org", "slideshare.net",
    "speakerdeck.com", "scribd.com", "notion.so", "figma.com",
}

# Two-part TLDs where the registrable domain is name.X.Y
_TWO_PART_TLDS = {
    "co.uk", "co.jp", "co.kr", "co.in", "co.za", "co.nz", "co.id",
    "com.au", "com.br", "com.cn", "com.mx", "com.sg", "com.tw",
    "com.hk", "com.ar", "org.uk", "org.au", "net.au", "ac.uk",
    "gov.uk", "edu.au",
}


def _extract_domain(url: str | None) -> str | None:
    """Extract the registrable (root) domain from a URL, stripping subdomains."""
    if not url:
        return None
    match = _DOMAIN_RE.search(url)
    if not match:
        return None
    host = match.group(1).lower().rstrip(".")

    # Remove port if present
    if ":" in host:
        host = host.split(":")[0]

    parts = host.split(".")
    if len(parts) < 2:
        return None

    # Check for two-part TLDs  (e.g.  example.co.uk → ["example", "co", "uk"])
    if len(parts) >= 3:
        candidate_tld = ".".join(parts[-2:])
        if candidate_tld in _TWO_PART_TLDS:
            # registrable domain is last 3 parts
            return ".".join(parts[-3:])

    # Default: registrable domain is last 2 parts  (e.g.  blog.monitis.com → monitis.com)
    return ".".join(parts[-2:])
