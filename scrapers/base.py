class BaseJobScraper:
    def __init__(self, source: dict, preferences: dict):
        self.source = source
        self.preferences = preferences

    def fetch_jobs(self) -> list[dict]:
        """
        Returns a list of job dicts:
        {
            "job_id": str,      # unique ID within this source
            "title": str,
            "company": str,
            "url": str,
            "location": str,
            "description": str  # optional short snippet
        }
        """
        raise NotImplementedError

    def matches_preferences(self, job: dict) -> bool:
        keywords = self.preferences.get("keywords", "")
        if not keywords:
            keyword_match = True
        else:
            keyword_list = [k.strip().lower() for k in keywords.split(",") if k.strip()]
            title = job.get("title", "").lower()
            description = job.get("description", "").lower()
            keyword_match = any(kw in title or kw in description for kw in keyword_list)

        category = self.source.get("category")
        if not category:
            category_match = True
        else:
            cat_list = [c.strip().lower() for c in category.split(",") if c.strip()]
            title = job.get("title", "").lower()
            department = job.get("department", "").lower()
            description = job.get("description", "").lower()
            category_match = any(cat in title or cat in department or cat in description for cat in cat_list)

        return keyword_match and category_match
