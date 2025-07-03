# mongo_client.py

import os
import re
from datetime import datetime
from pymongo import MongoClient, ASCENDING
from dotenv import load_dotenv

load_dotenv()

MONGO_HOST = os.getenv("MONGO_HOST", "localhost")
MONGO_PORT = int(os.getenv("MONGO_PORT", 27017))
MONGO_USER = os.getenv("MONGO_USER")
MONGO_PASS = os.getenv("MONGO_PASS")
MONGO_DB = os.getenv("MONGO_DB", "twitter_crawler_db")
MONGO_COL = os.getenv("MONGO_COLLECTION_NAME", "tweets")


def extract_hashtags(text):
    return re.findall(r"#\w+", text)


def parse_twitter_date(date_str):
    """Parse Twitter's date format to Python datetime object"""
    if isinstance(date_str, datetime):
        return date_str
    try:
        # Twitter format: "Wed Oct 10 20:19:24 +0000 2018"
        return datetime.strptime(date_str, "%a %b %d %H:%M:%S %z %Y")
    except:
        # Fallback to current time if parsing fails
        return datetime.utcnow()


class MongoDBClient:
    def __init__(self):
        uri = f"mongodb://{MONGO_USER}:{MONGO_PASS}@{MONGO_HOST}:{MONGO_PORT}"
        self.client = MongoClient(uri)
        self.db = self.client[MONGO_DB]
        self.col = self.db["tweets"]
        self.col.create_index([("created_at", ASCENDING)])
        self.col.create_index([("root_user_id", ASCENDING)])
        
        # Collection for trending keywords
        self.keywords_col = self.db["trending_keywords"]
        self.keywords_col.create_index([("timestamp", ASCENDING)])
        self.keywords_col.create_index([("root_user_id", ASCENDING)])
        
        # Run migrations on startup
        self._run_migrations()
    
    def _run_migrations(self):
        """Run database migrations using Flyway-like system"""
        try:
            from .db_migrations.migration_manager import MigrationManager
            migration_manager = MigrationManager(self.db)
            migration_manager.run_pending_migrations()
        except Exception as e:
            print(f"Migration warning: {e}")
            # Continue even if migrations fail in development
            # In production, you might want to fail fast

    def save_tweets(self, tweets, user_id, username):
        for tweet in tweets:
            if "full_text" not in tweet or "created_at" not in tweet:
                continue

            hashtags = [tag["text"] for tag in tweet.get("entities", {}).get("hashtags", [])]
            media = tweet.get("entities", {}).get("media", [])
            media_urls = [m.get("media_url_https") for m in media]
            media_type = [m.get("type") for m in media]

            doc = {
                "tweet_id": tweet.get("id_str"),
                "user_id": user_id,
                "username": username,
                "text": tweet["full_text"],
                "created_at": parse_twitter_date(tweet["created_at"]),
                "lang": tweet.get("lang", "unknown"),
                "hashtags": hashtags,
                "media_urls": media_urls,
                "media_type": media_type,
                "retweet_count": tweet.get("retweet_count", 0),
                "favorite_count": tweet.get("favorite_count", 0),
                "quote_count": tweet.get("quote_count", 0),
                "reply_count": tweet.get("reply_count", 0),
                "source": tweet.get("source", ""),
                "quoted_status_id": tweet.get("quoted_status_id_str")
            }

            self.col.insert_one(doc)

    def save_tweet(self, tweet, user_id, username, root_user_id=None):
        tweet_id = tweet.get("id_str")
        if not tweet_id:
            return

        hashtags = [tag["text"] for tag in tweet.get("entities", {}).get("hashtags", [])]
        media = tweet.get("entities", {}).get("media", [])
        media_urls = [m.get("media_url_https") for m in media]
        media_type = [m.get("type") for m in media]

        doc = {
            "tweet_id": tweet_id,
            "user_id": user_id,
            "username": username,
            "root_user_id": root_user_id or user_id,  # If no root_user_id provided, use user_id
            "text": tweet["full_text"],
            "created_at": parse_twitter_date(tweet["created_at"]),
            "lang": tweet.get("lang", "unknown"),
            "hashtags": hashtags,
            "media_urls": media_urls,
            "media_type": media_type,
            "retweet_count": tweet.get("retweet_count", 0),
            "favorite_count": tweet.get("favorite_count", 0),
            "quote_count": tweet.get("quote_count", 0),
            "reply_count": tweet.get("reply_count", 0),
            "source": tweet.get("source", ""),
            "quoted_status_id": tweet.get("quoted_status_id_str")
        }

        self.col.update_one(
            {"tweet_id": tweet_id},
            {"$set": doc},
            upsert=True
        )

    def load_texts(self, limit=600):
        docs = self.col.find().sort("created_at", -1).limit(limit)
        return [doc["text"] for doc in docs if "text" in doc]
    
    def load_recent_texts_per_user(self, tweets_per_user=20, root_user_id=None, 
                                  use_percentage=False, percent_tweets=40,
                                  time_filter_enabled=False, days_recent=30):
        """Load recent tweets, limiting to N tweets per user or percentage of user's tweets
        
        Args:
            tweets_per_user: Fixed number of tweets per user
            root_user_id: Root user ID to filter by
            use_percentage: Whether to use percentage-based selection
            percent_tweets: Percentage of recent tweets to get per user (0-100)
            time_filter_enabled: Whether to filter by time
            days_recent: Number of recent days to consider
        """
        pipeline = []
        
        # Build match stage
        match_stage = {}
        if root_user_id:
            match_stage["root_user_id"] = root_user_id
            
        # Add time filter if enabled
        if time_filter_enabled and days_recent > 0:
            from datetime import datetime, timedelta
            cutoff_date = datetime.utcnow() - timedelta(days=days_recent)
            match_stage["created_at"] = {"$gte": cutoff_date}
            
        if match_stage:
            pipeline.append({"$match": match_stage})
            
        pipeline.extend([
            {"$sort": {"created_at": -1}},
            {"$group": {
                "_id": "$username",
                "tweets": {"$push": {
                    "text": "$text",
                    "created_at": "$created_at",
                    "lang": "$lang"
                }},
                "total_count": {"$sum": 1}
            }}
        ])
        
        # If using percentage, we need to calculate dynamically
        if use_percentage:
            pipeline.append({
                "$project": {
                    "_id": 1,
                    "tweets": 1,
                    "total_count": 1,
                    "tweets_to_take": {
                        "$ceil": {
                            "$multiply": [
                                "$total_count",
                                percent_tweets / 100.0
                            ]
                        }
                    }
                }
            })
            pipeline.append({
                "$project": {
                    "_id": 1,
                    "tweets": {
                        "$slice": ["$tweets", "$tweets_to_take"]
                    }
                }
            })
        else:
            # Use fixed number
            pipeline.append({
                "$project": {
                    "_id": 1,
                    "tweets": {"$slice": ["$tweets", tweets_per_user]}
                }
            })
        
        texts = []
        for user_data in self.col.aggregate(pipeline):
            for tweet in user_data["tweets"]:
                texts.append(tweet["text"])
        
        return texts
    
    def save_trending_keywords(self, keywords, root_user_id, method="hybrid", ai_used=False, topics=None):
        """Save trending keywords with timestamp, root_user_id, and topics"""
        from datetime import datetime
        
        doc = {
            "timestamp": datetime.utcnow(),
            "root_user_id": root_user_id,
            "keywords": keywords,
            "method": method,
            "ai_used": ai_used
        }
        
        # Add topics if provided
        if topics:
            doc["topics"] = {
                "trending_topics": topics.get("trending_topics", []),
                "topics_count": topics.get("topics_count", 0),
                "topics_info": topics.get("topics_info", [])
            }
        
        return self.keywords_col.insert_one(doc)
    
    def get_latest_trending_keywords(self, root_user_id=None):
        """Get the most recent trending keywords for a specific root_user_id"""
        query = {}
        if root_user_id:
            query["root_user_id"] = root_user_id
            
        latest = self.keywords_col.find_one(
            query,
            sort=[("timestamp", -1)]
        )
        return latest if latest else None
    
    def get_topic_history(self, root_user_id=None, days=7):
        """Get topic history for trend analysis"""
        from datetime import datetime, timedelta
        
        query = {
            "timestamp": {"$gte": datetime.utcnow() - timedelta(days=days)},
            "topics": {"$exists": True}
        }
        if root_user_id:
            query["root_user_id"] = root_user_id
        
        cursor = self.keywords_col.find(query).sort("timestamp", -1)
        return list(cursor)
    
    def get_trending_topics_over_time(self, root_user_id=None, days=7, top_n=5):
        """Analyze how topics trend over time"""
        from collections import defaultdict
        from datetime import datetime, timedelta
        
        history = self.get_topic_history(root_user_id, days)
        
        # Group topics by day
        topics_by_day = defaultdict(lambda: defaultdict(int))
        
        for doc in history:
            day = doc["timestamp"].strftime("%Y-%m-%d")
            if "topics" in doc and "trending_topics" in doc["topics"]:
                for topic in doc["topics"]["trending_topics"][:top_n]:
                    topic_id = topic.get("topic_id", -1)
                    if topic_id != -1:
                        topics_by_day[day][topic_id] += topic.get("frequency", 0)
        
        return dict(topics_by_day)
    
    def get_all_root_users(self):
        """Get list of all unique root users with their IDs and usernames"""
        pipeline = [
            {"$group": {
                "_id": "$root_user_id",
                "username": {"$first": "$username"}
            }},
            {"$project": {
                "user_id": "$_id",
                "username": 1,
                "_id": 0
            }}
        ]
        return list(self.col.aggregate(pipeline))
