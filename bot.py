import feedparser
import requests
import json
import os
from datetime import datetime

WEBHOOK = os.getenv("DISCORD_WEBHOOK")

SCAN_MODE = os.getenv("SCAN_MODE", "normal")

DEEP_SCAN = "schedule" in SCAN_MODE

FEEDS = {
    "🆕 New Releases": "https://store.steampowered.com/feeds/newreleases.xml",
    "🔥 Daily Deals": "https://store.steampowered.com/feeds/daily_deals.xml",
    "🆓 Steam Collection": "https://store.steampowered.com/feeds/news/collection/steam"
}

DATA_DIR = "data"
SEEN_FILE = os.path.join(DATA_DIR, "seen.json")


# ---------------- INIT ----------------

def ensure():
    os.makedirs(DATA_DIR, exist_ok=True)


def load_seen():
    if not os.path.exists(SEEN_FILE):
        return {}
    with open(SEEN_FILE, "r") as f:
        return json.load(f)


def save_seen(data):
    with open(SEEN_FILE, "w") as f:
        json.dump(data, f, indent=2)


# ---------------- DISCORD ----------------

def send(title, link, feed):
    requests.post(WEBHOOK, json={
        "embeds": [{
            "title": title,
            "url": link,
            "description": f"Novo item em {feed}",
            "color": 3447003,
            "footer": {"text": "Steam RSS Bot"},
            "timestamp": datetime.utcnow().isoformat()
        }]
    })


def heartbeat():
    now = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")

    requests.post(WEBHOOK, json={
        "content": f"💓 Steam RSS Bot alive — {now} ({'DEEP' if DEEP_SCAN else 'NORMAL'})"
    })


# ---------------- FEED CHECK ----------------

def check_feed(name, url, seen):
    feed = feedparser.parse(url)

    if name not in seen:
        seen[name] = []

    found = False

    for entry in feed.entries:
        uid = entry.get("id", entry.link)

        # NORMAL: evita duplicados
        if not DEEP_SCAN and uid in seen[name]:
            continue

        send(entry.title, entry.link, name)

        if not DEEP_SCAN:
            seen[name].append(uid)
            seen[name] = seen[name][-200:]

        found = True

    return found


# ---------------- MAIN ----------------

def main():
    ensure()

    seen = load_seen()

    any_new = False

    for name, url in FEEDS.items():
        if check_feed(name, url, seen):
            any_new = True

    save_seen(seen)

    if not any_new:
        heartbeat()


if __name__ == "__main__":
    main()
