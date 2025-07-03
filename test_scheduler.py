#!/usr/bin/env python3
"""
Test script for the scheduler functionality - supports both API and direct testing
"""

import requests
import json
import time
from datetime import datetime
import sys
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configuration
BASE_URL = "http://localhost:5000"
USERNAME = os.getenv("AUTH_USERNAME", "admin")
PASSWORD = os.getenv("AUTH_PASSWORD", "admin")

# For direct scheduler testing
try:
    from app.scheduler import TaskScheduler

    DIRECT_MODE_AVAILABLE = True
except ImportError:
    DIRECT_MODE_AVAILABLE = False


def get_auth_token():
    """Login and get JWT token"""
    response = requests.post(f"{BASE_URL}/auth/login", json={
        "username": USERNAME,
        "password": PASSWORD
    })
    if response.status_code == 200:
        return response.json()["access_token"]
    else:
        print(f"Login failed: {response.json()}")
        return None


def test_scheduler_status(token):
    """Test getting scheduler status"""
    print("\n1. Testing scheduler status...")
    response = requests.get(f"{BASE_URL}/scheduler/status",
                            headers={"Authorization": f"Bearer {token}"})
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    return response.json()


def test_get_scheduled_users(token):
    """Test getting scheduled users"""
    print("\n2. Testing get scheduled users...")
    response = requests.get(f"{BASE_URL}/scheduler/users",
                            headers={"Authorization": f"Bearer {token}"})
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    return response.json()


def test_add_user(token, username="testuser123"):
    """Test adding a user to scheduler"""
    print(f"\n3. Testing add user '{username}' to scheduler...")
    data = {
        "username": username,
        "crawl_config": {
            "depth": 1,
            "max_following": 5,
            "max_tweets": 10,
            "include_root": True
        },
        "analysis_config": {
            "top_n": 10,
            "tweets_per_user": 5,
            "use_ai": False,
            "ai_provider": "claude"
        }
    }
    response = requests.post(f"{BASE_URL}/scheduler/users",
                             json=data,
                             headers={"Authorization": f"Bearer {token}"})
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    return response.json()


def test_start_scheduler(token):
    """Test starting the scheduler"""
    print("\n4. Testing start scheduler...")
    response = requests.post(f"{BASE_URL}/scheduler/start",
                             headers={"Authorization": f"Bearer {token}"})
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    return response.json()


def test_run_now(token, username=None):
    """Test running scheduler immediately"""
    print(f"\n5. Testing run now{' for ' + username if username else ''}...")
    data = {}
    if username:
        data["username"] = username

    response = requests.post(f"{BASE_URL}/scheduler/run-now",
                             json=data,
                             headers={"Authorization": f"Bearer {token}"})
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    return response.json()


def test_get_history(token, root_user_id=None):
    """Test getting scheduler history"""
    print("\n6. Testing get scheduler history...")
    params = {"limit": 10}
    if root_user_id:
        params["root_user_id"] = root_user_id

    response = requests.get(f"{BASE_URL}/scheduler/history",
                            params=params,
                            headers={"Authorization": f"Bearer {token}"})
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    return response.json()


def test_update_user(token, username="namvanhoatagvn"):
    """Test updating a user configuration"""
    print(f"\n7. Testing update user '{username}'...")
    data = {
        "enabled": True,
        "crawl_config": {
            "max_following": 10,
            "max_tweets": 15
        }
    }
    response = requests.put(f"{BASE_URL}/scheduler/users/{username}",
                            json=data,
                            headers={"Authorization": f"Bearer {token}"})
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    return response.json()


def test_stop_scheduler(token):
    """Test stopping the scheduler"""
    print("\n8. Testing stop scheduler...")
    response = requests.post(f"{BASE_URL}/scheduler/stop",
                             headers={"Authorization": f"Bearer {token}"})
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    return response.json()


