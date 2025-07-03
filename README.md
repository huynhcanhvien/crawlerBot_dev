# CrawlerX - Twitter Trending Keywords Analysis Service

## Purpose

CrawlerX is an automated Twitter analysis service that crawls tweets from specified users and their networks to identify trending keywords and topics. The service helps monitor social media trends, track discussions, and analyze content patterns in real-time with support for both Vietnamese and English languages.

## Features

- **Automated Twitter Crawling**: Periodically crawls tweets from configured users and their following networks
- **Advanced Multi-language Support**: 
  - Unified NLP service for both Vietnamese and English text processing
  - spaCy for advanced English NLP with named entity recognition
  - pyvi for Vietnamese tokenization and POS tagging
  - Automatic language detection with langdetect
  - Comprehensive stopwords (2000+ Vietnamese, NLTK English)
  - Automatic compound word detection
- **Smart Tweet Selection**:
  - **Percentage-based Selection**: Analyze a percentage of each user's recent tweets (e.g., 40% of their latest posts)
  - **Time-based Filtering**: Only analyze tweets from the last N days (e.g., last 30 days)
  - **Fixed Count Mode**: Traditional mode with fixed number of tweets per user
  - **Balanced Analysis**: Ensures fair representation from both active and less active users
- **Topic Modeling with BERTopic**: Groups keywords into semantic topics for better trend analysis
- **Hybrid Keyword Extraction**: Combines frequency-based, KeyBERT, and unified NLP methods
- **Scheduled Automation**: Runs automatically at configurable intervals (default: 1 hour)
- **REST API**: Provides endpoints to access trending keywords, topics, and manage the crawler
- **AI-Powered Analysis**: Optional integration with OpenAI, Claude, or Gemini for enhanced keyword extraction
- **JWT Authentication**: Secure API access with token-based authentication
- **Swagger Documentation**: Interactive API documentation at `/apidocs`

## Deployment & Installation

### Prerequisites
- Python 3.9 or higher
- MongoDB 6.0 or higher
- Docker & Docker Compose (for containerized deployment)
- RapidAPI key for Twitter API access

### Option 1: Deploy with Docker Compose (Recommended)

1. Clone the repository:
   ```bash
   git clone <repository-url>
   cd CrawlerX
   ```

2. Create `.env` file from the template:
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

3. Build and run services:
   ```bash
   # For newer Docker versions (Docker Desktop 20.10+)
   docker compose up --build -d
   
   # For older Docker versions
   docker-compose up --build -d
   ```

The API will be available at `http://localhost:5003`

#### CPU-Optimized Deployment for Linux/Ubuntu (No GPU)

If deploying on a Linux/Ubuntu server without GPU, use the optimized build to reduce image size from 7.2GB to ~2.5GB and build time from 1 hour to ~15 minutes:

```bash
# Use the CPU-optimized docker compose
DOCKER_BUILDKIT=1 docker-compose -f docker-compose.optimized.yml up -d --build
```

This optimized build:
- Uses CPU-only PyTorch (no CUDA/GPU libraries)
- Multi-stage build to minimize image size
- Optimized for 2-core CPUs
- Reduces download size by ~4.5GB

### Option 2: Local Development Setup

1. Install Python dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Install spaCy English model:
   ```bash
   python -m spacy download en_core_web_sm
   ```

3. Download NLTK data:
   ```bash
   python -c "import nltk; nltk.download('punkt'); nltk.download('punkt_tab'); nltk.download('averaged_perceptron_tagger'); nltk.download('wordnet'); nltk.download('stopwords')"
   ```

4. Install and start MongoDB:
   ```bash
   # macOS
   brew install mongodb-community
   brew services start mongodb-community
   
   # Ubuntu/Debian
   sudo apt-get install mongodb
   sudo systemctl start mongodb
   ```

5. Configure environment variables:
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

6. Run the service:
   ```bash
   python -m app.api
   ```

## Configuration

### Environment Variables (.env)

