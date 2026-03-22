import os
import json
import snscrape.modules.twitter as sntwitter
from atproto import Client

TWITTER_HANDLE = os.environ["TWITTER_HANDLE"]
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
    tweets = []
    try:
        for tweet in sntwitter.TwitterUserScraper(TWITTER_HANDLE).get_items():
            if len(tweets) >= 10:
                break
            if tweet.rawContent.startswith("RT @") or tweet.inReplyToTweetId:
                continue
            tweets.append({"id": str(tweet.id), "text": tweet.rawContent})
        print(f"Fetched {len(tweets)} tweets from @{TWITTER_HANDLE}")
    except Exception as e:
        print(f"Error fetching tweets: {e}")
    return tweets

def post_to_bluesky(text):
    try:
        bsky = Client()
        bsky.login(BLUESKY_HANDLE, BLUESKY_PASSWORD)
        bsky.send_post(text=text[:300])
        print("Posted to Bluesky:", text[:60])
    except Exception as e:
        print(f"Error posting to Bluesky: {e}")

def main():
    seen = load_seen()
    tweets = fetch_tweets()
    for tw in reversed(tweets):  # oldest first
        if tw["id"] in seen:
            continue
        print("Reposting:", tw["text"][:80])
        post_to_bluesky(tw["text"])
        seen.add(tw["id"])
    save_seen(seen)

if __name__ == "__main__":
    main()
