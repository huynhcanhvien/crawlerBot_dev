"""
Scheduler module for periodic tweet crawling and trending keyword analysis
"""

import json
import os
import time
import threading
import schedule
from datetime import datetime
from typing import Dict, List, Optional
from dotenv import load_dotenv

from .tweet_service import run_service, resolve_user_id
from .keyword_analysis import analyze_trending_keywords
from .mongo_client import MongoDBClient
from .logger import setup_logger
from .services.telegram_service import get_telegram_service

# Setup logger
logger = setup_logger(__name__)

load_dotenv()


class TaskScheduler:
    def __init__(self, config_path: str = "scheduler_config.json"):
        self.config_path = config_path
        self.config = self.load_config()
        self.running = False
        self.thread = None
        self.mongo = MongoDBClient()

        # Create a collection for task status tracking
        self.task_status_col = self.mongo.db["scheduler_tasks"]
        self.task_status_col.create_index([("timestamp", -1)])
        self.task_status_col.create_index([("root_user_id", 1)])

    def load_config(self) -> Dict:
        """Load configuration from JSON file"""
        try:
            with open(self.config_path, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            logger.warning(f"Config file {self.config_path} not found. Using defaults.")
            return self.get_default_config()

    def save_config(self):
        """Save current configuration to file"""
        with open(self.config_path, 'w') as f:
            json.dump(self.config, f, indent=2)

    def get_default_config(self) -> Dict:
        """Get default configuration"""
        return {
            "scheduler": {
                "interval_seconds": 3600,
                "enabled": True
            },
            "root_users": [],
            "default_config": {
                "crawl": {
                    "depth": 1,
                    "max_following": 30,
                    "max_tweets": 20,
                    "include_root": True
                },
                "analysis": {
                    "top_n": 20,
                    "tweets_per_user": 15,
                    "use_ai": False,
                    "ai_provider": "gemini"
                },
                "telegram": {
                    "enabled": False,
                    "post_after_analysis": True,
                    "include_topics": False
                }
            }
        }

    def add_root_user(self, username: str, crawl_config: Dict = None,
                      analysis_config: Dict = None, telegram_config: Dict = None):
        """Add a new root user to monitor"""
        # Resolve user ID
        user_id = resolve_user_id(username)
        if not user_id:
            raise ValueError(f"Could not resolve user ID for {username}")

        # Check if user already exists
        for user in self.config["root_users"]:
            if user["username"] == username or user.get("user_id") == user_id:
                raise ValueError(f"User {username} already exists in configuration")

        # Use default configs if not provided
        if not crawl_config:
            crawl_config = self.config["default_config"]["crawl"].copy()
        if not analysis_config:
            analysis_config = self.config["default_config"]["analysis"].copy()
        if not telegram_config:
            telegram_config = self.config["default_config"]["telegram"].copy()

        new_user = {
            "username": username,
            "user_id": user_id,
            "enabled": True,
            "crawl_config": crawl_config,
            "analysis_config": analysis_config,
            "telegram_config": telegram_config
        }

        self.config["root_users"].append(new_user)
        self.save_config()
        return new_user

    def remove_root_user(self, username: str = None, user_id: str = None):
        """Remove a root user from monitoring"""
        self.config["root_users"] = [
            user for user in self.config["root_users"]
            if user["username"] != username and user.get("user_id") != user_id
        ]
        self.save_config()

    def update_root_user(self, username: str = None, user_id: str = None,
                         enabled: bool = None, crawl_config: Dict = None,
                         analysis_config: Dict = None, telegram_config: Dict = None):
        """Update root user configuration"""
        for user in self.config["root_users"]:
            if user["username"] == username or user.get("user_id") == user_id:
                if enabled is not None:
                    user["enabled"] = enabled
                if crawl_config:
                    user["crawl_config"].update(crawl_config)
                if analysis_config:
                    user["analysis_config"].update(analysis_config)
                if telegram_config:
                    user.setdefault("telegram_config", {}).update(telegram_config)
                self.save_config()
                return user
        raise ValueError(f"User not found: {username or user_id}")

    def log_task_status(self, root_user_id: str, username: str, task_type: str,
                        status: str, details: Dict = None):
        """Log task execution status"""
        doc = {
            "timestamp": datetime.utcnow(),
            "root_user_id": root_user_id,
            "username": username,
            "task_type": task_type,  # "crawl" or "analysis"
            "status": status,  # "started", "completed", "failed"
            "details": details or {}
        }
        self.task_status_col.insert_one(doc)

    def get_task_history(self, root_user_id: str = None, limit: int = 50):
        """Get task execution history"""
        query = {}
        if root_user_id:
            query["root_user_id"] = root_user_id

        return list(self.task_status_col.find(query).sort("timestamp", -1).limit(limit))

    def run_task_for_user(self, user_config: Dict):
        """Run crawl and analysis task for a single user"""
        username = user_config["username"]
        user_id = user_config.get("user_id")

        # Resolve user_id if not set
        if not user_id:
            user_id = resolve_user_id(username)
            if user_id:
                user_config["user_id"] = user_id
                self.save_config()
            else:
                self.log_task_status(
                    username, username, "crawl", "failed",
                    {"error": "Could not resolve user ID"}
                )
                return

        logger.info(f"\n[{datetime.now()}] Starting scheduled task for @{username} (ID: {user_id})")

        # 1. Crawl tweets
        crawl_config = user_config["crawl_config"]
        try:
            self.log_task_status(user_id, username, "crawl", "started", crawl_config)

            start_time = time.time()
            run_service(
                username=username,
                depth=crawl_config["depth"],
                per_user_limit=crawl_config["max_following"],
                tweet_limit=crawl_config["max_tweets"],
                include_root=crawl_config["include_root"],
                concurrent_threads=crawl_config.get("concurrent_threads", 1)
            )

            crawl_duration = time.time() - start_time
            self.log_task_status(
                user_id, username, "crawl", "completed",
                {"duration": crawl_duration, **crawl_config}
            )
            logger.info(f"✅ Crawling completed for @{username} in {crawl_duration:.2f}s")

        except Exception as e:
            self.log_task_status(
                user_id, username, "crawl", "failed",
                {"error": str(e), **crawl_config}
            )
            logger.error(f"❌ Crawling failed for @{username}: {e}")
            return

        # 2. Analyze trending keywords
        analysis_config = user_config["analysis_config"]
        try:
            self.log_task_status(user_id, username, "analysis", "started", analysis_config)

            start_time = time.time()
            # Extract new configuration options
            use_percentage = analysis_config.get("use_percentage", False)
            percent_tweets = analysis_config.get("percent_tweets_per_user", 40)
            time_filter = analysis_config.get("time_filter", {})
            time_filter_enabled = time_filter.get("enabled", False)
            days_recent = time_filter.get("days_recent", 30)
            
            result = analyze_trending_keywords(
                texts=None,  # Load from DB
                top_n=analysis_config["top_n"],
                tweets_per_user=analysis_config.get("tweets_per_user", 10),
                use_ai=analysis_config["use_ai"],
                ai_provider=analysis_config.get("ai_provider"),  # Will use env var if not specified
                save_to_db=True,
                root_user_id=user_id,
                use_percentage=use_percentage,
                percent_tweets=percent_tweets,
                time_filter_enabled=time_filter_enabled,
                days_recent=days_recent
            )

            analysis_duration = time.time() - start_time
            self.log_task_status(
                user_id, username, "analysis", "completed",
                {
                    "duration": analysis_duration,
                    "total_texts": result.get("total_analyzed_texts", 0),
                    "keywords_found": len(result.get("keywords", [])),
                    **analysis_config
                }
            )
            logger.info(f"✅ Analysis completed for @{username} in {analysis_duration:.2f}s")
            logger.info(
                f"   Found {len(result.get('keywords', []))} trending keywords from {result.get('total_analyzed_texts', 0)} texts")

            # 3. Post to Telegram if enabled
            telegram_config = user_config.get("telegram_config", {})
            if telegram_config.get("enabled", False) and telegram_config.get("post_after_analysis", True):
                try:
                    telegram_service = get_telegram_service()

                    # Use the same format as returned by analyze_trending_keywords
                    trending_data = {
                        "keywords": result.get("keywords", []),
                        "total_analyzed_texts": result.get("total_analyzed_texts", 0),
                        "language_distribution": result.get("language_distribution", {}),
                        "topics": result.get("topics", {}),
                        "method": result.get("method", "hybrid"),
                        "ai_used": result.get("ai_used", False),
                        "include_topics": telegram_config.get("include_topics", False)
                    }

                    # Post to Telegram
                    telegram_success = telegram_service.send_trending_keywords(trending_data)

                    if telegram_success:
                        logger.info(f"✅ Posted trending keywords to Telegram for @{username}")
                        self.log_task_status(
                            user_id, username, "telegram", "completed",
                            {"keywords_count": len(result.get("keywords", []))}
                        )
                    else:
                        logger.warning(f"⚠️ Failed to post to Telegram for @{username}")
                        self.log_task_status(
                            user_id, username, "telegram", "failed",
                            {"error": "Failed to send message"}
                        )
                except ValueError as ve:
                    # Missing Telegram configuration
                    logger.warning(f"⚠️ Telegram posting skipped for @{username}: {ve}")
                    self.log_task_status(
                        user_id, username, "telegram", "skipped",
                        {"error": str(ve)}
                    )
                except Exception as te:
                    logger.error(f"❌ Telegram posting error for @{username}: {te}")
                    self.log_task_status(
                        user_id, username, "telegram", "failed",
                        {"error": str(te)}
                    )

        except Exception as e:
            self.log_task_status(
                user_id, username, "analysis", "failed",
                {"error": str(e), **analysis_config}
            )
            logger.error(f"❌ Analysis failed for @{username}: {e}")

    def run_all_tasks(self):
        """Run tasks for all enabled users"""
        logger.info(f"\n{'=' * 60}")
        logger.info(f"[{datetime.now()}] Running scheduled tasks")
        logger.info(f"{'=' * 60}")

        # Log start of analysis
        logger.info("Starting keyword analysis with unified NLP service...")

        enabled_users = [u for u in self.config["root_users"] if u.get("enabled", True)]

        if not enabled_users:
            logger.warning("No enabled users found in configuration")
            return

        for user_config in enabled_users:
            try:
                self.run_task_for_user(user_config)
                # Add delay between users to avoid rate limiting
                time.sleep(5)
            except Exception as e:
                logger.error(f"Error processing user {user_config['username']}: {e}")

        logger.info(f"\n[{datetime.now()}] All scheduled tasks completed")

    def schedule_jobs(self):
        """Schedule periodic jobs"""
        interval = self.config["scheduler"].get("interval_seconds", 3600)

        # Schedule the job
        schedule.every(interval).seconds.do(self.run_all_tasks)

        # Also run immediately on start
        self.run_all_tasks()

        logger.info(f"\n📅 Scheduler started - running every {interval} seconds ({interval / 60:.1f} minutes)")
        logger.info(f"Monitoring {len(self.config['root_users'])} users")

    def run_scheduler(self):
        """Run the scheduler in a separate thread"""
        while self.running:
            schedule.run_pending()
            time.sleep(1)  # Check every second for more responsive scheduling

    def start(self):
        """Start the scheduler"""
        if not self.config["scheduler"]["enabled"]:
            logger.warning("Scheduler is disabled in configuration")
            return

        if self.running:
            logger.warning("Scheduler is already running")
            return

        self.running = True
        self.schedule_jobs()

        # Run in a separate thread
        self.thread = threading.Thread(target=self.run_scheduler, daemon=True)
        self.thread.start()

        return True

    def stop(self):
        """Stop the scheduler"""
        self.running = False
        if self.thread:
            self.thread.join(timeout=5)
        schedule.clear()
        logger.info("Scheduler stopped")

    def get_status(self):
        """Get scheduler status"""
        return {
            "running": self.running,
            "enabled": self.config["scheduler"]["enabled"],
            "interval_seconds": self.config["scheduler"].get("interval_seconds", 3600),
            "monitored_users": len(self.config["root_users"]),
            "enabled_users": len([u for u in self.config["root_users"] if u.get("enabled", True)]),
            "next_run": str(schedule.next_run()) if schedule.jobs else None
        }


# Global scheduler instance
scheduler = None


def get_scheduler():
    """Get or create the global scheduler instance"""
    global scheduler
    if scheduler is None:
        scheduler = TaskScheduler()
    return scheduler
