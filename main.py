import os
from dotenv import load_dotenv
load_dotenv()

import discord
from discord.ext import commands, tasks
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from database import (
    init_db, add_source, remove_source, list_sources,
    set_preference, get_all_preferences
)
from discovery import discover_company
from scheduler import run_job_search

TOKEN = os.getenv("DISCORD_TOKEN")
CHANNEL_ID = int(os.getenv("DISCORD_CHANNEL_ID", "0"))

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="/", intents=intents)
scheduler = AsyncIOScheduler()


# ── Helpers ──────────────────────────────────────────────────────────────────

async def get_job_channel():
    return bot.get_channel(CHANNEL_ID)


async def post_to_channel(text: str):
    channel = await get_job_channel()
    if channel:
        await channel.send(text)


# ── Events ───────────────────────────────────────────────────────────────────

@bot.event
async def on_ready():
    init_db()
    print(f"Logged in as {bot.user}")

    # Schedule daily search at 8 AM
    scheduler.add_job(
        daily_search_job,
        CronTrigger(hour=8, minute=0),
        id="daily_search",
        replace_existing=True
    )
    scheduler.start()
    print("Scheduler started. Daily search at 8:00 AM.")


async def daily_search_job():
    await run_job_search(post_to_channel)


# ── Commands ─────────────────────────────────────────────────────────────────

@bot.command(name="add")
async def add_company(ctx, *, query: str):
    """Add a company to watch. Usage: /add Home Depot | IT"""
    category = None
    if "|" in query:
        parts = query.split("|", 1)
        query = parts[0].strip()
        category = parts[1].strip()

    await ctx.send(f"Searching for **{query}** career page...")

    result = await discover_company(query)

    if not result:
        await ctx.send(f"Could not find a career page for **{query}**. Try `/addurl <name> <url>` to add it manually.")
        return

    success = add_source(result["name"], result["url"], result.get("ats_type"), category)
    ats_label = f" ({result['ats_type'].title()})" if result.get("ats_type") else ""
    cat_label = f" [category: {category}]" if category else ""

    if success:
        await ctx.send(f"Added **{result['name']}**{ats_label}{cat_label}\n{result['url']}")
    else:
        await ctx.send(f"**{result['name']}** is already in your list.")


@bot.command(name="addurl")
async def add_url(ctx, name: str, url: str, *, category: str = None):
    """Add a company with a specific URL. Usage: /addurl \"Home Depot\" https://careers.homedepot.com Warehouse"""
    from discovery import detect_ats
    ats_type = detect_ats(url)
    success = add_source(name, url, ats_type, category)
    ats_label = f" ({ats_type.title()})" if ats_type else ""
    cat_label = f" [category: {category}]" if category else ""
    if success:
        await ctx.send(f"Added **{name}**{ats_label}{cat_label}\n{url}")
    else:
        await ctx.send(f"**{name}** (or that URL) is already in your list.")


