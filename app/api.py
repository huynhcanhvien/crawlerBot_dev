from flasgger import Swagger
from flask import Flask, request, jsonify
from flask_jwt_extended import JWTManager, jwt_required
from app.auth import auth_bp
from app.tweet_service import run_service
from app.keyword_analysis import analyze_trending_keywords
from app.mongo_client import MongoDBClient
from app.scheduler import get_scheduler
from app.services.telegram_service import get_telegram_service
from .logger import setup_logger
from .swagger_utils import swag_from
from . import api_docs
import os
from dotenv import load_dotenv

# Setup logger
logger = setup_logger(__name__)

# Load environment variables
load_dotenv()

app = Flask(__name__)

# Swagger configuration
swagger_config = {
    "headers": [],
    "specs": [
        {
            "endpoint": 'apispec',
            "route": '/apispec.json',
            "rule_filter": lambda rule: True,
            "model_filter": lambda tag: True,
        }
    ],
    "static_url_path": "/flasgger_static",
    "swagger_ui": True,
    "specs_route": "/apidocs/"
}

swagger_template = {
    "swagger": "2.0",
    "info": {
        "title": "CrawlerX API",
        "description": "Twitter Crawler and Trending Keywords Analysis API",
        "version": "1.0.0"
    },
    "host": "localhost:5003",
    "basePath": "/",
    "schemes": ["http"],
    "securityDefinitions": {
        "Bearer": {
            "type": "apiKey",
            "name": "Authorization",
            "in": "header",
            "description": "JWT Authorization header using the Bearer scheme. Example: 'Bearer {token}'"
        }
    }
}

swagger = Swagger(app, config=swagger_config, template=swagger_template)

app.config["JWT_SECRET_KEY"] = os.getenv("JWT_SECRET_KEY", "super-secret")
app.config["JWT_ACCESS_TOKEN_EXPIRES"] = 900
app.config["JWT_REFRESH_TOKEN_EXPIRES"] = 86400
jwt = JWTManager(app)

app.register_blueprint(auth_bp)


@app.route("/health", methods=["GET"])
def health_check():
    """Health check endpoint
    ---
    tags:
      - System
    responses:
      200:
        description: Service is healthy
        schema:
          type: object
          properties:
            status:
              type: string
              example: "healthy"
            service:
              type: string
              example: "CrawlerX API"
            version:
              type: string
              example: "1.0.0"
            database:
              type: string
              example: "connected"
      503:
        description: Service is unhealthy
    """
    try:
        # Check MongoDB connection
        mongo = MongoDBClient()
        mongo.client.server_info()  # Will throw exception if not connected
        db_status = "connected"
    except Exception:
        db_status = "disconnected"
        
    health_status = {
        "status": "healthy" if db_status == "connected" else "unhealthy",
        "service": "CrawlerX API",
        "version": "1.0.0",
        "database": db_status
    }
    
    status_code = 200 if db_status == "connected" else 503
    return jsonify(health_status), status_code


