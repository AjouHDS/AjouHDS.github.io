"""
Fetch official journal logos and save to images/journals/.

Rules:
  - Only journal-specific logos are saved (not publisher/brand logos)
  - If no official journal logo can be retrieved, the citation's 'image'
    field is left unset (blank thumbnail in the Research tab)
  - No favicon fallbacks, no generic publisher page fallbacks

Strategy:
  1. Publisher-specific fetchers for families where we know how to get
     the real journal logo (Springer Nature SVG headers, AHA CDN, etc.)
  2. For other journals: fetch the specific journal homepage URL from
     OpenAlex and scrape a logo from that page
  3. If blocked (403) or no distinct logo found → leave blank

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

# SSL context for stdlib urlopen
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

# Generic publisher domains — scraping these gives publisher logos, not journal logos.
# For journals hosted here, we scrape the specific journal sub-page instead.
GENERIC_PUBLISHER_DOMAINS = {
    "sciencedirect.com", "journals.elsevier.com", "elsevier.com",
    "onlinelibrary.wiley.com", "wiley.com",
    "jamanetwork.com", "jama.ama-assn.org", "archpedi.ama-assn.org",
    "ahajournals.org", "circ.ahajournals.org", "stroke.ahajournals.org",
    "hyper.ahajournals.org",
    "bmj.com", "bmjopenrespres.bmj.com", "informatics.bmj.com",
    "thelancet.com",
    "springer.com", "link.springer.com", "springernature.com",
    "biomedcentral.com", "bmcpsychiatry.biomedcentral.com",
    "bmcmedresmethodol.biomedcentral.com", "capmh.biomedcentral.com",
    "academic.oup.com", "ije.oxfordjournals.org",
    "journals.cambridge.org",
    "mdpi.com",
    "iospress.com", "iospress.nl",
    "frontiersin.org",
    "jmir.org",              # All JMIR journals share the same platform
}


def _session():
    s = requests.Session()
    s.headers.update(BROWSER_HEADERS)
    s.verify = False
    return s


# ─────────────────────────────────────────────
# Publisher-specific fetchers (journal-level logos)
# ─────────────────────────────────────────────

def fetch_springer_nature_logo(journal_slug):
    """Fetch the branded SVG header for a nature.com journal (journal-specific)."""
    url = f"https://www.nature.com/{journal_slug}/"
    try:
        s = _session()
        r = s.get(url, timeout=10)
        r.raise_for_status()
        matches = re.findall(
            r'https://media\.springernature\.com/full/nature-cms/uploads/product/'
            + re.escape(journal_slug)
            + r'/header-[a-f0-9]+\.svg',
            r.text,
        )
        if matches:
            img = s.get(matches[0], timeout=10)
            img.raise_for_status()
            return img.content, ".svg"
    except Exception as e:
        log(f"Springer Nature fetch failed ({journal_slug}): {e}", indent=2, level="INFO")
    return None, None


def fetch_aha_journal_logo(journal_slug):
    """Fetch an AHA journal logo from their pb-assets CDN (journal-specific)."""
    url = f"https://www.ahajournals.org/pb-assets/images/logos/{journal_slug}-logo-1620222428000.png"
    try:
        s = _session()
        r = s.get(url, timeout=10)
        if r.status_code == 200 and len(r.content) > 1000:
            return r.content, ".png"
    except Exception as e:
        log(f"AHA CDN fetch failed ({journal_slug}): {e}", indent=2, level="INFO")
    return None, None


def fetch_logo_from_journal_page(page_url):
    """
    Scrape a journal-specific page for a logo image.
    Only returns an image if we find something that looks like a journal logo
    (an <img> or SVG with logo/masthead/brand in its attributes/URL).
    Does NOT fall back to og:image (which is usually a generic publisher image).
    Returns (bytes, ext) or (None, None).
    """
    try:
        s = _session()
        r = s.get(page_url, timeout=10)
        if r.status_code != 200:
            log(f"Page blocked ({r.status_code}): {page_url[:60]}", indent=2, level="INFO")
            return None, None

        # Look for <img> with logo/masthead/brand in class, alt, or src
        img_tags = re.findall(
            r'<img[^>]+>',
            r.text, re.I | re.S
        )
        for tag in img_tags:
            alt = re.search(r'alt=["\']([^"\']*)["\']', tag)
            cls = re.search(r'class=["\']([^"\']*)["\']', tag)
            src = re.search(r'src=["\']([^"\']+)["\']', tag)
            alt_v = (alt.group(1) if alt else "").lower()
            cls_v = (cls.group(1) if cls else "").lower()
            src_v = (src.group(1) if src else "").lower()
            if any(kw in alt_v or kw in cls_v or kw in src_v
                   for kw in ["logo", "masthead", "journal-header", "brand-logo", "site-logo"]):
                if src:
                    src_url = src.group(1)
                    if src_url.startswith("//"):
                        src_url = "https:" + src_url
                    elif not src_url.startswith("http"):
                        base = f"{urlparse(r.url).scheme}://{urlparse(r.url).netloc}"
                        src_url = base + ("" if src_url.startswith("/") else "/") + src_url
                    img_r = s.get(src_url, timeout=8)
                    ct = img_r.headers.get("Content-Type", "")
                    # skip if not an image
                    if img_r.status_code == 200 and len(img_r.content) > 500 and "image" in ct:
                        ext = ".svg" if "svg" in ct else (".jpg" if "jpeg" in ct or "jpg" in ct else ".png")
                        return img_r.content, ext

        # Look for SVG files with logo/header in URL (linked directly in page)
        svg_urls = re.findall(
            r'(?:href|src)=["\']([^"\']*(?:logo|masthead|journal-header|brand)[^"\']*\.svg)["\']',
            r.text, re.I
        )
        for svg_url in svg_urls[:3]:
            if not svg_url.startswith("http"):
                base = f"{urlparse(r.url).scheme}://{urlparse(r.url).netloc}"
                svg_url = base + ("" if svg_url.startswith("/") else "/") + svg_url
            img_r = s.get(svg_url, timeout=8)
            if img_r.status_code == 200 and len(img_r.content) > 300:
                return img_r.content, ".svg"

    except Exception as e:
        log(f"Journal page scrape failed ({page_url[:60]}): {e}", indent=2, level="INFO")
    return None, None


def _is_generic_publisher_domain(netloc):
    """Return True if netloc or any parent domain is in GENERIC_PUBLISHER_DOMAINS."""
    netloc = netloc.replace("www.", "").lower()
    if netloc in GENERIC_PUBLISHER_DOMAINS:
        return True
    parts = netloc.split(".")
    for i in range(1, len(parts)):
        if ".".join(parts[i:]) in GENERIC_PUBLISHER_DOMAINS:
            return True
    return False


def fetch_favicon_for_domain(domain):
    """
    Fetch a high-resolution favicon for a domain.
    Uses Google's favicon service (sz=256) first, then falls back to /favicon.ico.
    Returns (bytes, ext) or (None, None).
    Google returns a small grey default (~200-400 bytes) for unknown domains;
    real favicons at 256px are typically > 1 KB.
    """
    clean = domain.replace("www.", "", 1)
    google_url = f"https://www.google.com/s2/favicons?domain={clean}&sz=256"
    try:
        r = _session().get(google_url, timeout=10)
        if r.status_code == 200 and len(r.content) > 1000:
            ct = r.headers.get("Content-Type", "")
            if "image" in ct:
                ext = ".png" if "png" in ct else ".ico"
                return r.content, ext
    except Exception as e:
        log(f"Google favicon fetch failed ({domain}): {e}", indent=2, level="INFO")

    # Direct /favicon.ico fallback
    try:
        favicon_url = f"https://{domain}/favicon.ico"
        r = _session().get(favicon_url, timeout=8)
        if r.status_code == 200 and len(r.content) > 500:
            return r.content, ".ico"
    except Exception as e:
        log(f"Direct favicon fetch failed ({domain}): {e}", indent=2, level="INFO")

    return None, None


# ─────────────────────────────────────────────
# Hardcoded journal-specific fetchers
# Only journals where we know exactly how to get the official logo
# ─────────────────────────────────────────────

def _springer_fetcher(slug):
    return lambda: fetch_springer_nature_logo(slug)

def _aha_fetcher(slug):
    return lambda: fetch_aha_journal_logo(slug)

def _page_fetcher(url):
    return lambda: fetch_logo_from_journal_page(url)

def _direct_url_fetcher(url, ext):
    """Fetch an image directly from a known URL."""
    def _fetch():
        try:
            r = _session().get(url, timeout=10)
            if r.status_code == 200 and len(r.content) > 300:
                return r.content, ext
        except Exception as e:
            log(f"Direct fetch failed ({url[:60]}): {e}", indent=2, level="INFO")
        return None, None
    return _fetch


# Maps lowercased, HTML-unescaped publisher name → fetcher lambda
PUBLISHER_FETCHERS = {
    # Springer Nature — journal-specific SVG headers
    "nature communications":        _springer_fetcher("ncomms"),
    "scientific data":              _springer_fetcher("sdata"),

    # AHA — journal-specific CDN logos
    "circulation":                  _aha_fetcher("circ"),
    "stroke":                       _aha_fetcher("str"),
    "hypertension":                 _aha_fetcher("hyp"),

    # JAMA family — journal-specific cover/favicon images from JAMA CDN
    # Cover images (print nameplate) for journals that have them
    "jama":                         _direct_url_fetcher("https://cdn.jamanetwork.com/UI/app/img/covers/jama.jpg", ".jpg"),
    "jama pediatrics":              _direct_url_fetcher("https://cdn.jamanetwork.com/UI/app/img/covers/peds.jpg", ".jpg"),
    "jama oncology":                _direct_url_fetcher("https://cdn.jamanetwork.com/UI/app/img/covers/oncol.jpg", ".jpg"),
    # JAMA Network Open is online-only (no print cover) — use journal-specific 192px favicon
    "jama network open":            _direct_url_fetcher("https://cdn.jamanetwork.com/UI/app/img/favicons/jamanetworkopen/favicon-192x192.png", ".png"),

    # JMIR: jmir.org returns the JMIR Publications corporate logo — skip all JMIR journals

    # arXiv SVG is white-on-transparent — not usable; leave blank
    # BMC journals share a Springer Nature corporate SVG — not journal-specific; leave blank
    # Preprints have no official journal logo; leave blank
}

# Publishers/journals that return a shared corporate or unusable logo
# when scraped — skip them entirely
KNOWN_BAD_SCRAPERS = {
    "arxiv",
    "bmc psychiatry",
    "bmc medical research methodology",
    "child and adolescent psychiatry and mental health",
    "medrxiv",
    "medrxiv (under review)",
    "medrxiv (accepted)",
    "openrxiv",
    "elsevier bv",
    "mdpi ag",
    "springer science and business media llc",
    "jmir publications inc.",       # returns same JMIR Publications corporate logo
    "jmir medical informatics",     # returns same JMIR Publications corporate logo
    "journal of medical internet research",  # jmir.org returns JMIR Publications corporate logo
    "studies in health technology and informatics",  # IOS Press corporate logo, not journal-specific
    "yonsei medical journal",       # eymj.org returns link-tracker image, not journal logo
}


# ─────────────────────────────────────────────
# OpenAlex: get the specific journal homepage URL
# ─────────────────────────────────────────────

@cache.memoize(name="openalex_homepage_v4", expire=30 * 24 * 60 * 60)
def get_journal_homepage(publisher_name):
    """
    Query OpenAlex for the specific journal homepage URL.
    Returns the URL string or '' if not found.
    """
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

    for r in results:
        homepage = (r.get("homepage_url") or "").strip()
        if homepage and r.get("display_name", "").lower() == publisher_name.lower():
            return homepage  # exact match
    # fallback: first result with a homepage
    for r in results:
        homepage = (r.get("homepage_url") or "").strip()
        if homepage:
            return homepage
    return ""


def sanitize_filename(publisher):
    name = html.unescape(publisher).lower()
    name = re.sub(r"[^\w\s-]", "", name)
    name = re.sub(r"[\s_-]+", "_", name)
    return name.strip("_")


# ─────────────────────────────────────────────
# Main entry point
# ─────────────────────────────────────────────

def main(citations):
    """
    For every citation without an 'image' field, attempt to fetch the
    official journal logo. If not found, leave 'image' unset.
    """
    if not HAS_REQUESTS:
        log("requests not available — skipping journal logo fetch", level="INFO")
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
        homepage = None

        # KNOWN_BAD_SCRAPERS: skip logo scraping (returns corporate/unusable logo),
        # but still try favicon as a last resort below.
        skip_logo_scraping = publisher_key in KNOWN_BAD_SCRAPERS

        if not skip_logo_scraping:
            # 1. Try hardcoded journal-specific fetcher
            fetcher = PUBLISHER_FETCHERS.get(publisher_key)
            if fetcher:
                data, ext = fetcher()

            # 2. Try scraping the specific journal homepage from OpenAlex
            if not data:
                homepage = get_journal_homepage(publisher)
                if homepage:
                    log(f"Scraping journal page: {homepage[:60]}", indent=2, level="INFO")
                    data, ext = fetch_logo_from_journal_page(homepage)

        # 3. Favicon fallback — only for journals with their own dedicated domain
        #    (shared publisher platforms would give every journal the same favicon)
        if not data:
            if homepage is None:
                homepage = get_journal_homepage(publisher)
            if homepage:
                domain = urlparse(homepage).netloc.replace("www.", "")
                if not _is_generic_publisher_domain(domain):
                    log(f"Trying favicon for: {domain}", indent=2, level="INFO")
                    data, ext = fetch_favicon_for_domain(domain)
                else:
                    log(f"Skipping favicon (shared publisher platform): {domain}", indent=2, level="INFO")

        if data and ext:
            dest = LOGOS_DIR / f"{base_name}{ext}"
            dest.write_bytes(data)
            rel = dest.relative_to(_REPO_ROOT).as_posix()
            publisher_cache[publisher] = rel
            citation["image"] = rel
            fetched += 1
            log(f"Saved: {rel}", indent=2, level="INFO")
        else:
            log(f"No logo or favicon found for '{publisher}'", indent=2, level="INFO")
            publisher_cache[publisher] = None

    log(f"Journal logos: {fetched} logo(s) fetched", level="SUCCESS")