```env
# Twitter API Access
RAPIDAPI_KEY=your-rapidapi-key-here

# Authentication
JWT_SECRET_KEY=your-secret-key-here
AUTH_USERNAME=admin
AUTH_PASSWORD=admin

# MongoDB Connection
MONGO_HOST=localhost          # Use 'mongo' for Docker
MONGO_PORT=27017
MONGO_USER=admin
MONGO_PASS=admin
MONGO_DB_NAME=twitter_crawler_db
MONGO_COLLECTION_NAME=tweets

# Crawler Settings
DELAY_BETWEEN_REQUESTS=1.2    # Delay between API calls in seconds
ROOT_USER_ID=123456789        # Default Twitter user ID for testing
ROOT_USER_NAME=username       # Default Twitter username for testing

# Scheduler
AUTO_START_SCHEDULER=true     # Start scheduler automatically on startup

# Logging
LOG_LEVEL=INFO               # Options: DEBUG, INFO, WARNING, ERROR
LOG_FILE=logs/app.log

# AI Integration (Optional)
AI_PROVIDER=gemini           # Options: openai, claude, gemini
# OPENAI_API_KEY=your-key
# CLAUDE_API_KEY=your-key
# GEMINI_API_KEY=your-key

# Telegram Integration (Optional)
# TELEGRAM_BOT_TOKEN=your-bot-token  # Get from @BotFather
# TELEGRAM_CHANNEL_ID=-1001234567890  # Channel ID or @channelname
```

### Scheduler Configuration (scheduler_config.json)

```json
{
  "scheduler": {
    "interval_seconds": 3600,
    "enabled": true
  },
  "root_users": [
    {
      "username": "twitter_username",
      "user_id": "twitter_user_id",
      "enabled": true,
      "crawl_config": {
        "depth": 1,
        "max_following": 100,
        "max_tweets": 20,
        "include_root": false
      },
      "analysis_config": {
        "top_n": 20,
        "tweets_per_user": 10,
        "use_percentage": false,
        "percent_tweets_per_user": 40,
        "time_filter": {
          "enabled": false,
          "days_recent": 30
        },
        "use_ai": false
      },
      "telegram_config": {
        "enabled": false,
        "post_after_analysis": true
      }
    }
  ]
}
```

**Configuration Fields:**
- `interval_seconds`: Run interval in seconds (3600 = 1 hour)
- `depth`: How deep to crawl following networks
- `max_following`: Maximum number of following accounts to crawl
- `max_tweets`: Maximum tweets per user
- `include_root`: Whether to include root user's own tweets
- `top_n`: Number of top keywords to extract
- `tweets_per_user`: Fixed number of tweets per user for analysis
- `use_percentage`: Enable percentage-based tweet selection (overrides tweets_per_user)
- `percent_tweets_per_user`: Percentage of recent tweets to analyze per user (0-100, default: 40)
- `time_filter.enabled`: Enable time-based filtering
- `time_filter.days_recent`: Number of recent days to consider (default: 30)
- `use_ai`: Enable AI-powered analysis
- `enabled`: Enable Telegram posting
- `post_after_analysis`: Auto-post after analysis

### Smart Tweet Selection

CrawlerX offers three modes for selecting tweets to analyze:

#### 1. Fixed Count Mode (Default)
The traditional approach where you specify a fixed number of tweets per user:
```json
{
  "tweets_per_user": 10,
  "use_percentage": false
}
```
This gets exactly 10 recent tweets from each user, regardless of their posting frequency.

#### 2. Percentage-Based Mode
Analyzes a percentage of each user's recent tweets, ensuring balanced representation:
```json
{
  "use_percentage": true,
  "percent_tweets_per_user": 40
}
```
- User A with 100 recent tweets → analyzes 40 tweets
- User B with 20 recent tweets → analyzes 8 tweets
- Ensures active users don't dominate the analysis

#### 3. Time-Based Filtering
Limits analysis to recent content only:
```json
{
  "time_filter": {
    "enabled": true,
    "days_recent": 30
  }
}
```
Only analyzes tweets from the last 30 days, keeping the analysis current and relevant.

