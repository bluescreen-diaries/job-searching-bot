from .greenhouse import GreenhouseScraper
from .lever import LeverScraper
from .workday import WorkdayScraper
from .generic import GenericScraper
from .playwright_scraper import PlaywrightScraper


def get_scraper(source: dict, preferences: dict):
    ats = (source.get("ats_type") or "").lower()
    scrapers = {
        "greenhouse": GreenhouseScraper,
        "lever": LeverScraper,
        "workday": WorkdayScraper,
        "browser": PlaywrightScraper,
    }
    cls = scrapers.get(ats, GenericScraper)
    return cls(source, preferences)
