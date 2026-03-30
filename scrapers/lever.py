import requests
from .base import BaseJobScraper


class LeverScraper(BaseJobScraper):
    """
    Lever ATS - uses their public JSON API.
    URL format: https://jobs.lever.co/{company_slug}
    API:        https://api.lever.co/v0/postings/{company_slug}
    """

    def fetch_jobs(self) -> list[dict]:
        url = self.source["url"]
        slug = self._extract_slug(url)
        if not slug:
            return []

        api_url = f"https://api.lever.co/v0/postings/{slug}?mode=json"
        try:
            resp = requests.get(api_url, timeout=15)
            resp.raise_for_status()
            data = resp.json()
        except Exception:
            return []

        jobs = []
        for job in data:
            jobs.append({
                "job_id": job.get("id", ""),
                "title": job.get("text", ""),
                "company": self.source["name"],
                "url": job.get("hostedUrl", ""),
                "location": job.get("categories", {}).get("location", ""),
                "description": job.get("descriptionPlain", "")[:300],
            })
        return [j for j in jobs if self.matches_preferences(j)]

    def _extract_slug(self, url: str) -> str | None:
        parts = url.rstrip("/").split("/")
        return parts[-1] if parts else None