@app.route("/crawl", methods=["POST"])
@jwt_required()
def crawl():
    """Manually trigger tweet crawling for a specific user
    ---
    tags:
      - Crawling
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
              description: Twitter username to crawl
              example: "elonmusk"
            depth:
              type: integer
              description: Crawl depth (how many levels of followings to crawl)
              default: 1
              example: 1
            max_following:
              type: integer
              description: Maximum number of followings to crawl per user
              default: 10
              example: 10
            max_tweets:
              type: integer
              description: Maximum number of tweets to collect per user
              default: 20
              example: 20
            include_root:
              type: boolean
              description: Whether to include the root user's tweets
              default: true
              example: true
    responses:
      200:
        description: Crawling completed successfully
        schema:
          type: object
          properties:
            status:
              type: string
              example: "success"
            message:
              type: string
              example: "Successfully crawled tweets for elonmusk"
            config:
              type: object
              properties:
                username:
                  type: string
                depth:
                  type: integer
                max_following:
                  type: integer
                max_tweets:
                  type: integer
                include_root:
                  type: boolean
      400:
        description: Bad request
      401:
        description: Unauthorized
      500:
        description: Internal server error
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "No JSON data provided"}), 400
        username = data.get("username")
        if not username:
            return jsonify({"error": "Username is required"}), 400
        depth = data.get("depth", 1)
        max_following = data.get("max_following", 10)
        max_tweets = data.get("max_tweets", 20)
        include_root = data.get("include_root", True)

        result = run_service(username, depth, max_following, max_tweets, include_root)
        return jsonify({
            "status": "success",
            "message": f"Successfully crawled tweets for {username}",
            "config": {
                "username": username,
                "depth": depth,
                "max_following": max_following,
                "max_tweets": max_tweets,
                "include_root": include_root
            }
        })
    except Exception as e:
        return jsonify({"error": f"Crawling failed: {str(e)}"}), 500


@app.route("/trending", methods=["GET"])
@jwt_required()
def trending():
    """Analyze and get trending keywords from tweets in database
    ---
    tags:
      - Analysis
    security:
      - Bearer: []
    parameters:
      - in: query
        name: count
        type: integer
        description: Number of trending keywords to return
        default: 10
        example: 10
      - in: query
        name: use_ai
        type: boolean
        description: Whether to use AI for keyword analysis
        default: false
        example: false
      - in: query
        name: ai_provider
        type: string
        description: AI provider to use (claude, openai, gemini)
        default: claude
        enum: [claude, openai, gemini]
        example: claude
      - in: query
        name: tweets_per_user
        type: integer
        description: Maximum tweets to analyze per user
        required: false
        example: 15
      - in: query
        name: save_to_db
        type: boolean
        description: Whether to save results to database
        default: true
        example: true
      - in: query
        name: root_user_id
        type: string
        description: Root user ID to filter tweets
        required: false
        example: "1234567890"
      - in: query
        name: use_percentage
        type: boolean
        description: Whether to use percentage-based tweet selection
        default: false
        example: false
      - in: query
        name: percent_tweets
        type: integer
        description: Percentage of recent tweets to analyze per user (0-100)
        default: 40
        example: 40
      - in: query
        name: time_filter_enabled
        type: boolean
        description: Whether to filter tweets by time
        default: false
        example: false
      - in: query
        name: days_recent
        type: integer
        description: Number of recent days to consider for analysis
        default: 30
        example: 30
    responses:
      200:
        description: Analysis completed successfully
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
            total_analyzed_texts:
              type: integer
              example: 500
            message:
              type: string
              example: "Successfully analyzed 500 tweets"
            method:
              type: string
              example: "hybrid"
            ai_used:
              type: boolean
              example: false
            root_user_id:
              type: string
              example: "1234567890"
            language_distribution:
              type: object
              example: {"en": 300, "vi": 200}
            topics:
              type: object
              description: Topic modeling results
      400:
        description: Bad request
      401:
        description: Unauthorized
      500:
        description: Internal server error
    """
    try:
        # Check and download VnCoreNLP if needed before analysis
        # logger.info("Checking VnCoreNLP availability for trending analysis...")
        # if not vncorenlp_service.check_and_download():
        #     logger.warning("VnCoreNLP download failed. Analysis will use fallback tokenizer.")

        # Get parameters
        count = int(request.args.get("count", 10))
        use_ai = request.args.get("use_ai", "false").lower() == "true"
        ai_provider = request.args.get("ai_provider", "claude")  # default to claude
        tweets_per_user = request.args.get("tweets_per_user", None)
        save_to_db = request.args.get("save_to_db", "true").lower() == "true"
        root_user_id = request.args.get("root_user_id", None)
        use_percentage = request.args.get("use_percentage", "false").lower() == "true"
        percent_tweets = int(request.args.get("percent_tweets", 40))
        time_filter_enabled = request.args.get("time_filter_enabled", "false").lower() == "true"
        days_recent = int(request.args.get("days_recent", 30))

        if count <= 0 or count > 100:
            return jsonify({"error": "Count must be between 1 and 100"}), 400

        if tweets_per_user:
            try:
                tweets_per_user = int(tweets_per_user)
                if tweets_per_user <= 0:
                    return jsonify({"error": "tweets_per_user must be positive"}), 400
            except ValueError:
                return jsonify({"error": "tweets_per_user must be a valid integer"}), 400
        
        # Validate percentage-based parameters
        if use_percentage:
            if percent_tweets < 0 or percent_tweets > 100:
                return jsonify({"error": "percent_tweets must be between 0 and 100"}), 400
        
        # Validate time filter parameters
        if time_filter_enabled:
            if days_recent <= 0:
                return jsonify({"error": "days_recent must be positive"}), 400

        # Analyze keywords with optional AI and tweets_per_user limit
        result = analyze_trending_keywords(
            texts=None,  # Will load from DB
            top_n=count,
            use_ai=use_ai,
            ai_provider=ai_provider if ai_provider else None,  # Will use env var if not specified
            tweets_per_user=tweets_per_user,
            save_to_db=save_to_db,
            root_user_id=root_user_id,
            use_percentage=use_percentage,
            percent_tweets=percent_tweets,
            time_filter_enabled=time_filter_enabled,
            days_recent=days_recent
        )

        # Format response
        response = {
            "trending_keywords": [
                {
                    "keyword": kw_data["keyword"],
                    "frequency": kw_data["score"],
                    "type": kw_data.get("type", "single")
                }
                for kw_data in result["keywords"]
            ],
            "total_analyzed_texts": result.get("total_analyzed_texts", 0),
            "message": result.get("message", f"Successfully analyzed {result.get('total_analyzed_texts', 0)} tweets"),
            "method": result.get("method", "hybrid"),
            "ai_used": result.get("ai_used", False),
            "root_user_id": root_user_id
        }

        if "language_distribution" in result:
            response["language_distribution"] = result["language_distribution"]

        # Add topic modeling results if available
        if "topics" in result:
            response["topics"] = result["topics"]

        return jsonify(response)

    except ValueError as e:
        return jsonify({"error": f"Invalid parameter: {str(e)}"}), 400
    except Exception as e:
        return jsonify({"error": f"Analysis failed: {str(e)}"}), 500


@app.route("/analyze/topics/history", methods=["GET"])
@jwt_required()
@swag_from(api_docs.TOPIC_HISTORY_DOC)
def get_topic_history():
    try:
        root_user_id = request.args.get("root_user_id")
        days = request.args.get("days", 7, type=int)

        if days < 1 or days > 30:
            return jsonify({"error": "days must be between 1 and 30"}), 400

        mongo = MongoDBClient()
        history = mongo.get_topic_history(root_user_id, days)

        # Format response
        formatted_history = []
        for doc in history:
            item = {
                "timestamp": doc["timestamp"].isoformat(),
                "topics_count": doc.get("topics", {}).get("topics_count", 0),
                "trending_topics": doc.get("topics", {}).get("trending_topics", [])[:5]
            }
            formatted_history.append(item)

        return jsonify({
            "history": formatted_history,
            "days": days,
            "root_user_id": root_user_id
        })

    except Exception as e:
        logger.error(f"Failed to get topic history: {e}")
        return jsonify({"error": f"Failed to get topic history: {str(e)}"}), 500


@app.route("/analyze/topics/trends", methods=["GET"])
@jwt_required()
@swag_from(api_docs.TOPIC_TRENDS_DOC)
def get_topic_trends():
    try:
        root_user_id = request.args.get("root_user_id")
        days = request.args.get("days", 7, type=int)
        top_n = request.args.get("top_n", 5, type=int)

        if days < 1 or days > 30:
            return jsonify({"error": "days must be between 1 and 30"}), 400

        if top_n < 1 or top_n > 20:
            return jsonify({"error": "top_n must be between 1 and 20"}), 400

        mongo = MongoDBClient()
        trends = mongo.get_trending_topics_over_time(root_user_id, days, top_n)

        return jsonify({
            "trends": trends,
            "days": days,
            "top_n": top_n,
            "root_user_id": root_user_id
        })

    except Exception as e:
        logger.error(f"Failed to get topic trends: {e}")
        return jsonify({"error": f"Failed to get topic trends: {str(e)}"}), 500


@app.route("/trending/latest", methods=["GET"])
@jwt_required()
@swag_from(api_docs.LATEST_TRENDING_DOC)
def latest_trending():
    try:
        root_user_id = request.args.get("root_user_id", None)

        mongo = MongoDBClient()
        latest = mongo.get_latest_trending_keywords(root_user_id)

        if not latest:
            return jsonify({
                "message": "No trending keywords found",
                "trending_keywords": []
            }), 404

        # Format response
        response = {
            "trending_keywords": [
                {
                    "keyword": kw_data["keyword"],
                    "frequency": kw_data["score"],
                    "type": kw_data.get("type", "single")
                }
                for kw_data in latest["keywords"]
            ],
            "timestamp": latest["timestamp"].isoformat(),
            "method": latest.get("method", "unknown"),
            "ai_used": latest.get("ai_used", False),
            "root_user_id": latest.get("root_user_id")
        }

        # Add topic modeling results if available
        if "topics" in latest:
            response["topics"] = latest["topics"]

        return jsonify(response)

    except Exception as e:
        return jsonify({"error": f"Failed to retrieve trending keywords: {str(e)}"}), 500


@app.route("/root-users", methods=["GET"])
@jwt_required()
@swag_from(api_docs.ROOT_USERS_DOC)
def get_root_users():
    try:
        mongo = MongoDBClient()
        root_users = mongo.get_all_root_users()

        return jsonify({
            "root_users": root_users,
            "count": len(root_users)
        })

    except Exception as e:
        return jsonify({"error": f"Failed to retrieve root users: {str(e)}"}), 500


@app.route("/scheduler/status", methods=["GET"])
@jwt_required()
@swag_from(api_docs.SCHEDULER_STATUS_DOC)
def scheduler_status():
    try:
        scheduler = get_scheduler()
        return jsonify(scheduler.get_status())
    except Exception as e:
        return jsonify({"error": f"Failed to get scheduler status: {str(e)}"}), 500


@app.route("/scheduler/start", methods=["POST"])
@jwt_required()
@swag_from(api_docs.SCHEDULER_START_DOC)
def start_scheduler():
    try:
        scheduler = get_scheduler()
        if scheduler.start():
            return jsonify({"message": "Scheduler started successfully", "status": scheduler.get_status()})
        else:
            return jsonify({"message": "Scheduler is already running or disabled", "status": scheduler.get_status()})
    except Exception as e:
        return jsonify({"error": f"Failed to start scheduler: {str(e)}"}), 500


@app.route("/scheduler/stop", methods=["POST"])
@jwt_required()
@swag_from(api_docs.SCHEDULER_STOP_DOC)
def stop_scheduler():
    try:
        scheduler = get_scheduler()
        scheduler.stop()
        return jsonify({"message": "Scheduler stopped successfully", "status": scheduler.get_status()})
    except Exception as e:
        return jsonify({"error": f"Failed to stop scheduler: {str(e)}"}), 500


@app.route("/scheduler/users", methods=["GET"])
@jwt_required()
@swag_from(api_docs.SCHEDULED_USERS_GET_DOC)
def get_scheduled_users():
    try:
        scheduler = get_scheduler()
        return jsonify({
            "users": scheduler.config["root_users"],
            "count": len(scheduler.config["root_users"])
        })
    except Exception as e:
        return jsonify({"error": f"Failed to get scheduled users: {str(e)}"}), 500


@app.route("/scheduler/users", methods=["POST"])
@jwt_required()
@swag_from(api_docs.SCHEDULED_USERS_POST_DOC)
def add_scheduled_user():
    try:
        data = request.get_json()
        username = data.get("username")
        if not username:
            return jsonify({"error": "Username is required"}), 400

        crawl_config = data.get("crawl_config")
        analysis_config = data.get("analysis_config")
        telegram_config = data.get("telegram_config")

        scheduler = get_scheduler()
        user = scheduler.add_root_user(username, crawl_config, analysis_config, telegram_config)

        return jsonify({
            "message": f"User @{username} added to scheduler",
            "user": user
        })
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        return jsonify({"error": f"Failed to add user: {str(e)}"}), 500


@app.route("/scheduler/users/<username>", methods=["PUT"])
@jwt_required()
def update_scheduled_user(username):
    """Update a scheduled user's configuration"""
    try:
        data = request.get_json()

        scheduler = get_scheduler()
        user = scheduler.update_root_user(
            username=username,
            enabled=data.get("enabled"),
            crawl_config=data.get("crawl_config"),
            analysis_config=data.get("analysis_config"),
            telegram_config=data.get("telegram_config")
        )

        return jsonify({
            "message": f"User @{username} updated",
            "user": user
        })
    except ValueError as e:
        return jsonify({"error": str(e)}), 404
    except Exception as e:
        return jsonify({"error": f"Failed to update user: {str(e)}"}), 500