def test_get_trending_latest(token, root_user_id=None):
    """Test getting latest trending keywords"""
    print("\n9. Testing get latest trending keywords...")
    params = {}
    if root_user_id:
        params["root_user_id"] = root_user_id

    response = requests.get(f"{BASE_URL}/trending/latest",
                            params=params,
                            headers={"Authorization": f"Bearer {token}"})
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    return response.json()


def test_direct_quick_schedule(interval_seconds=30, use_ai=False):
    """Test scheduler directly with a quick interval"""
    if not DIRECT_MODE_AVAILABLE:
        print("Direct mode not available. Please run from project root.")
        return

    print(f"\n🧪 Testing scheduler with {interval_seconds} seconds interval...")
    
    # Get AI configuration from environment
    ai_provider = os.getenv("AI_PROVIDER", "claude")
    if use_ai:
        print(f"🤖 AI Provider: {ai_provider} (from .env)")

    # Create test config
    test_config = {
        "scheduler": {
            "interval_seconds": interval_seconds,
            "enabled": True
        },
        "root_users": [
            {
                "username": "namvanhoatagvn",
                "user_id": "1498274549057548288",
                "enabled": True,
                "crawl_config": {
                    "depth": 1,
                    "max_following": 100,  # Small number for testing
                    "max_tweets": 20,  # Small number for testing
                    "include_root": False
                },
                "analysis_config": {
                    "top_n": 20,
                    "tweets_per_user": 10,
                    "use_ai": use_ai
                    # ai_provider will be taken from env
                }
            }
        ],
        "default_config": {
            "crawl": {
                "depth": 1,
                "max_following": 100,
                "max_tweets": 20,
                "include_root": False
            },
            "analysis": {
                "top_n": 20,
                "tweets_per_user": 10,
                "use_ai": use_ai
                # ai_provider will be taken from env
            }
        }
    }

    # Save test config
    with open("scheduler_config_test.json", 'w') as f:
        json.dump(test_config, f, indent=2)

    # Create scheduler with test config
    scheduler = TaskScheduler(config_path="scheduler_config_test.json")

    print(f"📋 Scheduler Configuration:")
    print(f"   - Interval: {interval_seconds} seconds")
    print(f"   - Users: {len(scheduler.config['root_users'])}")
    print(f"   - AI Analysis: {'Enabled' if use_ai else 'Disabled'}")
    if use_ai:
        print(f"   - AI Provider: {ai_provider}")
    print(f"   - Enabled: {scheduler.config['scheduler']['enabled']}")

    # Start scheduler
    scheduler.start()

    print(f"\n⏰ Scheduler started! Will run every {interval_seconds} seconds")
    print("📌 First run executes immediately, then waits for the interval")
    print("🛑 Press Ctrl+C to stop the test\n")

    try:
        while True:
            status = scheduler.get_status()
            print(
                f"[{datetime.now().strftime('%H:%M:%S')}] Status: {'🟢 Running' if status['running'] else '🔴 Stopped'} | Next run: {status['next_run']}")
            time.sleep(20)
    except KeyboardInterrupt:
        print("\n\n🛑 Stopping scheduler...")
        scheduler.stop()
        print("✅ Test completed!")


def test_direct_manual_run(use_ai=None):
    """Test running scheduler tasks manually"""
    if not DIRECT_MODE_AVAILABLE:
        print("Direct mode not available. Please run from project root.")
        return

    print("\n🧪 Testing manual task execution...")
    
    # If use_ai is specified, temporarily update the config
    if use_ai is not None:
        scheduler = TaskScheduler()
        
        # Update all users to use/not use AI
        for user in scheduler.config.get("root_users", []):
            if "analysis_config" in user:
                user["analysis_config"]["use_ai"] = use_ai
        
        ai_provider = os.getenv("AI_PROVIDER", "claude")
        print(f"📋 Running with AI: {'Enabled' if use_ai else 'Disabled'}")
        if use_ai:
            print(f"🤖 AI Provider: {ai_provider}")
    else:
        scheduler = TaskScheduler()
        print("📋 Running with current configuration")

    # Run tasks immediately
    print("📋 Running all tasks manually...")
    scheduler.run_all_tasks()

    print("✅ Manual test completed!")


