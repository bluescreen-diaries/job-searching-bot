import requests
from bs4 import BeautifulSoup
from .base import BaseJobScraper
import hashlib


class GenericScraper(BaseJobScraper):
    """
    Fallback scraper for unknown/custom career pages.
    Looks for links that look like job postings based on keywords.
    """

    JOB_KEYWORDS = ["engineer", "analyst", "manager", "developer", "designer",
                    "specialist", "coordinator", "director", "associate", "lead",
                    "scientist", "consultant", "architect", "administrator"]

    NEXT_PAGE_PATTERNS = ["next", "next page", "›", "»", ">"]

    def fetch_jobs(self) -> list[dict]:
        start_url = self.source["url"]
        jobs = []
        seen_urls = set()
        visited_pages = set()
        current_url = start_url

        while current_url and current_url not in visited_pages:
            visited_pages.add(current_url)
            try:
                resp = requests.get(current_url, timeout=15, headers={"User-Agent": "Mozilla/5.0"})
                resp.raise_for_status()
            except Exception:
                break

            soup = BeautifulSoup(resp.text, "html.parser")

            for a in soup.find_all("a", href=True):
                text = a.get_text(strip=True)
                href = a["href"]
                if not text or len(text) < 5 or len(text) > 150:
                    continue
                if not any(kw in text.lower() for kw in self.JOB_KEYWORDS):
                    continue

                full_url = self._resolve_url(start_url, href)
                if full_url in seen_urls:
                    continue
                seen_urls.add(full_url)

                job_id = hashlib.md5(full_url.encode()).hexdigest()[:12]
                jobs.append({
                    "job_id": job_id,
                    "title": text,
                    "company": self.source["name"],
                    "url": full_url,
                    "location": "",
                    "description": "",
                })

            current_url = self._find_next_page(soup, current_url, start_url)

        return [j for j in jobs if self.matches_preferences(j)]

    def _find_next_page(self, soup, current_url: str, base_url: str):
        for a in soup.find_all("a", href=True):
            text = a.get_text(strip=True).lower()
            if text in self.NEXT_PAGE_PATTERNS:
                return self._resolve_url(base_url, a["href"])
        return None

    def _resolve_url(self, base: str, href: str) -> str:
        from urllib.parse import urljoin
        return urljoin(base, href)