@app.route("/scheduler/users/<username>", methods=["DELETE"])
@jwt_required()
def remove_scheduled_user(username):
    """Remove a user from the scheduler"""
    try:
        scheduler = get_scheduler()
        scheduler.remove_root_user(username=username)

        return jsonify({
            "message": f"User @{username} removed from scheduler"
        })
    except Exception as e:
        return jsonify({"error": f"Failed to remove user: {str(e)}"}), 500


@app.route("/scheduler/history", methods=["GET"])
@jwt_required()
def get_scheduler_history():
    """Get scheduler task execution history"""
    try:
        root_user_id = request.args.get("root_user_id")
        limit = int(request.args.get("limit", 50))

        scheduler = get_scheduler()
        history = scheduler.get_task_history(root_user_id, limit)

        # Convert datetime objects to ISO format
        for task in history:
            task["timestamp"] = task["timestamp"].isoformat()
            task.pop("_id", None)  # Remove MongoDB ID

        return jsonify({
            "history": history,
            "count": len(history)
        })
    except Exception as e:
        return jsonify({"error": f"Failed to get history: {str(e)}"}), 500


@app.route("/telegram/post", methods=["POST"])
@jwt_required()
def post_to_telegram():
    """
    Post latest trending keywords to Telegram channel
    ---
    tags:
      - Telegram
    parameters:
      - in: body
        name: body
        schema:
          type: object
          properties:
            root_user_id:
              type: string
              description: Root user ID to get trending keywords for
              required: false
            include_topics:
              type: boolean
              description: Include topics in the message (default false)
              required: false
              default: false
    responses:
      200:
        description: Successfully posted to Telegram
        schema:
          type: object
          properties:
            success:
              type: boolean
            message:
              type: string
            keywords_count:
              type: integer
      400:
        description: Bad request or Telegram not configured
      500:
        description: Server error
    """
    try:
        # Log request details for debugging
        logger.info(f"Telegram POST request - Content-Type: {request.content_type}")
        logger.info(f"Request data: {request.data}")
        
        # Get request data
        data = request.get_json(force=True, silent=True) or {}
        logger.info(f"Parsed JSON data: {data}")
        
        root_user_id = data.get("root_user_id", os.getenv("ROOT_USER_ID"))
        include_topics = data.get("include_topics", False)

        # Get Telegram service
        telegram_service = get_telegram_service()

        if not telegram_service or not telegram_service.bot:
            return jsonify({
                "success": False,
                "error": "Telegram service not configured. Please set TELEGRAM_BOT_TOKEN and TELEGRAM_CHANNEL_ID"
            }), 400

        # Get latest trending keywords
        mongo = MongoDBClient()
        latest = mongo.get_latest_trending_keywords(root_user_id)

        if not latest:
            return jsonify({
                "success": False,
                "error": "No trending keywords found"
            }), 404

        # Prepare data for Telegram
        trending_data = {
            "keywords": latest.get("keywords", []),
            "total_analyzed_texts": len(latest.get("keywords", [])),
            "method": latest.get("method", "unknown"),
            "ai_used": latest.get("ai_used", False),
            "timestamp": latest.get("timestamp"),
            "language_distribution": {}  # Could be calculated from keywords
        }

        # Add topics if requested and available
        if include_topics and "topics" in latest:
            trending_data["topics"] = latest["topics"]
            trending_data["include_topics"] = True

        # Send to Telegram
        success, error_msg = telegram_service.send_trending_keywords(trending_data)

        if success:
            return jsonify({
                "success": True,
                "message": "Successfully posted to Telegram",
                "keywords_count": len(latest.get("keywords", [])),
                "topics_included": include_topics and "topics" in latest
            })
        else:
            return jsonify({
                "success": False,
                "error": error_msg or "Failed to send message to Telegram"
            }), 500

    except Exception as e:
        logger.error(f"Failed to post to Telegram: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/telegram/test", methods=["POST"])
