"""
Daily job search runner. Called by the scheduler and also on-demand.
"""
import asyncio
from concurrent.futures import ThreadPoolExecutor
from database import get_all_preferences, list_sources, is_job_seen, mark_job_seen
from scrapers import get_scraper

_executor = ThreadPoolExecutor(max_workers=3)


def _scrape_source(source, preferences):
    scraper = get_scraper(source, preferences)
    return scraper.fetch_jobs()


async def run_job_search(send_message_callback):
    """
    Scrapes all active sources, finds new jobs matching preferences,
    and calls send_message_callback(text) for each new result.
    """
    preferences = get_all_preferences()
    sources = list_sources()

    if not sources:
        await send_message_callback("No sources configured yet. Use `/add <company>` to add one.")
        return

    if not preferences.get("keywords"):
        await send_message_callback("No job keywords set. Use `/setpref keywords data analyst, SQL` to set preferences.")
        return

    total_new = 0
    loop = asyncio.get_event_loop()

    for source in sources:
        try:
            jobs = await loop.run_in_executor(_executor, _scrape_source, source, preferences)
        except Exception as e:
            await send_message_callback(f"Error scraping **{source['name']}**: {e}")
            continue

        new_jobs = []
        for job in jobs:
            if not is_job_seen(source["id"], job["job_id"]):
                new_jobs.append(job)
                mark_job_seen(source["id"], job["job_id"], job["title"], job["company"], job["url"])

        for job in new_jobs:
            location = f" — {job['location']}" if job.get("location") else ""
            msg = f"**{job['title']}** at **{job['company']}**{location}\n{job['url']}"
            await send_message_callback(msg)
            total_new += 1

    if total_new == 0:
        await send_message_callback("Daily search complete — no new matching jobs found.")
    else:
        await send_message_callback(f"Daily search complete — found **{total_new}** new job(s).")