#### Combined Mode Example
You can combine percentage-based selection with time filtering:
```json
{
  "use_percentage": true,
  "percent_tweets_per_user": 60,
  "time_filter": {
    "enabled": true,
    "days_recent": 7
  }
}
```
This analyzes 60% of each user's tweets from the last 7 days.

## API Documentation

### Base URL
```
http://localhost:5003
```

### Swagger UI
Interactive API documentation available at: `http://localhost:5003/apidocs`

### Authentication

All API endpoints require JWT authentication (except `/health`).

#### Get Access Token
**Request:**
```bash
POST /auth/login
Content-Type: application/json

{
  "username": "admin",
  "password": "admin"
}
```

**Response:**
```json
{
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "refresh_token": "eyJ0eXAiOiJKV1QiLCJhbG..."
}
```

Use the access token in subsequent requests:
```
Authorization: Bearer <access_token>
```

### API Endpoints

#### Get Latest Trending Keywords
Retrieves the most recent trending keywords analysis from the database.

**Request:**
```bash
GET /trending/latest
Authorization: Bearer <token>

# Optional: Get for specific user
GET /trending/latest?root_user_id=123456789
```

**Response:**
```json
{
  "trending_keywords": [
    {
      "keyword": "artificial_intelligence",
      "frequency": 342.5,
      "type": "compound"
    },
    {
      "keyword": "#TechNews",
      "frequency": 215.0,
      "type": "single"
    },
    {
      "keyword": "công_nghệ",
      "frequency": 189.3,
      "type": "compound"
    }
  ],
  "timestamp": "2024-12-06T10:30:00",
  "method": "hybrid",
  "ai_used": false,
  "root_user_id": "123456789",
  "topics": {
    "trending_topics": ["Technology", "Business", "Sports"],
    "topics_count": 10,
    "topics_info": [
      {
        "topic": 0,
        "count": 125,
        "name": "Technology_AI_Blockchain",
        "representative_docs": ["AI is transforming...", "Blockchain technology..."]
      }
    ]
  }
}
```

#### Generate New Trending Analysis
Triggers a new analysis of tweets in the database.

**Request:**
```bash
GET /trending?count=15&use_ai=false&root_user_id=123456789
Authorization: Bearer <token>

# Example with percentage-based selection and time filter
GET /trending?count=20&use_percentage=true&percent_tweets=60&time_filter_enabled=true&days_recent=7
Authorization: Bearer <token>
```

**Parameters:**
- `count` (int): Number of keywords to return (1-100, default: 10)
- `use_ai` (bool): Enable AI analysis (default: false)
- `ai_provider` (string): AI provider - openai/claude/gemini
- `tweets_per_user` (int): Fixed number of tweets analyzed per user
- `use_percentage` (bool): Enable percentage-based tweet selection (default: false)
- `percent_tweets` (int): Percentage of recent tweets per user (0-100, default: 40)
- `time_filter_enabled` (bool): Enable time-based filtering (default: false)
- `days_recent` (int): Number of recent days to consider (default: 30)
- `root_user_id` (string): Filter tweets by root user

**Response:**
```json
{
  "trending_keywords": [
    {
      "keyword": "blockchain",
      "frequency": 256.8,
      "type": "single"
    },
    {
      "keyword": "thị_trường_chứng_khoán",
      "frequency": 198.5,
      "type": "compound"
    }
  ],
  "total_analyzed_texts": 1250,
  "method": "hybrid",
  "ai_used": false,
  "language_distribution": {
    "vietnamese": 680,
    "english": 470,
    "mixed": 100
  },
  "topics": {
    "trending_topics": ["Technology", "Finance", "AI"],
    "topics_count": 5,
    "topics_info": []
  },
  "root_user_id": "123456789"
}
```

#### Crawl Tweets Manually
Manually trigger tweet crawling for a specific user.

