import requests
from .base import BaseJobScraper


class GreenhouseScraper(BaseJobScraper):
    """
    Greenhouse ATS - uses their public JSON API.
    URL format: https://boards.greenhouse.io/{company_slug}
    API:        https://boards-api.greenhouse.io/v1/boards/{company_slug}/jobs
    """

    def fetch_jobs(self) -> list[dict]:
        url = self.source["url"]
        slug = self._extract_slug(url)
        if not slug:
            return []

        api_url = f"https://boards-api.greenhouse.io/v1/boards/{slug}/jobs?content=true"
        try:
            resp = requests.get(api_url, timeout=15)
            resp.raise_for_status()
            data = resp.json()
        except Exception:
            return []

        jobs = []
        for job in data.get("jobs", []):
            departments = job.get("departments", [])
            department = departments[0].get("name", "") if departments else ""
            jobs.append({
                "job_id": str(job["id"]),
                "title": job.get("title", ""),
                "company": self.source["name"],
                "url": job.get("absolute_url", ""),
                "location": job.get("location", {}).get("name", ""),
                "department": department,
                "description": "",
            })
        return [j for j in jobs if self.matches_preferences(j)]

    def _extract_slug(self, url: str) -> str | None:
        # e.g. https://boards.greenhouse.io/stripe -> "stripe"
        parts = url.rstrip("/").split("/")
        return parts[-1] if parts else None
