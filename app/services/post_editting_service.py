import os
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import SystemMessage, HumanMessage
from typing import Optional
import time

# Prompts for various post-editing tasks
SYSTEM_PROMPT = (
    "You're an AI assistant helping build a system that automatically enhances and reformats tweets for crypto content creators to be suitable for Telegram channels.\n"
    "You can use HTML format or MarkdownV2 format. Convert the tweet of the voice of human to informative voice as AI\n"
    "\nYour task is to transform raw tweets into high-quality Telegram-ready content based on the following requirements:\n"
    "---\n"
    "### 🎯 Acceptance Criteria:\n"
    "- Automatically add context and background for crypto-related events.\n"
    "- Fact-check and verify key claims using multiple sources. E\n"
    "    Example:\n    - [Source 1](https://source1.com)\n    - [Source 2](https://source2.com)\n    - [Source 3](https://source3.com)\n"
    "- Make links preview-friendly for Telegram (e.g., full URLs or enriched previews).\n"
    "- Fix typos, grammar issues, and formatting problems.\n"
    "- Convert Twitter mentions (@username) into appropriate Telegram format. With the mentions of @username, you convert to appropriate name and remove '@'\n"
    '    Example: [@elonmusk](https://twitter.com/elonmusk) with MarkdownV2 or <a href="https://twitter.com/elonmusk">@elonmusk</a> with HTML\n'
    "- Add emojis that align with the culture of Telegram crypto communities. Prior to use icons of crypto, you can combine multiple emojis if needed:\n"
    "    Example: 🪙, 🚀, 📈, 💰, 💸, 👉, 📌, 💎, 🟡, 📈💰📊, 📊📈, 📊, ⚡, 💲, 🚨, ✓, 👨🏻‍💻, ➤, 🔥, 🌐, 💳.\n"
    "- Summarize and restructure long threads for easier mobile reading. The max token is 500.\n"
    "- Include appropriate call-to-action buttons or links (if applicable).\n"
    "    Example:\n    - [Read more](https://source1.com)\n    - [Read more](https://source2.com)\n    - [Read more](https://source3.com)\n"
    "- Format crypto-specific data (like prices, % changes, market cap) clearly. You can use the following format:\n"
    "    Example:\n    - $BTC is currently trading at $100,000.\n    - $BTC is up 10% in the last 24 hours.\n    - $BTC has a market cap of $1 trillion.\n"
    "- Add proper disclaimers and attribution for source information.\n"
    "Return the processed tweet content ready for Telegram as output. Ensure it is clean, concise, fact-checked, and correctly formatted.\n"
    "Only return the final message for Telegram. No explanation."
)

CHECK_FACT_SOURCE_SYSTEM_PROMPT = (
    "You are a helpful assistant that checks the fact source in the tweet."
)

FIX_GRAMMAR_SYSTEM_PROMPT = (
    "You are a helpful assistant that fixes grammar issues in the tweet.\n"
    "Don't return the added message from you, just return the content you have fixed"
)

CONVERT_TWEETER_MENTIONS_SYSTEM_PROMPT = (
    "You are a helpful assistant that converts the tweeter mentions to telegram mentions.\n"
    "Don't return the added message from you\n"
    "Return the content you have fixed and the links you have added\n"
    "Examples:\n    In tweets: @elonmusk\n"
    'Convert to: [@elonmusk](https://twitter.com/elonmusk) with MarkdownV2 or <a href="https://twitter.com/elonmusk">@elonmusk</a> with HTML'
)

ADD_CONTEXT_AND_BACKGROUND_CRYPTO_SYSTEM_PROMPT = (
    "You are a helpful assistant specialized in cryptocurrency.\n"
    "Your task is to expand short tweets related to crypto by adding clear and concise context, background, or implications so that general readers (non-experts) can better understand the meaning and significance of the tweet.\n"
    "Keep the tone neutral, informative, and avoid speculation unless explicitly stated in the tweet.\n"
    "Focus on clarifying abbreviations, explaining jargon, and providing a brief background if a person, token, or event is mentioned."
)

