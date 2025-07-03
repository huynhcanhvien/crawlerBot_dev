"""
Swagger documentation strings for API endpoints
"""

TOPIC_HISTORY_DOC = """Get historical topic data for trend analysis
---
tags:
  - Analysis
security:
  - Bearer: []
parameters:
  - in: query
    name: root_user_id
    type: string
    description: Root user ID to filter history
    required: false
    example: "1234567890"
  - in: query
    name: days
    type: integer
    description: Number of days of history to retrieve
    default: 7
    minimum: 1
    maximum: 30
    example: 7
responses:
  200:
    description: Historical data retrieved successfully
    schema:
      type: object
      properties:
        history:
          type: array
          items:
            type: object
            properties:
              timestamp:
                type: string
                example: "2024-01-01T00:00:00"
              topics_count:
                type: integer
                example: 10
              trending_topics:
                type: array
                items:
                  type: string
                example: ["AI", "Technology", "Climate"]
        days:
          type: integer
          example: 7
        root_user_id:
          type: string
          example: "1234567890"
  400:
    description: Bad request
  401:
    description: Unauthorized
  500:
    description: Internal server error
"""

TOPIC_TRENDS_DOC = """Get topic trends over time
---
tags:
  - Analysis
security:
  - Bearer: []
parameters:
  - in: query
    name: root_user_id
    type: string
    description: Root user ID to filter trends
    required: false
    example: "1234567890"
  - in: query
    name: days
    type: integer
    description: Number of days to analyze
    default: 7
    minimum: 1
    maximum: 30
    example: 7
  - in: query
    name: top_n
    type: integer
    description: Number of top topics to track
    default: 5
    minimum: 1
    maximum: 20
    example: 5
responses:
  200:
    description: Topic trends retrieved successfully
    schema:
      type: object
      properties:
        trends:
          type: object
          example: {"AI": [10, 15, 20], "Climate": [5, 8, 12]}
        days:
          type: integer
          example: 7
        top_n:
          type: integer
          example: 5
        root_user_id:
          type: string
          example: "1234567890"
  400:
    description: Bad request
  401:
    description: Unauthorized
  500:
    description: Internal server error
"""

LATEST_TRENDING_DOC = """Get the most recent trending keywords from database
---
tags:
  - Analysis
security:
  - Bearer: []
parameters:
  - in: query
    name: root_user_id
    type: string
    description: Root user ID to filter results
    required: false
    example: "1234567890"
responses:
  200:
    description: Latest trending keywords retrieved successfully
    schema:
      type: object
      properties:
        trending_keywords:
          type: array
          items:
            type: object
            properties:
              keyword:
                type: string
                example: "AI"
              frequency:
                type: number
                example: 0.85
              type:
                type: string
                example: "single"
        timestamp:
          type: string
          example: "2024-01-01T00:00:00"
        method:
          type: string
          example: "hybrid"
        ai_used:
          type: boolean
          example: false
        root_user_id:
          type: string
          example: "1234567890"
        topics:
          type: object
          description: Topic modeling results
          properties:
            trending_topics:
              type: array
              items:
                type: string
              example: ["Technology", "Business", "Sports"]
            topics_count:
              type: integer
              example: 10
            topics_info:
              type: array
              description: Detailed topic information
              items:
                type: object
                properties:
                  topic:
                    type: integer
                  count:
                    type: integer
                  name:
                    type: string
                  representative_docs:
                    type: array
                    items:
                      type: string
  404:
    description: No trending keywords found
  401:
    description: Unauthorized
  500:
    description: Internal server error
"""

ROOT_USERS_DOC = """Get list of all available root users
---
tags:
  - Users
security:
  - Bearer: []
responses:
  200:
    description: Root users retrieved successfully
    schema:
      type: object
      properties:
        root_users:
          type: array
          items:
            type: object
            properties:
              user_id:
                type: string
                example: "1234567890"
              username:
                type: string
                example: "elonmusk"
        count:
          type: integer
          example: 5
  401:
    description: Unauthorized
  500:
    description: Internal server error
"""

