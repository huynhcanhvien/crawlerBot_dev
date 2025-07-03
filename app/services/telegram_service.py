import os
import logging
from typing import Dict, List, Optional, Tuple
from datetime import datetime
import asyncio
import nest_asyncio
import time

# Allow nested event loops (useful for Jupyter/Flask environments)
nest_asyncio.apply()

logger = logging.getLogger(__name__)

try:
    from telegram import Bot
    from telegram.error import TelegramError
    from telegram.constants import ParseMode

    TELEGRAM_AVAILABLE = True
except ImportError:
    TELEGRAM_AVAILABLE = False
    logger.warning("python-telegram-bot not installed. Install with: pip install python-telegram-bot")


class TelegramService:
    """Service for posting trending keywords to Telegram channels"""

    # Telegram message limits
    MAX_MESSAGE_LENGTH = 4096
    MAX_CAPTION_LENGTH = 1024

    def __init__(self, bot_token: str = None, channel_id: str = None):
        """Initialize Telegram service
        
        Args:
            bot_token: Telegram bot token (from BotFather)
            channel_id: Channel ID or username (e.g., @channelname or -1001234567890)
        """
        self.bot_token = bot_token or os.getenv("TELEGRAM_BOT_TOKEN")
        self.channel_id = channel_id or os.getenv("TELEGRAM_CHANNEL_ID")

        if not TELEGRAM_AVAILABLE:
            logger.error("Telegram library not available")
            self.bot = None
            return

        if not self.bot_token:
            logger.error("Telegram bot token not provided")
            self.bot = None
            return

        if not self.channel_id:
            logger.error("Telegram channel ID not provided")
            self.bot = None
            return

        try:
            # Check if proxy is configured
            proxy_url = os.getenv("TELEGRAM_PROXY_URL")
            if proxy_url:
                # Use proxy for Telegram API
                from telegram.request import HTTPXRequest
                request = HTTPXRequest(proxy=proxy_url)
                self.bot = Bot(token=self.bot_token, request=request)
                logger.info(f"Telegram bot initialized with proxy: {proxy_url}")
            else:
                self.bot = Bot(token=self.bot_token)
                logger.info("Telegram bot initialized successfully")
            
            # Log channel info
            logger.info(f"Channel ID: {self.channel_id}")
            logger.info(f"Bot token (first 10 chars): {self.bot_token[:10]}...")
            
        except Exception as e:
            logger.error(f"Failed to initialize Telegram bot: {e}")
            self.bot = None

    def escape_html(self, text: str) -> str:
        """Escape special characters for Telegram HTML
        
        Args:
            text: Text to escape
            
        Returns:
            Escaped text safe for HTML
        """
        # HTML entities that need escaping
        text = text.replace('&', '&amp;')
        text = text.replace('<', '&lt;')
        text = text.replace('>', '&gt;')
        text = text.replace('"', '&quot;')
        
        return text
    
    def format_trending_keywords(self, data: Dict) -> str:
        """Format trending keywords data for Telegram message
        
        Args:
            data: Dictionary containing keywords and topics data
            
        Returns:
            Formatted message string
        """
        # Header with timestamp (show both UTC and GMT+7)
        utc_time = datetime.utcnow()
        utc_timestamp = utc_time.strftime("%Y-%m-%d %H:%M UTC")
        
        # Calculate GMT+7
        from datetime import timedelta
        gmt7_time = utc_time + timedelta(hours=7)
        gmt7_timestamp = gmt7_time.strftime("%Y-%m-%d %H:%M GMT+7")
        
        message = f"🔥 <b>Trending Keywords</b>\n"
        message += f"<i>{utc_timestamp} | {gmt7_timestamp}</i>\n\n"

        # Keywords
        keywords = data.get('keywords', [])

        for i, kw in enumerate(keywords[:20], 1):  # Top 20 keywords
            keyword = kw.get('keyword', '')
            score = kw.get('score', 0)
            # Escape special characters in keyword
            keyword_escaped = self.escape_html(keyword)

            # Add emoji based on ranking
            if i <= 3:
                emoji = "🥇🥈🥉"[i - 1]
            elif i <= 10:
                emoji = "🔸"
            else:
                emoji = "▫️"

            message += f"{emoji} {keyword_escaped} (Score: {score})\n"

        # Add topics if requested
        if data.get('include_topics', False):
            topics = data.get('topics', {})
            trending_topics = topics.get('trending_topics', [])

            if trending_topics:
                message += "\n\n📚 <b>Trending Topics</b>\n"
                for i, topic in enumerate(trending_topics[:5], 1):  # Top 5 topics
                    topic_words = topic.get('top_words', [])

                    if topic_words:
                        # Escape each topic word
                        escaped_words = [self.escape_html(word) for word in topic_words[:3]]
                        topic_str = ", ".join(escaped_words)
                        if i <= 3:
                            emoji = "🥇🥈🥉"[i - 1]
                        else:
                            emoji = "▫️"
                        message += f"{emoji} {topic_str}\n"

        return message

    def split_message(self, message: str, max_length: int = MAX_MESSAGE_LENGTH) -> List[str]:
        """Split long message into chunks that fit Telegram limits
        
        Args:
            message: Message to split
            max_length: Maximum length per chunk
            
        Returns:
            List of message chunks
        """
        if len(message) <= max_length:
            return [message]

        chunks = []
        lines = message.split('\n')
        current_chunk = ""

        for line in lines:
            if len(current_chunk) + len(line) + 1 > max_length:
                chunks.append(current_chunk)
                current_chunk = line
            else:
                if current_chunk:
                    current_chunk += '\n'
                current_chunk += line

        if current_chunk:
            chunks.append(current_chunk)

        return chunks

    async def send_message_async(self, text: str, parse_mode: str = ParseMode.HTML) -> Tuple[bool, Optional[str]]:
        """Send message to Telegram channel asynchronously
        
        Args:
            text: Message text
            parse_mode: Parse mode for formatting
            
        Returns:
            Tuple of (success status, error message if failed)
        """
        if not self.bot:
            error_msg = "Telegram bot not initialized"
            logger.error(error_msg)
            return False, error_msg

        try:
            chunks = self.split_message(text)

            for i, chunk in enumerate(chunks):
                # Add continuation marker if multiple chunks
                if len(chunks) > 1:
                    if i == 0:
                        chunk += "\n\n_(continued...)_"
                    elif i < len(chunks) - 1:
                        chunk = f"_(continued from previous)_\n\n{chunk}\n\n_(continued...)_"
                    else:
                        chunk = f"_(continued from previous)_\n\n{chunk}"

                logger.debug(f"Sending chunk {i+1}/{len(chunks)} to channel: {self.channel_id}")
                logger.debug(f"Chunk preview: {chunk[:100]}...")
                
                result = await self.bot.send_message(
                    chat_id=self.channel_id,
                    text=chunk,
                    parse_mode=parse_mode
                )
                logger.debug(f"Message sent successfully. Message ID: {result.message_id}")

                # Small delay between chunks to avoid rate limiting
                if i < len(chunks) - 1:
                    await asyncio.sleep(0.5)

            logger.info(f"Successfully sent {len(chunks)} message(s) to Telegram channel")
            return True, None

        except TelegramError as e:
            error_msg = f"Telegram API error: {str(e)}"
            logger.error(error_msg)
            return False, error_msg
        except Exception as e:
            error_msg = f"Failed to send message: {str(e)}"
            logger.error(error_msg)
            return False, error_msg

    def send_message(self, text: str, parse_mode: str = ParseMode.HTML) -> Tuple[bool, Optional[str]]:
        """Send message to Telegram channel (synchronous wrapper)
        
        Args:
            text: Message text
            parse_mode: Parse mode for formatting
            
        Returns:
            Tuple of (success status, error message if failed)
        """
        if not self.bot or not self.channel_id:
            return False, "Bot or channel not configured"
            
        try:
            # Use asyncio.run() which properly manages the event loop
            return asyncio.run(self.send_message_async(text, parse_mode))
        except RuntimeError as e:
            # If already running in an event loop, use nest_asyncio
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    # Use nest_asyncio to handle nested loops
                    task = loop.create_task(self.send_message_async(text, parse_mode))
                    return loop.run_until_complete(task)
                else:
                    return asyncio.run(self.send_message_async(text, parse_mode))
            except Exception as nested_e:
                error_msg = f"Failed to send message: {str(nested_e)}"
                logger.error(error_msg)
                return False, error_msg
        except Exception as e:
            error_msg = f"Failed to send message: {str(e)}"
            logger.error(error_msg)
            return False, error_msg

    def send_trending_keywords(self, trending_data: Dict) -> Tuple[bool, Optional[str]]:
        """Send formatted trending keywords to Telegram channel
        
        Args:
            trending_data: Dictionary containing trending keywords and topics
            
        Returns:
            Tuple of (success status, error message if failed)
        """
        if not self.bot:
            error_msg = "Telegram bot not initialized"
            logger.error(error_msg)
            return False, error_msg

        try:
            # Format the message
            message = self.format_trending_keywords(trending_data)

            # Send to channel
            return self.send_message(message)

        except Exception as e:
            error_msg = f"Failed to send trending keywords: {str(e)}"
            logger.error(error_msg)
            return False, error_msg

    def send_simple_keywords_list(self, keywords: List[Dict], title: str = "Trending Now") -> Tuple[bool, Optional[str]]:
        """Send a simple list of keywords (useful for quick updates)
        
        Args:
            keywords: List of keyword dictionaries
            title: Title for the message
            
        Returns:
            Tuple of (success status, error message if failed)
        """
        if not self.bot:
            error_msg = "Telegram bot not initialized"
            return False, error_msg

        try:
            # Use the same format as format_trending_keywords for consistency
            data = {"keywords": keywords}
            message = self.format_trending_keywords(data)

            return self.send_message(message)

        except Exception as e:
            error_msg = f"Failed to send simple keywords list: {str(e)}"
            logger.error(error_msg)
            return False, error_msg


# Singleton instance
telegram_service = None


def init_telegram_service(bot_token: str = None, channel_id: str = None):
    """Initialize the telegram service singleton
    
    Args:
        bot_token: Telegram bot token
        channel_id: Channel ID or username
    """
    global telegram_service
    telegram_service = TelegramService(bot_token, channel_id)
    return telegram_service


def get_telegram_service():
    """Get or create the telegram service singleton"""
    global telegram_service
    if telegram_service is None:
        telegram_service = TelegramService()
    return telegram_service