ADD_EMOJI_SYSTEM_PROMPT = (
    "You are an assistant that enhances short crypto-related social media messages for posting on Telegram.\n"
    "Your task is to insert relevant emojis into the original message to improve engagement and readability, following Telegram and crypto culture norms.\n"
    "💡 Guidelines:\n"
    "- Keep the original text **exactly as it is**. Do not rewrite or rephrase it.\n"
    "- Only insert emojis that are **contextually relevant** to the message (crypto, trading, emotions).\n"
    "- Place emojis in the **right location**: near keywords or at the beginning/end of sentences.\n"
    "- Use emojis **moderately** – no more than 3–6 per message. Avoid clutter.\n"
    "- Match the sentiment: 🚀 for hype, 📉 for bad news, 🟢🔴 for buy/sell, 🐂🐻 for bull/bear, etc.\n"
    "- Maintain a **natural, authentic tone** that fits Telegram groups.\n"
    "🧪 Examples:\n"
    "Input:\nBitcoin is pumping hard. Don't miss the train!\n"
    "Output:\nBitcoin 🚀 is pumping hard. Don't miss the train! 🚂\n"
    "Input:\nMarket is down. Everyone is selling.\n"
    "Output:\nMarket 📉 is down. Everyone is selling 🔴.\n"
    "Input:\nElon tweeted about DOGE again.\n"
    "Output:\nElon 👨‍🚀 tweeted about DOGE 🐶 again.\n"
    "Return only the enhanced message with emojis, no explanations."
)

SPECIAL_FORMAT_CRYPTO_SYSTEM_PROMPT = (
    "You are an assistant that formats crypto-related numbers in a message to be engaging and readable for Telegram users.\n"
    "Your task is to enhance the formatting of prices, percentage changes, and market-related numbers. Add relevant emojis, abbreviate large numbers, and highlight important information, following crypto culture norms.\n"
    "🔧 Formatting rules:\n"
    "- Add 💰 or token symbol (₿, Ξ, etc.) near prices\n"
    "- Highlight positive % with 📈 or 🟢, negative % with 📉 or 🔴\n"
    "- Use up to 2 decimal places for prices or % (e.g. +2.54%)\n"
    "- Use compact formatting for large numbers (e.g. 2.3M, 1.5B)\n"
    "- Use emoji like 🐂 (bullish), 🐻 (bearish), 🚀 (pump), 🧊 (freeze), 🐋 (whale) if context suggests it\n"
    '- Add space between numbers and symbols (e.g. "$30,251.20", not "$30,251.20USD")\n'
    "🎯 Output must be short, clear, and Telegram-friendly.\n"
    "---\n"
    "🧪 Examples:\n"
    "Input:\nBitcoin price is now 30251.2032 USD and it increased by 2.3421 percent in 24h.\n"
    "Output:\nBitcoin 💰 $30,251.20 📈 +2.34% (24h)\n"
    "---\n"
    "Input:\nEthereum dropped by -3.874% and market cap is 23241509823.\n"
    "Output:\nEthereum 🔴 -3.87% 📉 | Market Cap: 💰 $23.24B\n"
    "---\n"
    "Input:\nSOL is trading at 153.9 and gained 12.51 percent.\n"
    "Output:\nSOL 💰 $153.90 🚀 +12.51%\n"
    "---\n"
    "Return only the formatted message. Do not explain anything."
)

SUMMARY_SYSTEM_PROMPT = (
    "You are a Telegram assistant that restructures and summarizes crypto-related messages (tweets or news) for display on mobile Telegram channels.\n"
    "Your job is to shorten and reformat the message to:\n"
    "- Keep the core meaning and sentiment\n"
    "- Display clearly on small mobile screens\n"
    "- Use short, impactful sentence structure\n"
    "- Emphasize relevant keywords (token names, events, prices)\n"
    "- Optionally insert 1–3 appropriate emojis if relevant (🚀, 📉, 💰, etc.)\n"
    "- Avoid unnecessary phrases or repetition\n"
    "- Do not add opinions or change the meaning\n"
    "- Never rewrite in a clickbait style\n"
    "🧠 Formatting rules:\n"
    "- One or two short paragraphs (2–4 lines total)\n"
    "- Keep key data points (price, % change, announcement, etc.)\n"
    "- Start strong – important info first\n"
    "- End with a clear call-to-action or emotional punctuation if appropriate (! / ❗)\n"
    "---\n"
    "🧪 Examples:\n"
    "Input:\nBreaking: BlackRock's Bitcoin ETF just received approval. This could be a historic moment for institutional adoption. BTC already reacting with a +3% jump.\n"
    "Output:\n🚨 BlackRock's Bitcoin ETF just got approved.  \nBTC is pumping 📈 +3% – big moment for crypto institutions!\n"
    "---\n"
    "Input:\nElon Musk tweeted again about DOGE. Could this be the start of another meme rally?\n"
    "Output:\nElon 👨‍🚀 tweeted about DOGE 🐶 again.  \nMeme rally incoming?\n"
    "---\n"
    "Input:\nSolana is back above $150 with strong trading volume after weeks of consolidation.\n"
    "Output:\nSOL 💰 back over $150 🔥  \nVolume rising after long consolidation.\n"
    "---\n"
    "Only return the final message for Telegram. No explanation."
)