@bot.command(name="bulkadd")
async def bulk_add(ctx):
    """Bulk add companies from an attached .txt file (one per line). Supports 'Company Name' or 'Company Name https://url'"""
    if not ctx.message.attachments:
        await ctx.send("Please attach a `.txt` file. Each line: `Company Name` or `Company Name https://url`")
        return

    attachment = ctx.message.attachments[0]
    if not attachment.filename.endswith(".txt"):
        await ctx.send("Please attach a `.txt` file.")
        return

    content = (await attachment.read()).decode("utf-8")
    lines = [l.strip() for l in content.splitlines() if l.strip()]

    if not lines:
        await ctx.send("The file appears to be empty.")
        return

    await ctx.send(f"Processing **{len(lines)}** entries, this may take a moment...")

    added, skipped, failed = [], [], []

    for line in lines:
        # Split category by pipe: "Google | IT" or "Home Depot https://... | Warehouse"
        category = None
        if "|" in line:
            line, cat_part = line.split("|", 1)
            line = line.strip()
            category = cat_part.strip()

        parts = line.split()
        url = None
        if parts and parts[-1].startswith("http"):
            url = parts[-1]
            name = " ".join(parts[:-1])
        else:
            name = line.strip()
            url = None

        if not name:
            continue

        try:
            if url:
                from discovery import detect_ats
                ats_type = detect_ats(url)
                success = add_source(name, url, ats_type, category)
                if success:
                    added.append(name)
                else:
                    skipped.append(name)
            else:
                result = await discover_company(name)
                if not result:
                    failed.append(name)
                    continue
                success = add_source(result["name"], result["url"], result.get("ats_type"), category)
                if success:
                    added.append(result["name"])
                else:
                    skipped.append(result["name"])
        except Exception as e:
            failed.append(f"{name} ({e})")

    summary = f"**Bulk import complete:**\n✅ Added: {len(added)}\n⏭ Already existed: {len(skipped)}\n❌ Failed: {len(failed)}"
    if failed:
        summary += "\n\n**Failed:**\n" + "\n".join(f"• {f}" for f in failed)
    await ctx.send(summary)


@bot.command(name="remove")
async def remove_company(ctx, *, name: str):
    """Remove a company. Usage: /remove Home Depot"""
    success = remove_source(name)
    if success:
        await ctx.send(f"Removed **{name}** from your list.")
    else:
        await ctx.send(f"Could not find **{name}** in your list.")


@bot.command(name="list")
async def list_companies(ctx):
    """Show all tracked companies."""
    sources = list_sources()
    if not sources:
        await ctx.send("No companies tracked yet. Use `/add <company>` to add one.")
        return
    lines = [f"**Tracked companies ({len(sources)}):**"]
    for s in sources:
        ats = f" [{s['ats_type']}]" if s.get("ats_type") else ""
        cat = f" | {s['category']}" if s.get("category") else ""
        lines.append(f"• {s['name']}{ats}{cat} — {s['url']}")
    await ctx.send("\n".join(lines))


@bot.command(name="setpref")
async def set_pref(ctx, key: str, *, value: str):
    """Set a job preference. Usage: /setpref keywords data analyst, SQL, Python"""
    set_preference(key, value)
    await ctx.send(f"Preference set: **{key}** = `{value}`")


@bot.command(name="prefs")
async def show_prefs(ctx):
    """Show current preferences."""
    prefs = get_all_preferences()
    if not prefs:
        await ctx.send("No preferences set. Use `/setpref keywords <keywords>` to start.")
        return
    lines = ["**Current preferences:**"]
    for k, v in prefs.items():
        lines.append(f"• **{k}**: {v}")
    await ctx.send("\n".join(lines))


@bot.command(name="search")
async def manual_search(ctx):
    """Run a manual job search right now."""
    await ctx.send("Running job search now...")

    async def send(text):
        await ctx.send(text)

    await run_job_search(send)


@bot.command(name="help2")
async def help_cmd(ctx):
    """Show available commands."""
    help_text = """**Job Bot Commands:**

`/add <company name>` — auto-find and add a company's career page
`/add <company name> | <category>` — add with a category filter (e.g. `| IT`)
`/addurl <name> <url>` — add a company with a specific URL
`/addurl <name> <url> <category>` — add with a category filter
`/bulkadd` — attach a .txt file to bulk add companies (supports `| category`)
`/remove <company name>` — stop watching a company
`/list` — show all tracked companies
`/setpref keywords <keywords>` — set job title keywords (comma separated)
`/setpref location <location>` — set preferred location
`/prefs` — show current preferences
`/search` — run a search right now
`/help2` — show this message

**Examples:**
`/add Home Depot`
`/add Stripe`
`/setpref keywords data analyst, business analyst, SQL`
`/setpref location remote`
"""
    await ctx.send(help_text)


if __name__ == "__main__":
    bot.run(TOKEN)
