#!/usr/bin/env python3
"""
Test script for different AI providers (Claude, OpenAI, Gemini)
"""

import os
from dotenv import load_dotenv
from app.keyword_analysis import analyze_trending_keywords

# Load environment variables
load_dotenv()


def test_ai_provider(provider_name):
    """Test a specific AI provider"""
    print(f"\n{'='*60}")
    print(f"Testing {provider_name.upper()} AI Provider")
    print(f"{'='*60}")
    
    # Sample tweets for testing
    sample_texts = [
        "Công nghệ blockchain và trí tuệ nhân tạo đang thay đổi ngành tài chính Việt Nam #fintech #AI",
        "Thị trường bất động sản Hà Nội tăng trưởng mạnh trong quý 3 #batdongsan #hanoi",
        "Machine learning applications in healthcare showing promising results #ML #healthtech",
        "Đầu tư vào startup công nghệ tại Việt Nam đạt kỷ lục mới #startup #investment",
        "Chính sách mới về chuyển đổi số cho doanh nghiệp vừa và nhỏ #digitaltransformation",
        "The future of AI is here with amazing breakthroughs in natural language processing",
        "Việt Nam đang trở thành trung tâm công nghệ của Đông Nam Á với nhiều unicorn mới",
        "Blockchain technology revolutionizing supply chain management globally",
        "Giáo dục trực tuyến phát triển mạnh mẽ sau đại dịch COVID-19 #edtech",
        "Sustainable technology solutions for climate change becoming mainstream"
    ]
    
    # Check if API key exists for this provider
    api_key_name = f"{provider_name.upper()}_API_KEY"
    api_key = os.getenv(api_key_name)
    
    if not api_key:
        print(f"⚠️  {api_key_name} not found in .env file")
        print(f"   Please add your {provider_name} API key to .env file:")
        print(f"   {api_key_name}=your-api-key-here")
        return
    
    print(f"✅ {api_key_name} found")
    
    try:
        # Test with AI enabled
        print(f"\n🤖 Running keyword analysis with {provider_name}...")
        
        results = analyze_trending_keywords(
            texts=sample_texts,
            top_n=10,
            use_ai=True,
            ai_provider=provider_name.lower(),
            api_key=api_key
        )
        
        print(f"\n📊 Results using {provider_name}:")
        print(f"Total texts analyzed: {results.get('total_analyzed_texts', 0)}")
        print(f"Method: {results.get('method', 'unknown')}")
        print(f"AI used: {results.get('ai_used', False)}")
        
        print("\n🔥 Top Keywords:")
        for i, kw_data in enumerate(results.get('keywords', []), 1):
            print(f"  {i:2d}. {kw_data['keyword']} (score: {kw_data['score']}, type: {kw_data.get('type', 'unknown')})")
        
        if 'language_distribution' in results:
            print(f"\n🌐 Language distribution: {results['language_distribution']}")
            
    except Exception as e:
        print(f"❌ Error testing {provider_name}: {str(e)}")


def test_env_based_provider():
    """Test using AI provider from environment variable"""
    print(f"\n{'='*60}")
    print("Testing AI Provider from Environment Variable")
    print(f"{'='*60}")
    
    current_provider = os.getenv("AI_PROVIDER", "claude")
    print(f"Current AI_PROVIDER in .env: {current_provider}")
    
    # Sample texts
    sample_texts = [
        "Artificial Intelligence is transforming the tech industry #AI #Tech",
        "Công nghệ AI đang phát triển mạnh mẽ tại Việt Nam #AI #Vietnam",
        "Machine learning models getting more sophisticated every day",
        "Trí tuệ nhân tạo và học máy là tương lai của công nghệ"
    ]
    
    try:
        # Test with default provider from env
        print(f"\n🤖 Running analysis with {current_provider} (from env)...")
        
        results = analyze_trending_keywords(
            texts=sample_texts,
            top_n=5,
            use_ai=True
            # ai_provider not specified - will use from env
        )
        
        print(f"\n📊 Results:")
        for i, kw_data in enumerate(results.get('keywords', []), 1):
            print(f"  {i}. {kw_data['keyword']} (score: {kw_data['score']})")
            
    except Exception as e:
        print(f"❌ Error: {str(e)}")


def main():
    """Main test function"""
    print("🚀 AI Provider Test Suite")
    print("=" * 60)
    
    # Show current configuration
    print("\n📋 Current Configuration:")
    print(f"  AI_PROVIDER (env): {os.getenv('AI_PROVIDER', 'not set')}")
    print(f"  CLAUDE_API_KEY: {'✅ Set' if os.getenv('CLAUDE_API_KEY') else '❌ Not set'}")
    print(f"  OPENAI_API_KEY: {'✅ Set' if os.getenv('OPENAI_API_KEY') else '❌ Not set'}")
    print(f"  GEMINI_API_KEY: {'✅ Set' if os.getenv('GEMINI_API_KEY') else '❌ Not set'}")
    
    while True:
        print("\n🔧 Test Options:")
        print("1. Test Claude AI")
        print("2. Test OpenAI")
        print("3. Test Gemini AI")
        print("4. Test using AI_PROVIDER from .env")
        print("5. Test without AI (frequency-based only)")
        print("0. Exit")
        
        choice = input("\nSelect option (0-5): ").strip()
        
        if choice == "0":
            print("\n👋 Goodbye!")
            break
        elif choice == "1":
            test_ai_provider("claude")
        elif choice == "2":
            test_ai_provider("openai")
        elif choice == "3":
            test_ai_provider("gemini")
        elif choice == "4":
            test_env_based_provider()
        elif choice == "5":
            print("\n📊 Testing without AI (frequency-based)...")
            results = analyze_trending_keywords(
                texts=[
                    "AI and machine learning are the future #AI #ML",
                    "Công nghệ blockchain đang phát triển #blockchain",
                    "Digital transformation is key #digital"
                ],
                top_n=5,
                use_ai=False
            )
            print("\nResults (no AI):")
            for i, kw in enumerate(results.get('keywords', []), 1):
                print(f"  {i}. {kw['keyword']} (score: {kw['score']})")
        else:
            print("❌ Invalid option")


if __name__ == "__main__":
    main()