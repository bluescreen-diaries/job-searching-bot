# Job Bot

A Discord bot that automatically searches company career pages daily and posts new job listings matching your preferences directly to your Discord channel.

---

## What It Does

- Monitors company career pages for new job postings
- Filters jobs by your keywords (e.g. `data analyst, SQL, Python`)
- Filters by department/category per company (e.g. only `IT` or `Warehouse`)
- Posts new matches to your Discord channel every day at 8 AM
- Supports bulk importing companies from a `.txt` file
- Auto-detects the ATS (applicant tracking system) used by each company

---

## Tech Stack

| Tool | Purpose |
|------|---------|
| Python 3.14 | Core language |
| discord.py | Discord bot framework |
| Anthropic API (Claude Haiku) | Parses natural language commands, discovers career page URLs |
| APScheduler | Daily job at 8 AM |
| SQLite | Stores sources, preferences, and seen jobs |
| BeautifulSoup + requests | HTML scraping for generic career pages |

---

## Supported ATS Types

| ATS | How it's scraped |
|-----|-----------------|
| Greenhouse | Public JSON API |
| Lever | Public JSON API |
| Workday | Undocumented JSON API with full pagination |
| Generic | HTML scraping with next-page link following |

---

## Project Structure

```
job-bot/
├── main.py          # Discord bot and all slash commands
├── scheduler.py     # Daily search runner
├── discovery.py     # Auto-discovers career page URL from company name using DuckDuckGo + Claude
├── database.py      # SQLite: sources, preferences, seen_jobs tables
├── scrapers/
│   ├── base.py      # Base scraper class with keyword + category filtering
│   ├── greenhouse.py
│   ├── lever.py
│   ├── workday.py
│   └── generic.py   # HTML fallback with pagination
├── requirements.txt
└── .env             # Your API keys (not committed to git)
```

---

## Setup

### 1. Clone the repo

```bash
git clone https://github.com/yourusername/job-bot.git
cd job-bot
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Create your `.env` file

```
DISCORD_TOKEN=your-discord-bot-token
ANTHROPIC_API_KEY=your-anthropic-api-key
DISCORD_CHANNEL_ID=your-channel-id
```

### 4. Enable Discord Privileged Intents

1. Go to [discord.com/developers/applications](https://discord.com/developers/applications)
2. Select your app → **Bot**
3. Under **Privileged Gateway Intents**, enable **Message Content Intent**
4. Click **Save Changes**

### 5. Run the bot

```bash
python main.py
```

You should see `Logged in as <botname>` in the terminal. Keep the terminal open — closing it stops the bot.

---

## Commands

| Command | Description |
|---------|-------------|
| `/add <company>` | Auto-find and add a company's career page |
| `/add <company> \| <category>` | Add with department filter (e.g. `\| IT, Engineering`) |
| `/addurl <name> <url>` | Add a company with a direct URL |
| `/addurl <name> <url> <category>` | Add with a category filter |
| `/bulkadd` | Attach a `.txt` file to bulk add companies |
| `/remove <company>` | Stop watching a company |
| `/list` | Show all tracked companies |
| `/setpref keywords <keywords>` | Set job title keywords (comma separated) |
| `/setpref location <location>` | Set preferred location |
| `/prefs` | Show current preferences |
| `/search` | Run a search right now |
| `/help2` | Show command list in Discord |

---

## Bulk Import Format

Create a `.txt` file with one company per line. Attach it to a `/bulkadd` message in Discord.

```
Google
Stripe
Amazon | Warehouse, Operations
Home Depot https://careers.homedepot.com | IT
Anthropic https://www.anthropic.com/careers/jobs
```

- Lines with just a name → bot auto-discovers the career page URL
- Lines with a URL → uses that URL directly
- `| category` → only shows jobs from that department (supports multiple: `| IT, Engineering, Data`)
- No category → shows all jobs, filtered only by your keywords

---

## How Filtering Works

Every job goes through two filters:

1. **Keywords** (`/setpref keywords`) — checks job title and description. Set once, applies to all companies.
2. **Category** (set per company) — checks job title, department, and description. Only applies to that specific company.

A job must pass **both** filters to be posted.

---

## Notes

- The bot only checks career pages it can read directly. Pages that require you to type a location or select a filter before showing jobs won't work — copy the filtered URL from your browser instead and use `/addurl`.
- The bot tracks jobs it has already seen so it won't post duplicates.
- Jobs are checked once per day at 8 AM. Use `/search` to run manually.
