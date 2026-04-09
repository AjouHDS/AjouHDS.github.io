"""
Fetch proper journal logos and save to images/journals/.

Strategy per publisher family:
  - Springer Nature journals: scrape SVG header from nature.com/{slug}/
  - AHA journals (Circulation, Stroke, Hypertension): pb-assets CDN
  - Frontiers / JMIR / accessible sites: scrape og:image or logo img
  - Others: OpenAlex homepage → scrape logo → fall back to Google favicon

Sets the 'image' field on citations that don't already have one.
Called automatically from cite.py before saving citations.yaml.
"""

import re
import json
import html
import ssl
import warnings
import urllib.parse
from urllib.request import Request, urlopen
from urllib.parse import urlparse
from pathlib import Path

warnings.filterwarnings("ignore")

try:
    import requests
    from requests.packages.urllib3.exceptions import InsecureRequestWarning
    requests.packages.urllib3.disable_warnings(InsecureRequestWarning)
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False

from util import log, cache


# Repo root (parent of _cite/)
_REPO_ROOT = Path(__file__).parent.parent
LOGOS_DIR = _REPO_ROOT / "images" / "journals"

# SSL context for stdlib urlopen fallback
SSL_CTX = ssl.create_default_context()
SSL_CTX.check_hostname = False
SSL_CTX.verify_mode = ssl.CERT_NONE

BROWSER_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
}

# ─────────────────────────────────────────────
# Publisher-specific logo fetchers
# ─────────────────────────────────────────────

def _session():
    """Requests session with browser-like headers and SSL skipped."""
    s = requests.Session()
    s.headers.update(BROWSER_HEADERS)
    s.verify = False
    return s


def fetch_springer_nature_logo(journal_slug):
    """
    Scrape the SVG header logo for a nature.com journal.
    journal_slug examples: 'ncomms', 'sdata'
    Returns image bytes (SVG) or None.
    """
    url = f"https://www.nature.com/{journal_slug}/"
    try:
        s = _session()
        r = s.get(url, timeout=10)
        r.raise_for_status()
        # The full-size branded SVG header is at a predictable CDN path
        matches = re.findall(
            r'https://media\.springernature\.com/full/nature-cms/uploads/product/'
            + journal_slug
            + r'/header-[a-f0-9]+\.svg',
            r.text,
        )
        if matches:
            img = s.get(matches[0], timeout=10)
            img.raise_for_status()
            return img.content, ".svg"
    except Exception as e:
        log(f"Springer Nature logo failed for {journal_slug}: {e}", indent=2, level="INFO")
    return None, None


def fetch_aha_logo(journal_slug):
    """
    Download AHA journal logo from their pb-assets CDN.
    journal_slug: 'circ', 'jaha', etc.
    """
    url = f"https://www.ahajournals.org/pb-assets/images/logos/{journal_slug}-logo-1620222428000.png"
    try:
        s = _session()
        r = s.get(url, timeout=10)
        if r.status_code == 200 and len(r.content) > 500:
            return r.content, ".png"
    except Exception as e:
        log(f"AHA logo failed for {journal_slug}: {e}", indent=2, level="INFO")
    return None, None


