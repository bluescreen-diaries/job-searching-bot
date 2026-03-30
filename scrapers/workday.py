import requests
from .base import BaseJobScraper


class WorkdayScraper(BaseJobScraper):
    """
    Workday ATS - uses the undocumented but consistent JSON API.
    URL format: https://{company}.wd5.myworkdayjobs.com/{path}
    """

    def fetch_jobs(self) -> list[dict]:
        url = self.source["url"]
        api_url = self._build_api_url(url)
        if not api_url:
            return []

        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

        jobs = []
        limit = 20
        offset = 0

        while True:
            payload = {
                "appliedFacets": {},
                "limit": limit,
                "offset": offset,
                "searchText": self._get_search_text(),
            }
            try:
                resp = requests.post(api_url, json=payload, headers=headers, timeout=15)
                resp.raise_for_status()
                data = resp.json()
            except Exception:
                break

            postings = data.get("jobPostings", [])
            for job in postings:
                job_id = job.get("externalPath", job.get("bulletFields", [""])[0])
                job_url = self._build_job_url(url, job.get("externalPath", ""))
                jobs.append({
                    "job_id": job_id,
                    "title": job.get("title", ""),
                    "company": self.source["name"],
                    "url": job_url,
                    "location": job.get("locationsText", ""),
                    "description": "",
                })

            if len(postings) < limit:
                break
            offset += limit

        return [j for j in jobs if self.matches_preferences(j)]

    def _build_api_url(self, url: str) -> str | None:
        # Convert career page URL to API endpoint
        # e.g. https://homedepot.wd5.myworkdayjobs.com/en-US/CareerDepot
        #   -> https://homedepot.wd5.myworkdayjobs.com/wday/cxs/homedepot/CareerDepot/jobs
        try:
            from urllib.parse import urlparse
            parsed = urlparse(url)
            host = parsed.hostname  # e.g. homedepot.wd5.myworkdayjobs.com
            subdomain = host.split(".")[0]  # e.g. homedepot
            path_parts = [p for p in parsed.path.split("/") if p]
            # Remove locale segment like "en-US" if present
            path_parts = [p for p in path_parts if not ("-" in p and len(p) == 5)]
            tenant_path = path_parts[-1] if path_parts else subdomain
            return f"https://{host}/wday/cxs/{subdomain}/{tenant_path}/jobs"
        except Exception:
            return None

    def _build_job_url(self, base_url: str, external_path: str) -> str:
        from urllib.parse import urlparse
        parsed = urlparse(base_url)
        base = f"{parsed.scheme}://{parsed.netloc}"
        return f"{base}{external_path}"

    def _get_search_text(self) -> str:
        keywords = self.preferences.get("keywords", "")
        keyword_list = [k.strip() for k in keywords.split(",") if k.strip()]
        return keyword_list[0] if keyword_list else ""
