from .greenhouse import GreenhouseScraper
from .lever import LeverScraper
from .workday import WorkdayScraper
from .generic import GenericScraper


def get_scraper(source: dict, preferences: dict):
    ats = (source.get("ats_type") or "").lower()
    scrapers = {
        "greenhouse": GreenhouseScraper,
        "lever": LeverScraper,
        "workday": WorkdayScraper,
    }
    cls = scrapers.get(ats, GenericScraper)
    return cls(source, preferences)