def fetch_logo_from_page(page_url, timeout=10):
    """
    Scrape a journal homepage for the best available logo image.
    Priority: branded SVG logo img → og:image → None
    Returns (bytes, ext) or (None, None).
    """
    try:
        s = _session()
        r = s.get(page_url, timeout=timeout)
        if r.status_code != 200:
            return None, None

        # 1. Look for SVG/PNG logo in <img> tags with logo-like attributes
        img_tags = re.findall(
            r'<img[^>]+(?:class|alt|src)=["\'][^"\']*(?:logo|brand|masthead|header-logo)[^"\']*["\'][^>]*>',
            r.text, re.I
        )
        for tag in img_tags:
            src = re.search(r'src=["\']([^"\']+)["\']', tag)
            if src:
                src_url = src.group(1)
                if not src_url.startswith("http"):
                    base = f"{urlparse(r.url).scheme}://{urlparse(r.url).netloc}"
                    src_url = base + ("" if src_url.startswith("/") else "/") + src_url
                img_r = s.get(src_url, timeout=8)
                if img_r.status_code == 200 and len(img_r.content) > 500:
                    ext = ".svg" if "svg" in img_r.headers.get("Content-Type", "") else ".png"
                    return img_r.content, ext

        # 2. Look for SVG files referenced in the page with 'logo'/'header' in URL
        svg_urls = re.findall(r'https?://[^\s"\'<>]+(?:logo|header|brand)[^\s"\'<>]*\.svg', r.text, re.I)
        for url in svg_urls[:3]:
            img_r = s.get(url, timeout=8)
            if img_r.status_code == 200 and len(img_r.content) > 300:
                return img_r.content, ".svg"

        # 3. Fallback: og:image (often a branded banner/cover)
        og = re.search(r'<meta[^>]+property=["\']og:image["\'][^>]+content=["\']([^"\']+)["\']', r.text)
        if not og:
            og = re.search(r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+property=["\']og:image["\']', r.text)
        if og:
            img_url = og.group(1)
            if img_url.startswith("//"):
                img_url = "https:" + img_url
            img_r = s.get(img_url, timeout=8)
            if img_r.status_code == 200 and len(img_r.content) > 1000:
                ct = img_r.headers.get("Content-Type", "")
                ext = ".svg" if "svg" in ct else (".jpg" if "jpeg" in ct or "jpg" in ct else ".png")
                return img_r.content, ext

    except Exception as e:
        log(f"Page logo scrape failed ({page_url[:60]}): {e}", indent=2, level="INFO")
    return None, None


def fetch_favicon_fallback(domain):
    """Google's favicon service — last resort (gives brand icon, not a full logo)."""
    url = f"https://www.google.com/s2/favicons?domain={domain}&sz=128"
    try:
        s = _session()
        r = s.get(url, timeout=10)
        if r.status_code == 200 and len(r.content) > 200:
            return r.content, ".png"
    except Exception:
        pass
    return None, None


# ─────────────────────────────────────────────
# Publisher-specific routing table
# Each entry: publisher_key (lowercased, html-unescaped) → fetcher lambda
# ─────────────────────────────────────────────

def _springer_fetcher(slug):
    return lambda: fetch_springer_nature_logo(slug)

def _aha_fetcher(slug):
    return lambda: fetch_aha_logo(slug)

def _page_fetcher(url):
    return lambda: fetch_logo_from_page(url)

def _favicon_fetcher(domain):
    return lambda: fetch_favicon_fallback(domain)


PUBLISHER_FETCHERS = {
    # Springer Nature journals — scrape SVG from nature.com
    "nature communications":        _springer_fetcher("ncomms"),
    "scientific data":              _springer_fetcher("sdata"),

    # AHA journals — CDN logo
    "circulation":                  _aha_fetcher("circ"),

    # JMIR — accessible homepage
    "journal of medical internet research": _page_fetcher("https://www.jmir.org"),
    "jmir medical informatics":     _page_fetcher("https://medinform.jmir.org"),
    "jmir publications inc.":       _page_fetcher("https://www.jmir.org"),

    # Frontiers — accessible homepage
    "frontiers in psychiatry":      _page_fetcher("https://www.frontiersin.org/journals/psychiatry"),

    # Elsevier corporate logo (accessible)
    "elsevier bv":                  _page_fetcher("https://www.elsevier.com"),

    # MDPI — accessible
    "mdpi ag":                      _page_fetcher("https://www.mdpi.com"),
    "pharmaceuticals":              _page_fetcher("https://www.mdpi.com/journal/pharmaceuticals"),
    "journal of clinical medicine": _page_fetcher("https://www.mdpi.com/journal/jcm"),

    # Springer (non-Nature)
    "springer science and business media llc": _page_fetcher("https://www.springernature.com"),
    "bmc psychiatry":               _page_fetcher("https://bmcpsychiatry.biomedcentral.com"),
    "bmc medical research methodology": _page_fetcher("https://bmcmedresmethodol.biomedcentral.com"),

    # Frontiers
    "child and adolescent psychiatry and mental health": _page_fetcher("https://capmh.biomedcentral.com"),

    # Cambridge
    "psychological medicine":       _page_fetcher("https://www.cambridge.org/core/journals/psychological-medicine"),

    # IOS Press
    "studies in health technology and informatics": _page_fetcher("https://www.iospress.com"),

    # Preprints — favicon is fine (no official journal logo)
    "medrxiv":                      _favicon_fetcher("medrxiv.org"),
    "medrxiv (under review)":       _favicon_fetcher("medrxiv.org"),
    "medrxiv (accepted)":           _favicon_fetcher("medrxiv.org"),
    "openrxiv":                     _favicon_fetcher("medrxiv.org"),
    "arxiv":                        _favicon_fetcher("arxiv.org"),
}


# ─────────────────────────────────────────────
# OpenAlex homepage lookup (for fallback)
# ─────────────────────────────────────────────

HOST_ORG_DOMAINS = {
    "elsevier bv": "sciencedirect.com",
    "elsevier": "sciencedirect.com",
    "springer science and business media llc": "springer.com",
    "wiley": "onlinelibrary.wiley.com",
    "oxford university press": "academic.oup.com",
    "american medical association": "jamanetwork.com",
    "american heart association": "ahajournals.org",
    "bmj": "bmj.com",
    "the lancet": "thelancet.com",
    "mdpi": "mdpi.com",
}

KNOWN_DOMAINS = {
    "openrxiv": "medrxiv.org",
    "medrxiv": "medrxiv.org",
    "medrxiv (under review)": "medrxiv.org",
    "medrxiv (accepted)": "medrxiv.org",
    "arxiv": "arxiv.org",
    "elsevier bv": "elsevier.com",
    "mdpi ag": "mdpi.com",
    "springer science and business media llc": "springernature.com",
    "jmir publications inc.": "jmir.org",
    "jacc: advances": "jacc.org",
    "annals of allergy, asthma & immunology": "journals.elsevier.com",
    "the american journal of geriatric psychiatry": "journals.elsevier.com",
    "clinical & experimental allergy": "onlinelibrary.wiley.com",
    "bmj health & care informatics": "informatics.bmj.com",
}


def sanitize_filename(publisher):
    name = html.unescape(publisher).lower()
    name = re.sub(r"[^\w\s-]", "", name)
    name = re.sub(r"[\s_-]+", "_", name)
    return name.strip("_")


@cache.memoize(name="openalex_homepage_v3", expire=30 * 24 * 60 * 60)
def get_journal_domain(publisher_name):
    clean = html.unescape(publisher_name)
    clean = re.sub(r"[:\(\)\[\],]", " ", clean)
    clean = re.sub(r"\s+", " ", clean).strip()
    encoded = urllib.parse.quote(clean)
    url = (
        f"https://api.openalex.org/sources"
        f"?filter=display_name.search:{encoded}"
        f"&per_page=5&mailto=ajou-hds@ajou.ac.kr"
    )
    try:
        req = Request(url=url, headers={"User-Agent": "AjouHDS/1.0"})
        data = json.loads(urlopen(req, timeout=12, context=SSL_CTX).read())
        results = data.get("results", [])
    except Exception:
        return ""

    fallback = ""
    for r in results:
        homepage = (r.get("homepage_url") or "").strip()
        host_org = (r.get("host_organization_name") or "").strip().lower()
        if homepage:
            domain = urlparse(homepage).netloc.replace("www.", "")
            if r.get("display_name", "").lower() == publisher_name.lower():
                return domain
            fallback = fallback or domain
        elif host_org and not fallback:
            for key, dom in HOST_ORG_DOMAINS.items():
                if key in host_org:
                    fallback = dom
                    break
    return fallback


# ─────────────────────────────────────────────
# Main entry point
# ─────────────────────────────────────────────

def main(citations):
    """
    For every citation without an 'image' field, fetch the journal logo
    and set citation['image'] to the local path.
    """
    if not HAS_REQUESTS:
        log("requests library not available — skipping journal logo fetch", level="INFO")
        return

    log("Fetching journal logos")
    LOGOS_DIR.mkdir(parents=True, exist_ok=True)

    publisher_cache = {}
    fetched = 0

    for citation in citations:
        if citation.get("image"):
            continue

        publisher = (citation.get("publisher") or "").strip()
        if not publisher:
            continue

        if publisher in publisher_cache:
            if publisher_cache[publisher]:
                citation["image"] = publisher_cache[publisher]
            continue

        base_name = sanitize_filename(publisher)

        # Check disk cache
        existing = list(LOGOS_DIR.glob(f"{base_name}.*"))
        if existing:
            rel = existing[0].relative_to(_REPO_ROOT).as_posix()
            log(f"Cached: '{publisher}'", indent=1, level="INFO")
            publisher_cache[publisher] = rel
            citation["image"] = rel
            continue

        log(f"Fetching logo: {publisher}", indent=1)

        publisher_key = html.unescape(publisher).lower().strip()
        data, ext = None, None

        # 1. Try publisher-specific fetcher
        fetcher = PUBLISHER_FETCHERS.get(publisher_key)
        if fetcher:
            data, ext = fetcher()

        # 2. Try scraping the journal homepage
        if not data:
            domain = KNOWN_DOMAINS.get(publisher_key) or get_journal_domain(publisher)
            if domain:
                page_url = f"https://{domain}"
                log(f"Scraping: {page_url}", indent=2, level="INFO")
                data, ext = fetch_logo_from_page(page_url)

                # 3. Favicon fallback
                if not data:
                    log(f"Falling back to favicon: {domain}", indent=2, level="INFO")
                    data, ext = fetch_favicon_fallback(domain)

        if data and ext:
            dest = LOGOS_DIR / f"{base_name}{ext}"
            dest.write_bytes(data)
            rel = dest.relative_to(_REPO_ROOT).as_posix()
            publisher_cache[publisher] = rel
            citation["image"] = rel
            fetched += 1
            log(f"Saved: {rel}", indent=2, level="INFO")
        else:
            log(f"No logo found for '{publisher}'", indent=2, level="INFO")
            publisher_cache[publisher] = None

    log(f"Journal logos: {fetched} new logo(s) fetched", level="SUCCESS")
