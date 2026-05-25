import feedparser
import requests
import json
import os
import time
from datetime import datetime

WEBHOOK = os.getenv("DISCORD_WEBHOOK")

FEEDS = {
    "🆕 New Releases": "https://store.steampowered.com/feeds/newreleases.xml",
    "🔥 Daily Deals": "https://store.steampowered.com/feeds/daily_deals.xml",
    "📰 Steam News": "https://store.steampowered.com/feeds/news.xml"
}

DATA_DIR = "data"

SEEN_FILE = os.path.join(DATA_DIR, "seen.json")
HEARTBEAT_FILE = os.path.join(DATA_DIR, "heartbeat.json")
FULL_CHECK_FILE = os.path.join(DATA_DIR, "last_full_check.json")

FULL_CHECK_INTERVAL = 60 * 60 * 4  # 4 horas


def ensure_data_dir():
    os.makedirs(DATA_DIR, exist_ok=True)


def load_json(path, default):
    if not os.path.exists(path):
        return default

    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def load_seen():
    return load_json(SEEN_FILE, {})


def save_seen(seen):
    save_json(SEEN_FILE, seen)


def send_discord_message(content=None, embeds=None):
    payload = {}

    if content:
        payload["content"] = content

    if embeds:
        payload["embeds"] = embeds

    response = requests.post(WEBHOOK, json=payload)

    if response.status_code not in [200, 204]:
        print("Discord error:", response.text)


def send_feed_item(feed_name, title, link):
    embeds = [
        {
            "title": title,
            "url": link,
            "description": f"Novo item em {feed_name}",
            "color": 3447003,
            "footer": {
                "text": "Steam RSS Bot"
            },
            "timestamp": datetime.utcnow().isoformat()
        }
    ]

    send_discord_message(embeds=embeds)


def should_send_heartbeat():
    today = datetime.utcnow().strftime("%Y-%m-%d")

    data = load_json(HEARTBEAT_FILE, {})

    return data.get("last_heartbeat") != today


def save_heartbeat():
    today = datetime.utcnow().strftime("%Y-%m-%d")

    save_json(HEARTBEAT_FILE, {
        "last_heartbeat": today
    })


def send_heartbeat():
    now = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")

    send_discord_message(
        content=f"💓 Steam RSS Bot alive — {now}"
    )


def should_run_full_check():
    data = load_json(FULL_CHECK_FILE, {
        "last_check": 0
    })

    last_check = data.get("last_check", 0)

    return time.time() - last_check > FULL_CHECK_INTERVAL


def save_full_check():
    save_json(FULL_CHECK_FILE, {
        "last_check": time.time()
    })


def check_feed(feed_name, url, seen):
    print(f"Checking {feed_name}")

    found_new = False

    feed = feedparser.parse(url)

    if feed_name not in seen:
        seen[feed_name] = []

    for entry in feed.entries:
        uid = entry.get("id", entry.link)

        if uid in seen[feed_name]:
            continue

        title = entry.title
        link = entry.link

        print(f"New item: {title}")

        send_feed_item(feed_name, title, link)

        seen[feed_name].append(uid)

        seen[feed_name] = seen[feed_name][-100:]

        found_new = True

    return found_new


def main():
    ensure_data_dir()

    seen = load_seen()

    found_anything = False

    full_check = should_run_full_check()

    if full_check:
        print("Running 4h full revision...")
        save_full_check()

    for feed_name, url in FEEDS.items():
        result = check_feed(feed_name, url, seen)

        if result:
            found_anything = True

    save_seen(seen)

    if not found_anything and should_send_heartbeat():
        send_heartbeat()
        save_heartbeat()


if __name__ == "__main__":
    main()
