# !/usr/bin/env python3
"""
Test script for the main service functions:
- run_service (tweet crawling and storage)
- analyze_trending_keywords (trending keywords analysis with optional AI)
"""
# Import the main functions we want to test
from app.tweet_service import run_service
from app.keyword_analysis import analyze_trending_keywords
from app.mongo_client import MongoDBClient

import os
import sys
import time
from dotenv import load_dotenv

# Add current directory to path
sys.path.append('test')

# Load environment variables
load_dotenv()


def check_prerequisites():
    """Check if all prerequisites are met"""
    print("🔍 Checking prerequisites...")

    issues = []

    # Check API key
    api_key = os.getenv("RAPIDAPI_KEY")
    if not api_key or api_key == "your_rapidapi_key_here":
        issues.append("❌ RAPIDAPI_KEY not set in .env file")
    else:
        print("✅ RapidAPI key found")
    
    # Check AI configuration
    ai_provider = os.getenv("AI_PROVIDER", "claude")
    print(f"🤖 AI Provider configured: {ai_provider}")
    
    # Check API keys for different providers
    claude_key = os.getenv("CLAUDE_API_KEY")
    openai_key = os.getenv("OPENAI_API_KEY")
    gemini_key = os.getenv("GEMINI_API_KEY")
    
    if claude_key:
        print("✅ Claude API key found")
    if openai_key:
        print("✅ OpenAI API key found")
    if gemini_key:
        print("✅ Gemini API key found")
    
    # Check if the configured provider has an API key
    if ai_provider == "claude" and not claude_key:
        print(f"⚠️  AI_PROVIDER is set to 'claude' but CLAUDE_API_KEY not found")
    elif ai_provider == "openai" and not openai_key:
        print(f"⚠️  AI_PROVIDER is set to 'openai' but OPENAI_API_KEY not found")
    elif ai_provider == "gemini" and not gemini_key:
        print(f"⚠️  AI_PROVIDER is set to 'gemini' but GEMINI_API_KEY not found")

    # Check MongoDB connection
    try:
        mongo = MongoDBClient()
        # Try a simple operation
        mongo.col.find_one()
        print("✅ MongoDB connection successful")
    except Exception as e:
        issues.append(f"❌ MongoDB connection failed: {e}")

    if issues:
        print("\n🚨 Issues found:")
        for issue in issues:
            print(f"  {issue}")
        return False

    print("✅ All prerequisites met!")
    return True


def test_run_service():
    """Test the run_service function with small parameters"""
    print("\n" + "=" * 60)
    print("🕷️ TESTING run_service FUNCTION")
    print("=" * 60)

    # Configuration for testing
    config = {
        "username": "namvanhoatagvn",
        #"username": "cz_binance",
        #"username": "0x_Malc",
        "depth": 1,  # Only go 1 level deep
        "per_user_limit": 100,  # Only get 100 followings
        "tweet_limit": 20,  # Only 20 tweets per user
        "include_root": False
    }

    print(f"📋 Test Configuration:")
    print(f"   - Username: @{config['username']}")
    print(f"   - Depth: {config['depth']}")
    print(f"   - Max followings: {config['per_user_limit']}")
    print(f"   - Tweets per user: {config['tweet_limit']}")
    print(f"   - Include root user: {config['include_root']}")

    # Count existing tweets before
    mongo = MongoDBClient()
    tweets_before = mongo.col.count_documents({})
    print(f"\n📊 Tweets in database before: {tweets_before}")

    print(f"\n🚀 Starting crawl...")
    start_time = time.time()

    try:
        # This is the main function your API calls
        run_service(
            username=config["username"],
            depth=config["depth"],
            per_user_limit=config["per_user_limit"],
            tweet_limit=config["tweet_limit"],
            include_root=config["include_root"]
        )

        end_time = time.time()
        duration = end_time - start_time

        # Count tweets after
        tweets_after = mongo.col.count_documents({})
        new_tweets = tweets_after - tweets_before

        print(f"\n✅ run_service completed successfully!")
        print(f"📊 Results:")
        print(f"   - Duration: {duration:.2f} seconds")
        print(f"   - Tweets before: {tweets_before}")
        print(f"   - Tweets after: {tweets_after}")
        print(f"   - New tweets added: {new_tweets}")

        # Show some sample tweets
        if new_tweets > 0:
            print(f"\n📝 Sample new tweets:")
            recent_tweets = list(mongo.col.find().sort("_id", -1).limit(3))
            for i, tweet in enumerate(recent_tweets, 1):
                username = tweet.get('username', 'unknown')
                text = tweet.get('text', 'No text')[:100] + '...'
                print(f"   {i}. @{username}: {text}")

        return True

    except Exception as e:
        print(f"\n❌ run_service failed: {e}")
        return False


