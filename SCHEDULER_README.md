# Twitter Crawler Scheduler

## Overview

The scheduler feature allows you to automatically crawl tweets and analyze trending keywords at regular intervals. It supports multiple root users with individual configurations.

## Features

- **Automated Crawling**: Periodically crawl tweets from configured users and their networks
- **Keyword Analysis**: Automatically analyze trending keywords after each crawl
- **Multi-User Support**: Monitor multiple Twitter accounts with different settings
- **Task History**: Track all scheduled task executions with status and results
- **RESTful API**: Full control through API endpoints
- **Configurable Intervals**: Set custom crawl intervals (default: hourly)

## Configuration

### Configuration File: `scheduler_config.json`

```json
{
  "scheduler": {
    "interval_hours": 1,
    "enabled": true
  },
  "root_users": [
    {
      "username": "elonmusk",
      "user_id": null,
      "enabled": true,
      "crawl_config": {
        "depth": 2,
        "max_following": 50,
        "max_tweets": 30,
        "include_root": true
      },
      "analysis_config": {
        "top_n": 20,
        "tweets_per_user": 20,
        "use_ai": false,
        "ai_provider": "claude"
      }
    }
  ],
  "default_config": {
    "crawl": {
      "depth": 1,
      "max_following": 30,
      "max_tweets": 20,
      "include_root": true
    },
    "analysis": {
      "top_n": 15,
      "tweets_per_user": 15,
      "use_ai": false,
      "ai_provider": "claude"
    }
  }
}
```

### Environment Variables

Add to your `.env` file:

```bash
# Auto-start scheduler when API starts
AUTO_START_SCHEDULER=true
```

## API Endpoints

All endpoints require JWT authentication.

### Scheduler Status

```bash
GET /scheduler/status
```

Response:
```json
{
  "running": true,
  "enabled": true,
  "interval_hours": 1,
  "monitored_users": 1,
  "enabled_users": 1,
  "next_run": "2024-01-15 15:00:00"
}
```

### Start Scheduler

```bash
POST /scheduler/start
```

### Stop Scheduler

```bash
POST /scheduler/stop
```

### Get Scheduled Users

```bash
GET /scheduler/users
```

### Add User to Scheduler

```bash
POST /scheduler/users
Content-Type: application/json

{
  "username": "NASA",
  "crawl_config": {
    "depth": 1,
    "max_following": 20,
    "max_tweets": 25,
    "include_root": true
  },
  "analysis_config": {
    "top_n": 15,
    "tweets_per_user": 10,
    "use_ai": false,
    "ai_provider": "claude"
  }
}
```

### Update User Configuration

```bash
PUT /scheduler/users/{username}
Content-Type: application/json

{
  "enabled": true,
  "crawl_config": {
    "max_following": 30
  }
}
```

### Remove User from Scheduler

```bash
DELETE /scheduler/users/{username}
```

### Get Task History

```bash
GET /scheduler/history?limit=50&root_user_id={user_id}
```

### Run Tasks Immediately

```bash
POST /scheduler/run-now
Content-Type: application/json

{
  "username": "elonmusk"  // Optional - run for specific user
}
```

## Testing the Scheduler

### 1. Test Script

Run the provided test script to verify all scheduler endpoints:

```bash
python test_scheduler.py
```

### 2. Monitor Script

Use the monitor script to watch scheduler status in real-time:

```bash
python monitor_scheduler.py
```

### 3. Manual Testing with cURL

```bash
# Login
TOKEN=$(curl -X POST http://localhost:5000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin123"}' \
  | jq -r '.access_token')

# Check status
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:5000/scheduler/status | jq

# Start scheduler
curl -X POST -H "Authorization: Bearer $TOKEN" \
  http://localhost:5000/scheduler/start | jq

# Run immediately
curl -X POST -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"username":"elonmusk"}' \
  http://localhost:5000/scheduler/run-now | jq
```

## How It Works

1. **Initialization**: The scheduler loads configuration from `scheduler_config.json`
2. **Task Execution**: For each enabled user:
   - Crawl tweets based on crawl_config
   - Store tweets with root_user_id for tracking
   - Analyze trending keywords based on analysis_config
   - Save trending keywords to database with timestamp
3. **History Tracking**: All task executions are logged with:
   - Timestamp
   - Task type (crawl/analysis)
   - Status (started/completed/failed)
   - Execution details (duration, tweets found, etc.)

## Database Collections

### scheduler_tasks
Tracks all scheduled task executions:
- `timestamp`: When the task was executed
- `root_user_id`: The user being monitored
- `username`: Twitter username
- `task_type`: "crawl" or "analysis"
- `status`: "started", "completed", or "failed"
- `details`: Execution details (duration, error messages, etc.)

### trending_keywords
Stores trending keywords over time:
- `timestamp`: When keywords were analyzed
- `root_user_id`: Associated root user
- `keywords`: Array of keyword objects with scores
- `method`: Analysis method used
- `ai_used`: Whether AI was used for analysis

## Best Practices

1. **Rate Limiting**: The scheduler respects Twitter API rate limits with delays between requests
2. **Error Handling**: Failed tasks are logged but don't stop the scheduler
3. **Resource Usage**: Consider server resources when setting crawl depths and limits
4. **Monitoring**: Use the monitor script to track scheduler health
5. **Configuration**: Start with conservative settings and adjust based on needs

## Troubleshooting

### Scheduler won't start
- Check if scheduler is enabled in config
- Verify all dependencies are installed
- Check MongoDB connection

### Tasks failing
- Check API keys in .env file
- Verify Twitter usernames are valid
- Check rate limit settings
- Review error messages in task history

### No trending keywords
- Ensure tweets are being crawled successfully
- Check if there are enough recent tweets
- Verify keyword analysis configuration