# tweet_service.py

import time
import os
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Semaphore
from dotenv import load_dotenv
from .mongo_client import MongoDBClient
from .logger import setup_logger

# Setup logger
logger = setup_logger(__name__)

load_dotenv()

BASE_URL = "https://twitter241.p.rapidapi.com"
HEADERS = {
    "x-rapidapi-host": "twitter241.p.rapidapi.com",
    "x-rapidapi-key": os.getenv("RAPIDAPI_KEY")
}
DELAY_BETWEEN_REQUESTS = float(os.getenv("DELAY_BETWEEN_REQUESTS", 1.2))

# Rate limiter to control concurrent API calls
class RateLimiter:
    def __init__(self, max_concurrent_calls=1):
        self.semaphore = Semaphore(max_concurrent_calls)
        self.last_call_time = 0
        self.min_delay = DELAY_BETWEEN_REQUESTS / max_concurrent_calls
    
    def __enter__(self):
        self.semaphore.acquire()
        current_time = time.time()
        elapsed = current_time - self.last_call_time
        if elapsed < self.min_delay:
            time.sleep(self.min_delay - elapsed)
        self.last_call_time = time.time()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.semaphore.release()


# --- Resolve username to user ID ---
def resolve_user_id(username: str) -> str:
    try:
        url = f"{BASE_URL}/user"
        params = {"username": username}
        resp = requests.get(url, headers=HEADERS, params=params)
        resp.raise_for_status()
        data = resp.json()
        user_id = data.get("result", {}).get("data", {}).get("user", {}).get("result", {}).get("rest_id")
        return user_id or username  # nếu user_id là None thì trả về username
    except Exception as e:
        return username


def get_user_tweets(user_id: str, count: int = 20):
    url = f"{BASE_URL}/user-tweets"
    params = {"user": user_id, "count": count}
    resp = requests.get(url, headers=HEADERS, params=params)
    data = resp.json()
    tweets = []
    for instr in data.get("result", {}).get("timeline", {}).get("instructions", []):
        if instr.get("type") == "TimelineAddEntries":
            for entry in instr.get("entries", []):
                try:
                    tweet = entry["content"]["itemContent"]["tweet_results"]["result"]["legacy"]
                    tweets.append(tweet)
                except KeyError:
                    continue
    return tweets


# --- Get list of followings ---
def get_following(user_id: str, count: int = 20):
    url = f"{BASE_URL}/followings"
    users = []
    cursor = None
    
    while len(users) < count:
        # Build params with optional cursor
        params = {"user": user_id, "count": count}
        if cursor:
            params["cursor"] = cursor
            
        try:
            resp = requests.get(url, headers=HEADERS, params=params)
            resp.raise_for_status()
            data = resp.json()
            
            # Extract cursor for next page if it exists
            cursor_obj = data.get("cursor", {})
            next_cursor = cursor_obj.get("bottom") if cursor_obj else None
            
            # Extract users from response
            batch_users = []
            for instr in data.get("result", {}).get("timeline", {}).get("instructions", []):
                if instr.get("type") == "TimelineAddEntries":
                    entries = instr.get("entries", [])
                    for entry in entries:
                        try:
                            # Skip cursor entries
                            if entry.get("entryId", "").startswith("cursor-"):
                                continue
                                
                            user_result = entry["content"]["itemContent"]["user_results"]["result"]
                            rest_id = user_result.get("rest_id")
                            screen_name = user_result.get("legacy", {}).get("screen_name")
                            if rest_id and screen_name:
                                batch_users.append((rest_id, screen_name))
                        except KeyError:
                            continue
            
            # Add users from this batch
            users.extend(batch_users)
            
            # If we have enough users, return the requested count
            if len(users) >= count:
                return users[:count]
            
            # If no cursor or no more users in this batch, we've reached the end
            if not next_cursor or not batch_users:
                break
                
            cursor = next_cursor
            # Add delay between requests to avoid rate limiting
            time.sleep(DELAY_BETWEEN_REQUESTS)
            
        except Exception as e:
            logger.error(f"Error fetching followings: {e}")
            break
    
    return users


def fetch_user_tweets_concurrent(user_data, tweet_limit, mongo, root_user_id, rate_limiter):
    """Fetch tweets for a single user with rate limiting"""
    f_user_id, f_username = user_data
    try:
        with rate_limiter:
            tweets = get_user_tweets(f_user_id, count=tweet_limit)
            for tweet in tweets:
                mongo.save_tweet(tweet, f_user_id, f_username, root_user_id)
            logger.info(f"Fetched {len(tweets)} tweets for user {f_username}")
            return f_user_id, f_username, len(tweets)
    except Exception as e:
        logger.error(f"Error fetching tweets for user {f_username}: {e}")
        return f_user_id, f_username, 0


def crawl_user_and_following(
        user_id: str,
        username: str,
        depth: int = 1,
        per_user_limit: int = 10,
        tweet_limit: int = 20,
        visited=None,
        include_root=True,
        mongo=None,
        root_user_id=None,
        concurrent_threads=1
):
    if visited is None:
        visited = set()
    if user_id in visited:
        return

    visited.add(user_id)
    if mongo is None:
        mongo = MongoDBClient()
    
    # Set root_user_id for the first call
    if root_user_id is None:
        root_user_id = user_id

    if include_root:
        logger.info(f"Include root user {user_id}")
        tweets = get_user_tweets(user_id, count=tweet_limit)
        for tweet in tweets:
            mongo.save_tweet(tweet, user_id, username, root_user_id)
        time.sleep(DELAY_BETWEEN_REQUESTS)

    if depth <= 0:
        return

    logger.info(f"Get followings!!!")
    followings = get_following(user_id, count=per_user_limit)
    logger.info(f"Number of following got: {len(followings)}")
    
    # Use ThreadPoolExecutor for concurrent API calls
    rate_limiter = RateLimiter(max_concurrent_calls=concurrent_threads)
    
    with ThreadPoolExecutor(max_workers=concurrent_threads) as executor:
        # Submit all tweet fetching tasks
        future_to_user = {
            executor.submit(fetch_user_tweets_concurrent, user_data, tweet_limit, mongo, root_user_id, rate_limiter): user_data
            for user_data in followings
        }
        
        # Process completed tasks and collect users for recursive crawling
        users_to_crawl = []
        for future in as_completed(future_to_user):
            user_data = future_to_user[future]
            try:
                f_user_id, f_username, tweet_count = future.result()
                if tweet_count > 0:
                    users_to_crawl.append((f_user_id, f_username))
            except Exception as e:
                logger.error(f"Error processing user {user_data}: {e}")
    
    # Recursively crawl following users (still sequential for depth control)
    for f_user_id, f_username in users_to_crawl:
        crawl_user_and_following(
            f_user_id,
            f_username,
            depth - 1,
            per_user_limit,
            tweet_limit,
            visited,
            include_root=False,
            mongo=mongo,
            root_user_id=root_user_id,
            concurrent_threads=concurrent_threads
        )


def run_service(
        username: str,
        depth: int = 2,
        per_user_limit: int = 10,
        tweet_limit: int = 20,
        include_root: bool = True,
        concurrent_threads: int = 1
):
    user_id = resolve_user_id(username)
    mongo = MongoDBClient()
    time.sleep(DELAY_BETWEEN_REQUESTS)
    crawl_user_and_following(
        user_id,
        username,
        depth=depth,
        per_user_limit=per_user_limit,
        tweet_limit=tweet_limit,
        include_root=include_root,
        mongo=mongo,
        root_user_id=user_id,
        concurrent_threads=concurrent_threads
    )