**Request:**
```bash
POST /crawl
Authorization: Bearer <token>
Content-Type: application/json

{
  "username": "elonmusk",
  "depth": 1,
  "max_following": 50,
  "max_tweets": 20,
  "include_root": true
}
```

**Response:**
```json
{
  "status": "success",
  "message": "Successfully crawled tweets for elonmusk",
  "config": {
    "username": "elonmusk",
    "depth": 1,
    "max_following": 50,
    "max_tweets": 20,
    "include_root": true
  }
}
```

#### Scheduler Management

**Get Status:**
```bash
GET /scheduler/status
Authorization: Bearer <token>
```

**Start Scheduler:**
```bash
POST /scheduler/start
Authorization: Bearer <token>
```

**Stop Scheduler:**
```bash
POST /scheduler/stop
Authorization: Bearer <token>
```

**Get Scheduled Users:**
```bash
GET /scheduler/users
Authorization: Bearer <token>
```

**Add Scheduled User:**
```bash
POST /scheduler/users
Authorization: Bearer <token>
Content-Type: application/json

{
  "username": "tech_influencer",
  "crawl_config": {
    "depth": 1,
    "max_following": 30,
    "max_tweets": 20,
    "include_root": true
  },
  "analysis_config": {
    "top_n": 15,
    "tweets_per_user": 15,
    "use_percentage": false,
    "percent_tweets_per_user": 40,
    "time_filter": {
      "enabled": false,
      "days_recent": 30
    },
    "use_ai": false
  }
}
```

#### Telegram Integration

**Post to Telegram Channel:**
```bash
POST /telegram/post
Authorization: Bearer <token>
Content-Type: application/json

{
  "root_user_id": "optional_user_id",
  "include_topics": false
}
```

**Parameters:**
- `root_user_id`: Uses default if not specified
- `include_topics`: Include topics in message (default: false)

**Test Telegram Connection:**
```bash
POST /telegram/test
Authorization: Bearer <token>
Content-Type: application/json

{
  "message": "Test message from CrawlerX!"
}
```

#### Other Endpoints

- **GET /root-users** - List all available root users
- **GET /analyze/topics/history** - Get historical topic data
- **GET /analyze/topics/trends** - Get topic trends over time
- **GET /health** - Health check (no auth required)

## Running the Service

### Development Mode
```bash
# Start MongoDB (if not using Docker)
mongod

# Run the API service
python -m app.api
```

### Production Mode
```bash
# Start all services with Docker Compose
docker compose up -d

# View logs
docker compose logs -f app

# Stop services
docker compose down
```

### Verify Service is Running

1. Check health endpoint:
   ```bash
   curl http://localhost:5003/health
   ```

2. Access Swagger UI:
   ```
   http://localhost:5003/apidocs
   ```

3. Get authentication token and test API:
   ```bash
   # Get token
   TOKEN=$(curl -s -X POST http://localhost:5003/auth/login \
     -H "Content-Type: application/json" \
     -d '{"username": "admin", "password": "admin"}' \
     | jq -r .access_token)
   
   # Get trending keywords
   curl -H "Authorization: Bearer $TOKEN" \
     http://localhost:5003/trending/latest
   ```

## Telegram Integration Setup

### Step 1: Create a Telegram Bot
1. Open Telegram and search for @BotFather
2. Send `/newbot` and follow the prompts
3. Copy the bot token (looks like: `1234567890:ABCdefGHIjklMNOpqrsTUVwxyz`)

### Step 2: Create or Get Channel ID
**For Public Channel:**
- Use the channel username (e.g., `@yourchannel`)

**For Private Channel:**
1. Add your bot as an admin to the channel
2. Send a message to the channel
3. Visit: `https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getUpdates`
4. Find the channel ID (negative number like `-1001234567890`)

### Step 3: Configure Environment
Add to your `.env` file:
```env
TELEGRAM_BOT_TOKEN=your-bot-token-here
TELEGRAM_CHANNEL_ID=@yourchannel or -1001234567890
```

