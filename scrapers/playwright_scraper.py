import hashlib
from .base import BaseJobScraper

SEARCH_INPUT_SELECTORS = [
    'input[type="search"]',
    'input[placeholder*="search" i]',
    'input[placeholder*="job" i]',
    'input[placeholder*="title" i]',
    'input[aria-label*="search" i]',
    'input[name*="search" i]',
    'input[name*="keyword" i]',
    'input[id*="search" i]',
]

JOB_KEYWORDS = [
    "engineer", "analyst", "manager", "developer", "designer",
    "specialist", "coordinator", "director", "associate", "lead",
    "scientist", "consultant", "architect", "administrator", "support",
    "technician", "representative", "agent"
]


class PlaywrightScraper(BaseJobScraper):
    """
    Browser-based scraper using Playwright.
    Handles JS-rendered pages and sites with search forms.
    """

    def fetch_jobs(self) -> list[dict]:
        try:
            from playwright.sync_api import sync_playwright
        except ImportError:
            return []

        url = self.source["url"]
        keywords = self.preferences.get("keywords", "")
        keyword_list = [k.strip() for k in keywords.split(",") if k.strip()] if keywords else []

        jobs = []
        seen_urls = set()

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)

            try:
                # Search once with no keyword if no keywords set, otherwise once per keyword
                search_terms = keyword_list if keyword_list else [""]

                for keyword in search_terms:
                    page = browser.new_page()
                    page.set_extra_http_headers({"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"})

                    try:
                        page.goto(url, timeout=20000, wait_until="domcontentloaded")
                        page.wait_for_timeout(2000)

                        # Try to fill a search field if one exists
                        if keyword:
                            for selector in SEARCH_INPUT_SELECTORS:
                                try:
                                    input_el = page.query_selector(selector)
                                    if input_el and input_el.is_visible():
                                        input_el.fill(keyword)
                                        input_el.press("Enter")
                                        page.wait_for_timeout(2000)
                                        break
                                except Exception:
                                    continue

                        # Extract job links from the rendered page
                        anchors = page.query_selector_all("a")
                        for a in anchors:
                            try:
                                text = a.inner_text().strip()
                                href = a.get_attribute("href") or ""
                            except Exception:
                                continue

                            if not text or len(text) < 5 or len(text) > 150:
                                continue
                            if not any(kw in text.lower() for kw in JOB_KEYWORDS):
                                continue

                            if href and not href.startswith("http"):
                                from urllib.parse import urljoin
                                href = urljoin(url, href)

                            if not href or href in seen_urls:
                                continue
                            seen_urls.add(href)

                            job_id = hashlib.md5(href.encode()).hexdigest()[:12]
                            jobs.append({
                                "job_id": job_id,
                                "title": text,
                                "company": self.source["name"],
                                "url": href,
                                "location": "",
                                "description": "",
                            })

                    except Exception:
                        pass
                    finally:
                        page.close()

            finally:
                browser.close()

        return [j for j in jobs if self.matches_preferences(j)]
