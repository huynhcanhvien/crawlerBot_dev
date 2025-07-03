#!/usr/bin/env python3
"""
Monitor script for scheduler - shows real-time status
"""

import requests
import json
import time
from datetime import datetime
import os

# Configuration
BASE_URL = "http://localhost:5000"
USERNAME = "admin"  # Change this to your actual username
PASSWORD = "admin123"  # Change this to your actual password
CHECK_INTERVAL = 60  # Check every 60 seconds


def clear_screen():
    """Clear the terminal screen"""
    os.system('cls' if os.name == 'nt' else 'clear')


def get_auth_token():
    """Login and get JWT token"""
    response = requests.post(f"{BASE_URL}/auth/login", json={
        "username": USERNAME,
        "password": PASSWORD
    })
    if response.status_code == 200:
        return response.json()["access_token"]
    return None


def get_scheduler_status(token):
    """Get current scheduler status"""
    try:
        response = requests.get(f"{BASE_URL}/scheduler/status",
                                headers={"Authorization": f"Bearer {token}"})
        if response.status_code == 200:
            return response.json()
    except:
        pass
    return None


def get_recent_history(token, limit=5):
    """Get recent task history"""
    try:
        response = requests.get(f"{BASE_URL}/scheduler/history",
                                params={"limit": limit},
                                headers={"Authorization": f"Bearer {token}"})
        if response.status_code == 200:
            return response.json()["history"]
    except:
        pass
    return []


def get_latest_trending(token):
    """Get latest trending keywords"""
    try:
        response = requests.get(f"{BASE_URL}/trending/latest",
                                headers={"Authorization": f"Bearer {token}"})
        if response.status_code == 200:
            return response.json()
    except:
        pass
    return None


def format_status(status):
    """Format status for display"""
    if not status:
        return "Unable to get scheduler status"

    lines = [
        f"Scheduler Status: {'✅ RUNNING' if status['running'] else '❌ STOPPED'}",
        f"Enabled: {status['enabled']}",
        f"Interval: Every {status.get('interval_seconds', 3600)} seconds ({status.get('interval_seconds', 3600)/60:.1f} minutes)",
        f"Monitored Users: {status['monitored_users']} total, {status['enabled_users']} enabled",
        f"Next Run: {status['next_run'] or 'N/A'}"
    ]
    return "\n".join(lines)


def format_history(history):
    """Format history for display"""
    if not history:
        return "No recent task history"

    lines = ["Recent Task History:"]
    for task in history:
        timestamp = task["timestamp"].replace("T", " ").split(".")[0]
        status_icon = "✅" if task["status"] == "completed" else "❌" if task["status"] == "failed" else "🔄"
        lines.append(f"  {status_icon} {timestamp} - @{task['username']} - {task['task_type']} - {task['status']}")
        if task["status"] == "completed" and task["task_type"] == "analysis":
            details = task.get("details", {})
            if "keywords_found" in details:
                lines.append(
                    f"     → Found {details['keywords_found']} keywords from {details.get('total_texts', 0)} texts")

    return "\n".join(lines)


def format_trending(trending):
    """Format trending keywords for display"""
    if not trending:
        return "No trending keywords found"

    lines = [f"Latest Trending Keywords (from {trending['timestamp'].split('T')[0]}):"]
    keywords = trending.get("trending_keywords", [])[:10]  # Show top 10

    for i, kw in enumerate(keywords, 1):
        lines.append(f"  {i:2d}. {kw['keyword']} (score: {kw['frequency']:.2f})")

    return "\n".join(lines)


def monitor():
    """Main monitoring loop"""
    print("Starting Scheduler Monitor...")
    print("Press Ctrl+C to stop\n")

    # Get auth token
    token = get_auth_token()
    if not token:
        print("Failed to authenticate. Exiting.")
        return

    print("Authentication successful!")
    print(f"Checking every {CHECK_INTERVAL} seconds...\n")

    try:
        while True:
            clear_screen()
            print("=" * 80)
            print(f"Twitter Crawler Scheduler Monitor - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            print("=" * 80)

            # Get and display status
            status = get_scheduler_status(token)
            print("\n" + format_status(status))

            # Get and display recent history
            history = get_recent_history(token, 10)
            print("\n" + format_history(history))

            # Get and display trending keywords
            trending = get_latest_trending(token)
            print("\n" + format_trending(trending))

            print("\n" + "=" * 80)
            print(f"Next check in {CHECK_INTERVAL} seconds... (Press Ctrl+C to stop)")

            time.sleep(CHECK_INTERVAL)

    except KeyboardInterrupt:
        print("\n\nMonitoring stopped.")


if __name__ == "__main__":
    monitor()