def test_keyword_analysis_no_ai():
    """Test keyword analysis WITHOUT AI"""
    print("\n" + "=" * 60)
    print("📊 TESTING KEYWORD ANALYSIS WITHOUT AI")
    print("=" * 60)
    
    root_user_id = os.getenv("ROOT_USER_ID")
    mongo = MongoDBClient()
    
    # Get count of tweets for root user
    if root_user_id:
        tweet_count = mongo.col.count_documents({"root_user_id": root_user_id})
        print(f"📈 Found {tweet_count} tweets for root user {root_user_id}")
    else:
        tweet_count = mongo.col.count_documents({})
        print(f"📈 Found {tweet_count} total tweets in database")
    
    if tweet_count == 0:
        print("⚠️ No tweets in database. Run crawl test first.")
        return False
        
    print(f"\n🔍 Analyzing tweets WITHOUT AI...")
    print(f"⚠️  Note: Results will NOT be saved to database (save_to_db=False)")
    
    try:
        start_time = time.time()
        result = analyze_trending_keywords(
            texts=None,  # Load from DB
            top_n=20,  # Get more keywords for better analysis
            use_ai=False,
            root_user_id=root_user_id,
            tweets_per_user=10,  # Get 5 recent tweets per user
            save_to_db=False,  # DO NOT SAVE TO DATABASE
            use_percentage=True,  # Use percentage to get tweets
            percent_tweets=50,
            days_recent=30  # Just get recent tweets in 30 days from now
        )
        duration = time.time() - start_time
        
        print(f"\n✅ Analysis completed in {duration:.2f} seconds")
        print(f"📊 Method: {result.get('method', 'unknown')}")
        print(f"🌐 Language distribution: {result.get('language_distribution', {})}")
        
        if result.get('keywords'):
            print(f"\n🔥 Top {len(result['keywords'])} Keywords:")
            for i, kw in enumerate(result['keywords'], 1):
                print(f"   {i:2d}. {kw['keyword']:<30} (score: {kw['score']:>8.2f})")
        
        # Show topics if available
        if result.get('topics'):
            topics = result['topics']
            print(f"\n🎯 Topic Modeling Results:")
            print(f"   - Total topics found: {topics.get('topics_count', 0)}")
            
            if topics.get('trending_topics'):
                print(f"\n📊 Top Trending Topics:")
                for i, topic in enumerate(topics['trending_topics'][:5], 1):
                    print(f"\n   Topic {i} (ID: {topic.get('topic_id', -1)}, Frequency: {topic.get('frequency', 0)}):")
                    print(f"   Top words: {', '.join(topic.get('top_words', []))}")
                    if topic.get('keywords'):
                        print(f"   Keywords:")
                        for kw in topic['keywords'][:3]:
                            print(f"     - {kw['word']} (score: {kw['score']:.2f})")
                            
    except Exception as e:
        print(f"❌ Analysis failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    return True


def test_keyword_analysis_with_ai():
    """Test keyword analysis WITH AI"""
    print("\n" + "=" * 60)
    print("📊 TESTING KEYWORD ANALYSIS WITH AI")
    print("=" * 60)
    
    # Check AI configuration
    ai_provider = os.getenv("AI_PROVIDER", "claude")
    api_key = os.getenv(f"{ai_provider.upper()}_API_KEY")
    root_user_id = os.getenv("ROOT_USER_ID")
    
    if not api_key:
        print(f"❌ {ai_provider.upper()}_API_KEY not found in .env")
        print(f"   Please add your {ai_provider} API key to use AI features")
        return False
    
    mongo = MongoDBClient()
    
    # Get count of tweets for root user
    if root_user_id:
        tweet_count = mongo.col.count_documents({"root_user_id": root_user_id})
        print(f"📈 Found {tweet_count} tweets for root user {root_user_id}")
    else:
        tweet_count = mongo.col.count_documents({})
        print(f"📈 Found {tweet_count} total tweets in database")
    
    if tweet_count == 0:
        print("⚠️ No tweets in database. Run crawl test first.")
        return False
        
    print(f"\n🤖 Analyzing tweets with {ai_provider.upper()} AI...")
    
    try:
        start_time = time.time()
        result = analyze_trending_keywords(
            texts=None,  # Load from DB
            top_n=20,
            use_ai=True,
            root_user_id=root_user_id,
            tweets_per_user=30  # Use fewer tweets for AI to save tokens
            # ai_provider will be taken from env
        )
        duration = time.time() - start_time
        
        print(f"\n✅ AI Analysis completed in {duration:.2f} seconds")
        print(f"🤖 AI Provider: {ai_provider}")
        print(f"📊 Method: {result.get('method', 'unknown')}")
        print(f"🤖 AI Used: {result.get('ai_used', False)}")
        
        if result.get('keywords'):
            print(f"\n🔥 Top {len(result['keywords'])} AI-Enhanced Keywords:")
            for i, kw in enumerate(result['keywords'], 1):
                print(f"   {i:2d}. {kw['keyword']:<30} (score: {kw['score']:>8.2f})")
    except Exception as e:
        print(f"❌ AI Analysis failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    return True


def test_run_keyword_analysis():
    """Test the analyze_trending_keywords function"""
    print("\n" + "=" * 60)
    print("📊 TESTING analyze_trending_keywords FUNCTION")
    print("=" * 60)

    # Check if we have tweets to analyze
    mongo = MongoDBClient()
    root_user_id = os.getenv("ROOT_USER_ID")
    
    # Get tweet counts
    if root_user_id:
        tweet_count = mongo.col.count_documents({"root_user_id": root_user_id})
        total_tweets = mongo.col.count_documents({})
        print(f"📋 Database status:")
        print(f"   - Total tweets in DB: {total_tweets}")
        print(f"   - Tweets for root user {root_user_id}: {tweet_count}")
    else:
        tweet_count = mongo.col.count_documents({})
        print(f"📋 Database status:")
        print(f"   - Total tweets available: {tweet_count}")

    if tweet_count == 0:
        print("⚠️ No tweets in database. Keyword analysis may not work well.")
        print("💡 Run the crawl test first to collect some tweets.")
        return False
    
    # Check if AI is available
    ai_provider = os.getenv("AI_PROVIDER", "claude")
    ai_keys = {
        "claude": os.getenv("CLAUDE_API_KEY"),
        "openai": os.getenv("OPENAI_API_KEY"),
        "gemini": os.getenv("GEMINI_API_KEY")
    }
    use_ai = ai_keys.get(ai_provider) is not None

    print(f"\n🔍 Starting keyword analysis...")
    
    # Test 1: Without AI
    print("\n--- Test 1: Analysis WITHOUT AI ---")
    try:
        start_time = time.time()
        result = analyze_trending_keywords(
            texts=None,  # Load from DB
            top_n=20,
            use_ai=False,
            root_user_id=root_user_id,
            tweets_per_user=10  # Get 50 recent tweets per user
        )
        end_time = time.time()

        print(f"⏱️ Analysis took {end_time - start_time:.2f} seconds")
        print(f"📊 Method: {result.get('method', 'unknown')}")
        
        if 'language_distribution' in result:
            print(f"🌐 Language distribution: {result['language_distribution']}")

        if result and 'keywords' in result:
            print(f"\n✅ Found {len(result['keywords'])} keywords:")

            for i, item in enumerate(result['keywords'], 1):
                keyword = item['keyword']
                score = item['score']
                kw_type = item.get('type', 'unknown')
                print(f"   {i:2d}. {keyword:<30} (score: {score:>8.2f}, type: {kw_type})")

        else:
            print("⚠️ No keywords returned from analysis")

    except Exception as e:
        print(f"\n❌ Basic analysis failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # Test 2: With AI (if available)
    if use_ai:
        print(f"\n--- Test 2: Analysis WITH AI ({ai_provider.upper()}) ---")
        try:
            start_time = time.time()
            result_ai = analyze_trending_keywords(
                texts=None,  # Load from DB
                top_n=20,
                use_ai=True,
                root_user_id=root_user_id,
                tweets_per_user=10  # Use fewer tweets for AI to save tokens
                # ai_provider will be taken from env
            )
            end_time = time.time()

            print(f"⏱️ AI Analysis took {end_time - start_time:.2f} seconds")
            print(f"🤖 AI Used: {result_ai.get('ai_used', False)}")
            print(f"📊 Method: {result_ai.get('method', 'unknown')}")

            if result_ai and 'keywords' in result_ai:
                print(f"\n✅ AI found {len(result_ai['keywords'])} keywords:")

                for i, item in enumerate(result_ai['keywords'], 1):
                    keyword = item['keyword']
                    score = item['score']
                    kw_type = item.get('type', 'unknown')
                    print(f"   {i:2d}. {keyword:<30} (score: {score:>8.2f}, type: {kw_type})")

                # Compare with non-AI results
                ai_keywords = {kw['keyword'] for kw in result_ai['keywords']}
                non_ai_keywords = {kw['keyword'] for kw in result['keywords']}
                unique_to_ai = ai_keywords - non_ai_keywords
                
                if unique_to_ai:
                    print(f"\n🎯 Keywords unique to AI analysis:")
                    for kw in list(unique_to_ai)[:5]:
                        print(f"   - {kw}")

        except Exception as e:
            print(f"\n⚠️ AI analysis failed (this is normal if API key not set): {e}")
    else:
        print(f"\n⚠️ Skipping AI test - {ai_provider.upper()}_API_KEY not set")

    print(f"\n📈 Analysis summary:")
    print(f"   - Root user ID: {root_user_id or 'Not specified'}")
    print(f"   - Total texts analyzed: {result.get('total_analyzed_texts', 0)}")
    print(f"   - Analysis methods tested: {'Both (with/without AI)' if use_ai else 'Basic only'}")
    
    return True


def show_database_stats():
    """Show current database statistics"""
    print("\n" + "=" * 60)
    print("📊 DATABASE STATISTICS")
    print("=" * 60)

    try:
        mongo = MongoDBClient()

        # Total tweets
        total_tweets = mongo.col.count_documents({})
        print(f"📈 Total tweets: {total_tweets}")

        if total_tweets > 0:
            # Unique users
            unique_users = len(mongo.col.distinct("username"))
            print(f"👥 Unique users: {unique_users}")

            # Recent tweets
            recent_tweets = list(mongo.col.find().sort("_id", -1).limit(5))
            print(f"\n📝 Most recent tweets:")
            for i, tweet in enumerate(recent_tweets, 1):
                username = tweet.get('username', 'unknown')
                text = tweet.get('text', 'No text')[:50] + '...'
                created_at = tweet.get('created_at', 'unknown time')
                print(f"   {i}. @{username} ({created_at}): {text}")

            # User distribution
            print(f"\n👥 Tweets per user:")
            pipeline = [
                {"$group": {"_id": "$username", "count": {"$sum": 1}}},
                {"$sort": {"count": -1}},
                {"$limit": 10}
            ]
            user_stats = list(mongo.col.aggregate(pipeline))
            for user_stat in user_stats:
                username = user_stat['_id']
                count = user_stat['count']
                print(f"   - @{username}: {count} tweets")

    except Exception as e:
        print(f"❌ Could not get database stats: {e}")


def main():
    """Main test function"""
    print("🐦 TWITTER CRAWLER - MAIN FUNCTIONS TEST")
    print("=" * 60)

    # Check prerequisites
    if not check_prerequisites():
        print(f"\n💡 Please fix the issues above before running tests.")
        return

    # Show initial database state
    show_database_stats()

    # Ask user what to test
    print(f"\n🎯 What would you like to test?")
    print(f"   1. Test run_service (crawl tweets)")
    print(f"   2. Test keyword analysis WITHOUT AI")
    print(f"   3. Test keyword analysis WITH AI (using {os.getenv('AI_PROVIDER', 'claude')})")
    print(f"   4. Test both crawl and analysis")
    print(f"   5. Just show database stats")

    choice = input("\nEnter choice (1-5): ").strip()

    if choice == "1":
        test_run_service()
        show_database_stats()

    elif choice == "2":
        # Test WITHOUT AI
        test_keyword_analysis_no_ai()

    elif choice == "3":
        # Test WITH AI
        test_keyword_analysis_with_ai()

    elif choice == "4":
        print(f"\n🚀 Running both crawl and analysis tests...")

        # Test crawling first
        crawl_success = test_run_service()

        if crawl_success:
            # Wait a moment, then test analysis
            print(f"\n⏱️ Waiting 2 seconds before keyword analysis...")
            time.sleep(2)
            test_run_keyword_analysis()
        else:
            print(f"\n⚠️ Skipping keyword analysis due to crawl failure")

        show_database_stats()

    elif choice == "5":
        show_database_stats()

    else:
        print(f"Invalid choice. Running both tests...")
        test_run_service()
        test_run_keyword_analysis()
        show_database_stats()

    print(f"\n🎉 Test completed!")
    print(f"💡 If these functions work, your API endpoints should work too!")


if __name__ == "__main__":
    main()