SCHEDULER_STATUS_DOC = """Get scheduler status
---
tags:
  - Scheduler
security:
  - Bearer: []
responses:
  200:
    description: Scheduler status retrieved successfully
    schema:
      type: object
      properties:
        running:
          type: boolean
          example: true
        enabled:
          type: boolean
          example: true
        interval_seconds:
          type: integer
          example: 3600
        monitored_users:
          type: integer
          example: 5
        enabled_users:
          type: integer
          example: 4
        next_run:
          type: string
          example: "2024-01-01 12:00:00"
  401:
    description: Unauthorized
  500:
    description: Internal server error
"""

SCHEDULER_START_DOC = """Start the scheduler
---
tags:
  - Scheduler
security:
  - Bearer: []
responses:
  200:
    description: Scheduler started successfully
    schema:
      type: object
      properties:
        message:
          type: string
          example: "Scheduler started successfully"
        status:
          type: object
  401:
    description: Unauthorized
  500:
    description: Internal server error
"""

SCHEDULER_STOP_DOC = """Stop the scheduler
---
tags:
  - Scheduler
security:
  - Bearer: []
responses:
  200:
    description: Scheduler stopped successfully
    schema:
      type: object
      properties:
        message:
          type: string
          example: "Scheduler stopped successfully"
        status:
          type: object
  401:
    description: Unauthorized
  500:
    description: Internal server error
"""

SCHEDULED_USERS_GET_DOC = """Get list of scheduled users
---
tags:
  - Scheduler
security:
  - Bearer: []
responses:
  200:
    description: Scheduled users retrieved successfully
    schema:
      type: object
      properties:
        users:
          type: array
          items:
            type: object
            properties:
              username:
                type: string
                example: "elonmusk"
              user_id:
                type: string
                example: "1234567890"
              enabled:
                type: boolean
                example: true
              crawl_config:
                type: object
                properties:
                  depth:
                    type: integer
                  max_following:
                    type: integer
                  max_tweets:
                    type: integer
                  include_root:
                    type: boolean
              analysis_config:
                type: object
                properties:
                  top_n:
                    type: integer
                  tweets_per_user:
                    type: integer
                  use_ai:
                    type: boolean
                  ai_provider:
                    type: string
              telegram_config:
                type: object
                properties:
                  enabled:
                    type: boolean
                  post_after_analysis:
                    type: boolean
        count:
          type: integer
          example: 5
  401:
    description: Unauthorized
  500:
    description: Internal server error
"""

SCHEDULED_USERS_POST_DOC = """Add a user to the scheduler
---
tags:
  - Scheduler
security:
  - Bearer: []
parameters:
  - in: body
    name: body
    required: true
    schema:
      type: object
      required:
        - username
      properties:
        username:
          type: string
          description: Twitter username to add
          example: "elonmusk"
        crawl_config:
          type: object
          description: Crawl configuration (optional, uses defaults if not provided)
          properties:
            depth:
              type: integer
              example: 1
            max_following:
              type: integer
              example: 30
            max_tweets:
              type: integer
              example: 20
            include_root:
              type: boolean
              example: true
        analysis_config:
          type: object
          description: Analysis configuration (optional, uses defaults if not provided)
          properties:
            top_n:
              type: integer
              example: 15
            tweets_per_user:
              type: integer
              example: 15
            use_ai:
              type: boolean
              example: false
            ai_provider:
              type: string
              example: "claude"
        telegram_config:
          type: object
          description: Telegram configuration (optional, uses defaults if not provided)
          properties:
            enabled:
              type: boolean
              description: Whether to post to Telegram
              example: false
            post_after_analysis:
              type: boolean
              description: Automatically post after analysis completes
              example: true
responses:
  200:
    description: User added successfully
    schema:
      type: object
      properties:
        message:
          type: string
          example: "User added successfully"
        user:
          type: object
  400:
    description: Bad request
  401:
    description: Unauthorized
  500:
    description: Internal server error
"""