def show_test_menu():
    """Show test options menu"""
    ai_provider = os.getenv("AI_PROVIDER", "claude")
    print("\n🔧 Scheduler Test Menu")
    print("=" * 40)
    print(f"Current AI Provider: {ai_provider}")
    print("=" * 40)
    print("--- API Tests ---")
    print("1. Run full API test suite")
    print("2. Test scheduler status only")
    print("3. Test run-now endpoint")
    if DIRECT_MODE_AVAILABLE:
        print("\n--- Direct Tests (No API) ---")
        print("4. Test schedule (30s) WITHOUT AI")
        print("5. Test schedule (30s) WITH AI")
        print("6. Test manual run (current config)")
        print("7. Test manual run WITH AI")
        print("8. Test manual run WITHOUT AI")
        print("9. Test long schedule (15 min) WITHOUT AI")
        print("10. Test long schedule (15 min) WITH AI")
    print("\n0. Exit")
    print("=" * 40)


def run_api_test_suite(token):
    """Run the full API test suite"""
    try:
        # Check initial status
        status = test_scheduler_status(token)

        # Get current users
        users = test_get_scheduled_users(token)

        # Start scheduler if not running
        if not status.get("running"):
            test_start_scheduler(token)
            time.sleep(2)  # Wait for scheduler to start

        # Update existing user
        test_update_user(token, "namvanhoatagvn")

        # Run tasks immediately for testing
        test_run_now(token, "namvanhoatagvn")

        # Wait a bit for tasks to complete
        print("\nWaiting 30 seconds for tasks to complete...")
        time.sleep(30)

        # Check history
        test_get_history(token)

        # Get latest trending keywords
        test_get_trending_latest(token)

    except Exception as e:
        print(f"\nError during testing: {e}")


def main():
    print("=" * 60)
    print("Twitter Crawler Scheduler Test")
    print("=" * 60)

    while True:
        show_test_menu()
        choice = input("\nSelect test option: ").strip()

        if choice == "0":
            print("\n👋 Goodbye!")
            break

        # API tests require authentication
        if choice in ["1", "2", "3"]:
            token = get_auth_token()
            if not token:
                print("Failed to authenticate. Please check your credentials.")
                continue
            print("\nAuthentication successful!")

            if choice == "1":
                run_api_test_suite(token)
            elif choice == "2":
                test_scheduler_status(token)
            elif choice == "3":
                test_run_now(token, "namvanhoatagvn")

        # Direct tests
        elif choice == "4" and DIRECT_MODE_AVAILABLE:
            test_direct_quick_schedule(30, use_ai=False)
        elif choice == "5" and DIRECT_MODE_AVAILABLE:
            test_direct_quick_schedule(30, use_ai=True)
        elif choice == "6" and DIRECT_MODE_AVAILABLE:
            test_direct_manual_run()  # Use current config
        elif choice == "7" and DIRECT_MODE_AVAILABLE:
            test_direct_manual_run(use_ai=True)
        elif choice == "8" and DIRECT_MODE_AVAILABLE:
            test_direct_manual_run(use_ai=False)
        elif choice == "9" and DIRECT_MODE_AVAILABLE:
            test_direct_quick_schedule(15 * 60, use_ai=False)
        elif choice == "10" and DIRECT_MODE_AVAILABLE:
            test_direct_quick_schedule(15 * 60, use_ai=True)
        else:
            print("❌ Invalid option. Please try again.")

    print("\n" + "=" * 60)
    print("Test completed!")
    print("=" * 60)


if __name__ == "__main__":
    main()