@jwt_required()
def test_telegram():
    """
    Test Telegram connection with a simple message
    ---
    tags:
      - Telegram
    parameters:
      - in: body
        name: body
        schema:
          type: object
          properties:
            message:
              type: string
              description: Test message to send
              default: "Hello from CrawlerX! 🚀"
    responses:
      200:
        description: Test message sent successfully
      400:
        description: Telegram not configured
      500:
        description: Failed to send test message
    """
    try:
        data = request.get_json() or {}
        test_message = data.get("message", "Hello from CrawlerX! 🚀")

        # Initialize Telegram service
        from .services.telegram_service import init_telegram_service, telegram_service
        init_telegram_service()

        if not telegram_service or not telegram_service.bot:
            return jsonify({
                "success": False,
                "error": "Telegram service not configured"
            }), 400

        # Send test message
        success, error_msg = telegram_service.send_message(f"*Test Message*\n\n{test_message}")

        if success:
            return jsonify({
                "success": True,
                "message": "Test message sent successfully"
            })
        else:
            return jsonify({
                "success": False,
                "error": error_msg or "Failed to send test message"
            }), 500

    except Exception as e:
        logger.error(f"Failed to send test message: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/scheduler/run-now", methods=["POST"])
@jwt_required()
def run_scheduler_now():
    """Run scheduler tasks immediately"""
    try:
        data = request.get_json()
        username = data.get("username")

        scheduler = get_scheduler()

        if username:
            # Run for specific user
            user_config = None
            for user in scheduler.config["root_users"]:
                if user["username"] == username:
                    user_config = user
                    break

            if not user_config:
                return jsonify({"error": f"User @{username} not found in scheduler"}), 404

            scheduler.run_task_for_user(user_config)
            return jsonify({"message": f"Task executed for @{username}"})
        else:
            # Run for all users
            scheduler.run_all_tasks()
            return jsonify({"message": "Tasks executed for all enabled users"})

    except Exception as e:
        return jsonify({"error": f"Failed to run tasks: {str(e)}"}), 500


@app.route("/health", methods=["GET"])
def health():
    """Health check endpoint - no authentication required"""
    return jsonify({"status": "healthy", "message": "Twitter Crawler API is running"})


def start_scheduler_async():
    """Start scheduler in background after a delay"""
    import time
    time.sleep(2)  # Wait for Flask to start
    try:
        scheduler = get_scheduler()
        scheduler.start()
        logger.info("✅ Scheduler auto-started")
    except Exception as e:
        logger.warning(f"⚠️ Failed to auto-start scheduler: {e}")


if __name__ == "__main__":
    # Start scheduler in background if configured
    if os.getenv("AUTO_START_SCHEDULER", "false").lower() == "true":
        import threading

        scheduler_thread = threading.Thread(target=start_scheduler_async, daemon=True)
        scheduler_thread.start()

    # Start Flask app
    logger.info(f"🚀 Starting API on http://0.0.0.0:5003")
    logger.info(f"📖 Swagger docs available at: http://localhost:5003/apidocs/")
    app.run(host="0.0.0.0", port=5003)