### Step 4: Enable in Scheduler
Update `scheduler_config.json` for automatic posting:
```json
{
  "telegram_config": {
  "enabled": true,
  "post_after_analysis": true,
  "include_topics": false
  }
}
```

**Note:** Set `include_topics` to `true` to include topics in the Telegram message.

## Monitoring & Logs

- Application logs: `./logs/app.log`
- Docker logs: `docker compose logs -f app`
- MongoDB logs: `docker compose logs -f mongo`

## NLP Features & Configuration

### Unified NLP Service
The service uses a unified NLP approach for both languages:
- **English**: spaCy with en_core_web_sm model for advanced NLP
- **Vietnamese**: pyvi for tokenization and POS tagging
- **Language Detection**: Automatic detection using langdetect library
- **Fallback Support**: NLTK as fallback for English if spaCy unavailable

### Key Features
- **Automatic Language Detection**: Processes mixed language content seamlessly
- **POS Tagging**: Extracts meaningful words based on grammatical roles
- **Named Entity Recognition**: Identifies people, organizations, locations (English)
- **Compound Word Preservation**: Maintains Vietnamese compound words with underscores
- **TF-IDF Scoring**: Combines frequency and importance for better keyword ranking

### Stopwords Management
- **Comprehensive Lists**: 2000+ Vietnamese stopwords, full NLTK English corpus
- **Social Media Specific**: Filters common social media terms (RT, DM, LOL, etc.)
- **Custom Filtering**: Additional noise reduction for cleaner results

### Topic Modeling
- **BERTopic Integration**: Groups keywords into semantic topics
- **Multilingual Support**: Uses paraphrase-multilingual-MiniLM-L12-v2 model
- **Topic Evolution**: Tracks how topics change over time
- **Hierarchical Clustering**: Identifies main topics and subtopics

## Database Migrations

CrawlerX includes a Flyway-like migration system that automatically runs on startup. Migrations are versioned and tracked in the database.

### How it works
1. Migration files are stored in `app/db_migrations/` with naming pattern `V001__description.py`
2. On startup, the system checks for pending migrations and runs them in order
3. Migration history is tracked in the `schema_version` collection

### Managing Migrations

```bash
# Check migration status
python manage_migrations.py status

# List pending migrations
python manage_migrations.py pending

# Create a new migration
python manage_migrations.py create "add user preferences collection"
```

### Creating a Migration

1. Use the CLI tool:
   ```bash
   python manage_migrations.py create "your migration description"
   ```

2. Edit the generated file in `app/db_migrations/V00X__your_migration_description.py`:
   ```python
   def up(db):
       """Apply the migration"""
       # Your migration logic here
       collection = db["new_collection"]
       collection.create_index([("field", 1)])
   ```

### Migration Best Practices
- Always test migrations on a development database first
- Keep migrations small and focused
- Migrations run automatically on service startup
- Failed migrations are logged but won't stop the service (configurable)

## Troubleshooting

1. **Service won't start**: Check MongoDB connection in `.env`
2. **Authentication errors**: Verify JWT_SECRET_KEY is set
3. **No trending keywords**: Ensure scheduler is running and has collected tweets
4. **Scheduler not working**: Check `AUTO_START_SCHEDULER=true` in `.env`
5. **NLTK errors**: Run the NLTK download commands in installation steps
6. **spaCy model missing**: Run `python -m spacy download en_core_web_sm`
7. **Topic modeling errors**: Check if BERTopic dependencies are installed correctly

## Architecture Overview

The service is built with a modular architecture:
- **API Layer**: Flask-based REST API with JWT authentication
- **NLP Service**: Unified service handling both English and Vietnamese
- **Scheduler**: Automated task runner for periodic crawling
- **MongoDB**: Document store for tweets and analysis results
- **Docker**: Containerized deployment for easy scaling

## Performance Considerations

- **Rate Limiting**: Configurable delays between API calls
- **Batch Processing**: Analyzes tweets in batches for efficiency
- **Caching**: Results stored in MongoDB for quick retrieval
- **Language-specific Processing**: Optimized pipelines for each language