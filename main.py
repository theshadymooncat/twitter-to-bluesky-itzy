import os
import json
import re
import requests
import feedparser
from bs4 import BeautifulSoup
from atproto import Client

NITTER_RSS = "https://nitter.net/official_artms/rss"
NITTER_BASE = "https://nitter.net"
BLUESKY_HANDLE = os.environ["BLUESKY_HANDLE"]
BLUESKY_PASSWORD = os.environ["BLUESKY_PASSWORD"]
STATE_FILE = "seen_ids.json"

def load_seen():
    try:
        return set(json.load(open(STATE_FILE)))
    except (FileNotFoundError, json.JSONDecodeError):
        return set()

def save_seen(seen):
    with open(STATE_FILE, "w") as f:
        json.dump(list(seen), f)

def fetch_tweets():
    feed = feedparser.parse(NITTER_RSS)
    tweets = []
    for entry in feed.entries[:10]:
        if entry.title.startswith("RT by") or entry.title.startswith("R to"):
            continue
        tweet_id = entry.guid
        text = entry.title

        # Parse images from description
        soup = BeautifulSoup(entry.description, "html.parser")
        images = []
        for img in soup.find_all("img"):
            src = img.get("src", "")
            # Convert nitter image URLs to real twitter image URLs
            src = src.replace("https://nitter.net/pic/", "https://pbs.twimg.com/")
            src = requests.utils.unquote(src)
            images.append(src)

        tweets.append({"id": tweet_id, "text": text, "images": images})

    print(f"Fetched {len(tweets)} tweets")
    return tweets

def post_to_bluesky(text, images):
    try:
        bsky = Client()
        bsky.login(BLUESKY_HANDLE, BLUESKY_PASSWORD)

        image_blobs = []
        for url in images[:4]:  # Bluesky max 4 images
            try:
                resp = requests.get(url, timeout=10)
                blob = bsky.upload_blob(resp.content)
                image_blobs.append(blob.blob)
            except Exception as e:
                print(f"Failed to upload image {url}: {e}")

        if image_blobs:
            from atproto import models
            bsky.send_post(
                text=text[:300],
                embed=models.AppBskyEmbedImages.Main(
                    images=[
                        models.AppBskyEmbedImages.Image(
                            image=blob,
                            alt=""
                        ) for blob in image_blobs
                    ]
                )
            )
        else:
            bsky.send_post(text=text[:300])

        print("Posted to Bluesky:", text[:60])
    except Exception as e:
        print(f"Error posting to Bluesky: {e}")

def main():
    seen = load_seen()
    tweets = fetch_tweets()
    for tw in reversed(tweets):
        if tw["id"] in seen:
            continue
        print("Reposting:", tw["text"][:80])
        post_to_bluesky(tw["text"], tw["images"])
        seen.add(tw["id"])
    save_seen(seen)

if __name__ == "__main__":
    main()