class PostEditingService:
    def __init__(
        self,
        api_key: Optional[str] = os.getenv("GEMINI_API_KEY"),
        model: str = "gemini-2.0-flash-001",
        temperature: float = 0.5,
    ):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        self.model = model
        self.temperature = temperature
        self.llm = ChatGoogleGenerativeAI(
            model=self.model, temperature=self.temperature, api_key=self.api_key
        )

    def process_tweet(self, tweet: str) -> str:
        result = self.llm.invoke(
            [
                SystemMessage(content=SYSTEM_PROMPT),
                HumanMessage(content=tweet),
            ]
        )
        return result.content if hasattr(result, "content") else str(result)

    def fix_grammar(self, content: str) -> str:
        result = self.llm.invoke(
            [
                SystemMessage(content=FIX_GRAMMAR_SYSTEM_PROMPT),
                HumanMessage(content=content),
            ]
        )
        return result.content if hasattr(result, "content") else str(result)

    def convert_tweeter_mentions(self, content: str) -> str:
        result = self.llm.invoke(
            [
                SystemMessage(content=CONVERT_TWEETER_MENTIONS_SYSTEM_PROMPT),
                HumanMessage(content=content),
            ]
        )
        return result.content if hasattr(result, "content") else str(result)

    def add_context_and_background_crypto(self, content: str) -> str:
        result = self.llm.invoke(
            [
                SystemMessage(content=ADD_CONTEXT_AND_BACKGROUND_CRYPTO_SYSTEM_PROMPT),
                HumanMessage(content=content),
            ]
        )
        return result.content if hasattr(result, "content") else str(result)

    def add_emoji(self, content: str) -> str:
        result = self.llm.invoke(
            [
                SystemMessage(content=ADD_EMOJI_SYSTEM_PROMPT),
                HumanMessage(content=content),
            ]
        )
        return result.content if hasattr(result, "content") else str(result)

    def format_crypto_data(self, content: str) -> str:
        result = self.llm.invoke(
            [
                SystemMessage(content=SPECIAL_FORMAT_CRYPTO_SYSTEM_PROMPT),
                HumanMessage(content=content),
            ]
        )
        return result.content if hasattr(result, "content") else str(result)

    def summary_and_restructure_content(self, content: str) -> str:
        result = self.llm.invoke(
            [
                SystemMessage(content=SUMMARY_SYSTEM_PROMPT),
                HumanMessage(content=content),
            ]
        )
        return result.content if hasattr(result, "content") else str(result)


if __name__ == "__main__":
    # Example usage for testing
    service = PostEditingService()
    sample_tweet = (
        "Chia sẻ chút quan điểm cá nhân về $BTC cho ae cùng tham khảo:\n"
        "Link: https://x.com/search?q=namvanhoatagvn&src=typed_query\n"
        "Mình vẫn nghiêng về xu hướng tăng trong trung hạn, nhưng để cẩn trọng thì mình nghĩ kịch bản 'bearish' khả dĩ nhất hiện tại là:\n"
        "Động lực tăng của BTC đang chậm lại khá rõ, giá đang đi trong range. Khả năng cao đợt mua lớn tiếp theo sẽ chỉ diễn ra khi BTC chạm vùng giá 'value', tức là đáy của range.\n"
        "Mùa hè này có vẻ cũng sẽ giống năm ngoái: giá đi ngang, không có biến động mạnh. Nên chuyện BTC retest vùng $97k–$103k rồi mới bật lại là điều hoàn toàn có thể.\n"
        "Với những ai đang dùng đòn bẩy cao thì nên chú ý đoạn này. Còn về tổng thể thì mình không nghĩ nó ảnh hưởng tới xu hướng lớn: BTC vẫn có thể lập ATH mới trong 2025, và cá nhân mình kỳ vọng BTC sẽ lên vùng $130k–$150k trong vài tháng tới.\n"
        "Nguồn: namvanhoatagvn"
    )
    start = time.time()
    result = service.process_tweet(sample_tweet)
    end = time.time()
    print("\n=== Telegram-ready Output ===\n")
    print(result)
    print(f"\nProcessing time: {end - start:.2f} seconds")
