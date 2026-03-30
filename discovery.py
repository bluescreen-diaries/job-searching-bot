"""
Auto-discover career page URL and ATS type from a company name.
Uses Claude to interpret the command and web search to find the URL.
"""
import re
import requests
from anthropic import Anthropic

client = Anthropic()

ATS_FINGERPRINTS = {
    "greenhouse": ["boards.greenhouse.io", "greenhouse.io"],
    "lever": ["jobs.lever.co", "lever.co"],
    "workday": ["myworkdayjobs.com", "wd1.myworkdayjobs", "wd5.myworkdayjobs"],
    "icims": ["icims.com"],
    "taleo": ["taleo.net"],
}


def detect_ats(url: str) -> str | None:
    for ats, patterns in ATS_FINGERPRINTS.items():
        if any(p in url for p in patterns):
            return ats
    return None


def search_career_page(company_name: str) -> str | None:
    """Search DuckDuckGo for the company's career page URL."""
    query = f"{company_name} official careers jobs"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    try:
        resp = requests.get(
            "https://html.duckduckgo.com/html/",
            params={"q": query},
            headers=headers,
            timeout=10
        )
        from bs4 import BeautifulSoup
        from urllib.parse import unquote, parse_qs, urlparse
        soup = BeautifulSoup(resp.text, "html.parser")

        # Try result__a links (DuckDuckGo main result links)
        for a in soup.find_all("a", class_="result__a"):
            href = a.get("href", "")
            text = a.get_text(strip=True).lower()
            if "uddg=" in href:
                parsed = urlparse(href)
                params = parse_qs(parsed.query)
                if "uddg" in params:
                    href = unquote(params["uddg"][0])
            if any(word in text or word in href.lower() for word in ["career", "job", "work"]):
                return href

        # Fallback: try result__url links
        for a in soup.find_all("a", class_="result__url"):
            href = a.get("href", "")
            text = a.get_text(strip=True).lower()
            if any(word in text or word in href.lower() for word in ["career", "job", "work"]):
                if "uddg=" in href:
                    parsed = urlparse(href)
                    params = parse_qs(parsed.query)
                    if "uddg" in params:
                        return unquote(params["uddg"][0])
                return href
    except Exception:
        pass

    # Last resort: try common career URL patterns
    slug = company_name.lower().replace(" ", "").replace(".", "")
    candidates = [
        f"https://careers.{slug}.com",
        f"https://jobs.{slug}.com",
        f"https://{slug}.com/careers",
        f"https://{slug}.com/jobs",
    ]
    for url in candidates:
        try:
            resp = requests.get(url, timeout=5, headers=headers, allow_redirects=True)
            if resp.status_code == 200:
                return resp.url
        except Exception:
            continue

    return None


def parse_add_command(user_message: str) -> dict:
    """
    Use Claude to extract company name and intent from a natural language message.
    Returns: {"company_name": str, "url": str|None}
    """
    response = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=200,
        system=(
            "You extract company names from job bot commands. "
            "Reply with ONLY a JSON object like: "
            '{\"company\": \"Home Depot\", \"url\": null} '
            "If the user provides a URL, include it. Otherwise url is null. "
            "No explanation, just JSON."
        ),
        messages=[{"role": "user", "content": user_message}]
    )
    text = response.content[0].text.strip()
    import json
    try:
        data = json.loads(text)
        return {
            "company_name": data.get("company", "").strip(),
            "url": data.get("url")
        }
    except Exception:
        # Fallback: treat the whole message as the company name
        return {"company_name": user_message.strip(), "url": None}


async def discover_company(user_message: str) -> dict | None:
    """
    Full pipeline: parse command -> find URL -> detect ATS.
    Returns: {"name": str, "url": str, "ats_type": str|None} or None on failure.
    """
    parsed = parse_add_command(user_message)
    company_name = parsed["company_name"]
    url = parsed["url"]

    if not company_name:
        return None

    if not url:
        url = search_career_page(company_name)

    if not url:
        return None

    ats_type = detect_ats(url)

    # If no ATS detected from URL, follow redirect and check final URL
    if not ats_type:
        try:
            resp = requests.get(url, timeout=10, headers={"User-Agent": "Mozilla/5.0"}, allow_redirects=True)
            final_url = resp.url
            ats_type = detect_ats(final_url)
            if ats_type:
                url = final_url
        except Exception:
            pass

    return {
        "name": company_name,
        "url": url,
        "ats_type": ats_type
    }
