import feedparser
import requests
import json
import os
import time
import re
from datetime import datetime

WEBHOOK = os.getenv("DISCORD_WEBHOOK")

FEEDS = {
    "🆕 New Releases": "https://store.steampowered.com/feeds/newreleases.xml",
    "🔥 Daily Deals": "https://store.steampowered.com/feeds/daily_deals.xml"
}

DATA_DIR = "data"

SEEN_FILE = os.path.join(DATA_DIR, "seen.json")
HEARTBEAT_FILE = os.path.join(DATA_DIR, "heartbeat.json")
FULL_CHECK_FILE = os.path.join(DATA_DIR, "last_full_check.json")

FULL_CHECK_INTERVAL = 60 * 60 * 4  # 4h


# -------------------- INIT --------------------

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


# -------------------- DISCORD --------------------

def send_discord(payload):
    requests.post(WEBHOOK, json=payload)


def send_embed(title, url, feed_name, image_url=None):
    embed = {
        "title": title,
        "url": url,
        "description": f"Novo item em {feed_name}",
        "color": 3447003,
        "footer": {"text": "Steam RSS Bot"},
        "timestamp": datetime.utcnow().isoformat()
    }

    if image_url:
        embed["thumbnail"] = {"url": image_url}

    send_discord({"embeds": [embed]})


# -------------------- IMAGE EXTRACTION --------------------

def extract_image(entry):
    if "media_content" in entry and entry.media_content:
        return entry.media_content[0].get("url")

    if "media_thumbnail" in entry and entry.media_thumbnail:
        return entry.media_thumbnail[0].get("url")

    if "summary" in entry:
        match = re.search(r'<img.*src="(.*?)"', entry.summary)
        if match:
            return match.group(1)

    return None


# -------------------- HEARTBEAT --------------------

def should_send_heartbeat():
    today = datetime.utcnow().strftime("%Y-%m-%d")
    data = load_json(HEARTBEAT_FILE, {})
    return data.get("last_heartbeat") != today


def save_heartbeat():
    save_json(HEARTBEAT_FILE, {
        "last_heartbeat": datetime.utcnow().strftime("%Y-%m-%d")
    })


def send_heartbeat():
    now = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
    send_discord({
        "content": f"💓 Steam RSS Bot online — {now}"
    })


# -------------------- FULL CHECK --------------------

def should_run_full_check():
    data = load_json(FULL_CHECK_FILE, {"last_check": 0})
    return time.time() - data["last_check"] > FULL_CHECK_INTERVAL


def save_full_check():
    save_json(FULL_CHECK_FILE, {"last_check": time.time()})


# -------------------- FEED CHECK --------------------

def check_feed(feed_name, url, seen):
    print(f"Checking {feed_name}")

    feed = feedparser.parse(url)

    if feed_name not in seen:
        seen[feed_name] = []

    found = False

    for entry in feed.entries:
        uid = entry.get("id", entry.link)

        if uid in seen[feed_name]:
            continue

        image = extract_image(entry)

        send_embed(entry.title, entry.link, feed_name, image)

        seen[feed_name].append(uid)
        seen[feed_name] = seen[feed_name][-100:]

        found = True

    return found


# -------------------- MAIN --------------------

def main():
    ensure_data_dir()

    seen = load_seen()

    found_any = False

    if should_run_full_check():
        print("Running 4h full revision...")
        save_full_check()

    for name, url in FEEDS.items():
        if check_feed(name, url, seen):
            found_any = True

    save_seen(seen)

    if not found_any and should_send_heartbeat():
        send_heartbeat()
        save_heartbeat()


if __name__ == "__main__":
    main()
