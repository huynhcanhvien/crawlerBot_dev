import os
import logging
import requests
import nltk
from typing import Set, Dict
from functools import lru_cache

logger = logging.getLogger(__name__)


class StopwordsService:
    """Service for managing stopwords in multiple languages"""

    def __init__(self):
        self._stopwords_cache: Dict[str, Set[str]] = {}
        self._custom_stopwords: Dict[str, Set[str]] = {
            'vietnamese': set(),
            'english': set(),
            'both': set()
        }
        self._initialize_nltk()

    def _initialize_nltk(self):
        """Download required NLTK data"""
        try:
            nltk.data.find('corpora/stopwords')
        except LookupError:
            logger.info("Downloading NLTK stopwords...")
            nltk.download('stopwords', quiet=True)

    @lru_cache(maxsize=1)
    def get_vietnamese_stopwords(self) -> Set[str]:
        """Get comprehensive Vietnamese stopwords"""
        if 'vietnamese' in self._stopwords_cache:
            return self._stopwords_cache['vietnamese']

        stopwords = set()

        # Try to load from online source
        try:
            response = requests.get(
                'https://raw.githubusercontent.com/stopwords/vietnamese-stopwords/master/vietnamese-stopwords.txt',
                timeout=5
            )
            if response.status_code == 200:
                online_stopwords = set(response.text.strip().split('\n'))
                stopwords.update(online_stopwords)
                logger.info(f"Loaded {len(online_stopwords)} Vietnamese stopwords from online source")
        except Exception as e:
            logger.warning(f"Failed to load online Vietnamese stopwords: {e}")

        # Fallback to basic Vietnamese stopwords
        if not stopwords:
            logger.info("Using fallback Vietnamese stopwords")
            stopwords = {
                "là", "và", "có", "được", "của", "với", "cho", "trong", "một", "không",
                "đã", "sẽ", "để", "về", "khi", "tại", "từ", "này", "những", "các",
                "rất", "nhiều", "còn", "như", "nhưng", "thì", "cũng", "vì", "nên", "bởi",
                "vậy", "thì", "hay", "hoặc", "chỉ", "chưa", "đang", "đây", "đó", "ấy",
                "mà", "nếu", "vẫn", "rồi", "lại", "cả", "làm", "gì", "ai", "đâu",
                "nào", "thế", "nữa", "hơn", "bao", "lắm", "ở", "theo", "do", "bị",
                "vào", "ra", "lên", "xuống", "tới", "đến", "sau", "trước", "mới", "cũ",
                "mình", "họ", "triệu", "tỷ", "nó", "thôi", "mua", "amp"
            }

        # Add common Vietnamese particles and function words
        additional_stopwords = {
            "thì", "mà", "nhé", "nhỉ", "chứ", "à", "ạ", "ơi", "hả", "sao",
            "đấy", "thôi", "nha", "nhá", "ha", "hi", "he", "hu", "hừ", "hử",
            "ừ", "ờ", "ôi", "ui", "ủa", "á", "a", "i", "e", "o", "u", "y"
        }
        stopwords.update(additional_stopwords)
        
        # Add tokenized versions of Vietnamese stopwords (for sklearn compatibility)
        # These are generated when Vietnamese diacritics are processed by certain tokenizers
        tokenized_stopwords = {
            'bao', 'bay', 'biến', 'biệt', 'bây', 'bõm', 'bảo', 'bất', 'bẩy', 'bập', 'bắt', 'bội',
            'chao', 'chi', 'chia', 'chu', 'chui', 'chuẩn', 'chà', 'chành', 'chí', 'chót', 'chùn',
            'chăn', 'chũn', 'chưng', 'chạnh', 'chả', 'chầm', 'chầy', 'chập', 'chắn', 'chẳng',
            'chết', 'chốc', 'chừ', 'chừng', 'coi', 'cu', 'cá', 'câu', 'cóc', 'công', 'cạnh',
            'cảm', 'cầu', 'cật', 'cắt', 'cổ', 'cụ', 'cục', 'cực', 'da', 'dà', 'dĩ', 'dưng',
            'dần', 'dầu', 'dịp', 'dở', 'dụng', 'gian', 'giá', 'giác', 'giời', 'hiện', 'hoàn',
            'hèn', 'hình', 'hô', 'hầu', 'hậu', 'hẳn', 'hồ', 'hỗ', 'hội', 'hợp', 'hự', 'khói',
            'khô', 'khăn', 'khắc', 'khẳng', 'kia', 'kiện', 'kê', 'kì', 'kìa', 'kỳ', 'lai',
            'le', 'liên', 'liệt', 'loạt', 'luận', 'luật', 'luốt', 'lình', 'lí', 'lô', 'lý',
            'lập', 'lẽ', 'lị', 'lự', 'lực', 'mày', 'mòi', 'mù', 'mạng', 'mấy', 'mẹ', 'mực',
            'nghiễm', 'ngõ', 'ngăn', 'ngắt', 'ngộ', 'ngờ', 'nhiên', 'nhiêu', 'nhiệt', 'nhung',
            'nhân', 'nhén', 'nhón', 'nhăng', 'nhược', 'nhỡ', 'nả', 'nỗi', 'nở', 'nức', 'oai',
            'phi', 'phui', 'phàm', 'phù', 'phăn', 'phương', 'phỉ', 'quan', 'qui', 'quy', 'quyết',
            'ren', 'riu', 'ríu', 'rón', 'rút', 'rốt', 'sa', 'sinh', 'song', 'sả', 'sẻ', 'sốt',
            'sột', 'sở', 'sợ', 'sức', 'sử', 'ta', 'te', 'tha', 'than', 'thay', 'thi', 'thiên',
            'thiết', 'thoảng', 'thành', 'thái', 'tháo', 'thân', 'thình', 'thúng', 'thương',
            'thảo', 'thảy', 'thắng', 'thể', 'thỉnh', 'thị', 'thời', 'thục', 'thử', 'thực',
            'tiên', 'tiếp', 'tiện', 'tiệt', 'toàn', 'toé', 'trung', 'tráo', 'trình', 'trí',
            'trạng', 'trạo', 'trếu', 'trệu', 'trị', 'trọi', 'trọng', 'trời', 'trở', 'trợ',
            'trừ', 'trực', 'tuyệt', 'tuần', 'tuốt', 'tuồn', 'tuồng', 'tuột', 'tà', 'tàn',
            'tán', 'tâm', 'tê', 'tì', 'tình', 'tít', 'tò', 'tông', 'tù', 'tăm', 'tả', 'tất',
            'tần', 'tập', 'tật', 'tế', 'tề', 'tỏ', 'tốc', 'tối', 'tục', 'tức', 'tử', 'tựu',
            'vung', 'vàn', 'ví', 'vô', 'văng', 'vạn', 'vả', 'vấn', 'vẻ', 'vị', 'vốn', 'xiết',
            'xon', 'xoành', 'xoạch', 'xuất', 'xón', 'xúi', 'xăm', 'xưa', 'xả', 'xảy', 'xắm',
            'xềnh', 'xệch', 'xử', 'xửa', 'yêu', 'âu', 'đi', 'đành', 'đán', 'đánh', 'đáo',
            'đùng', 'đơn', 'đạch', 'đại', 'đảm', 'đất', 'đầu', 'đặc', 'đề', 'địa', 'định',
            'đối', 'đồ', 'đồng', 'đổi', 'ơn', 'ầu', 'ối'
        }
        stopwords.update(tokenized_stopwords)

        # Add social media specific Vietnamese stopwords
        social_media_vn = {
            'gm', 'gn', 'dm', 'cc', 'ck', 'link', 'click', 'xem',
            'hehe', 'hihi', 'haha', 'huhu', 'haiz', 'hic', 'hichic',
            'lol', 'lmao', 'omg', 'wtf', 'btw', 'fyi', 'imo', 'imho', 'tbh',
            'rt', 'retweet', 'reply', 'follow', 'like', 'share', 'comment',
            'tôi', 'bạn', 'nó', 'họ', 'người', 'mình',
            'anh', 'em', 'chị', 'bác', 'chú', 'cô', 'dì'  # Vietnamese pronouns
        }
        stopwords.update(social_media_vn)

        self._stopwords_cache['vietnamese'] = stopwords
        return stopwords

    @lru_cache(maxsize=1)
    def get_english_stopwords(self) -> Set[str]:
        """Get comprehensive English stopwords"""
        if 'english' in self._stopwords_cache:
            return self._stopwords_cache['english']

        # Get NLTK English stopwords
        try:
            from nltk.corpus import stopwords as nltk_stopwords
            stopwords = set(nltk_stopwords.words('english'))
            logger.info(f"Loaded {len(stopwords)} English stopwords from NLTK")
        except Exception as e:
            logger.warning(f"Failed to load NLTK English stopwords: {e}")
            # Fallback to basic English stopwords
            stopwords = {
                "the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for",
                "of", "with", "by", "from", "up", "about", "into", "through", "during",
                "before", "after", "above", "below", "between", "under", "again", "further",
                "then", "once", "here", "there", "when", "where", "why", "how", "all",
                "both", "each", "few", "more", "most", "other", "some", "such", "no",
                "nor", "not", "only", "own", "same", "so", "than", "too", "very",
                "can", "will", "just", "should", "now", "i", "you", "he", "she", "it",
                "we", "they", "them", "their", "this", "that", "these", "those", "am",
                "is", "are", "was", "were", "been", "be", "have", "has", "had", "do",
                "does", "did", "done", "would", "could", "should", "may", "might", "must",
                "shall", "will", "me", "him", "her", "us", "my", "your", "his", "its",
                "our", "their", "mine", "yours"
            }

        # Add web-specific stopwords
        web_stopwords = {
            "http", "https", "www", "com", "org", "net", "html", "htm", "php",
            "aspx", "jsp", "pdf", "doc", "docx", "xls", "xlsx", "png", "jpg",
            "jpeg", "gif", "mp4", "mp3", "zip", "rar", "exe", "dmg", "pkg",
            "deb", "rpm", "tar", "gz", "tgz", "bz2", "7z", "iso", "img",
            "nbsp", "amp", "lt", "gt", "quot", "&amp;"
        }
        stopwords.update(web_stopwords)

        # Add social media and common filler words
        social_media_en = {
            'gm', 'gn', 'dm', 'cc', 'link', 'click', 'see', 'look', 'check',
            'lol', 'lmao', 'omg', 'wtf', 'btw', 'fyi', 'imo', 'imho', 'tbh',
            'rt', 'retweet', 'reply', 'follow', 'like', 'share', 'comment',
            'today', 'tomorrow', 'yesterday', 'week', 'month', 'year', 'time',
            'day', 'minute', 'second', 'hour',
            'thing', 'something', 'anything', 'nothing', 'everything',
            'someone', 'anyone', 'everyone', 'nobody', 'everybody',
            'co', 'gm', 'gn', 'say', 'yes', 'no', 'just',
            'ae', 'next', 'get', 'real',  # Added new stopwords
            'one', 'two', 'three', 'four', 'five', 'six', 'seven', 'eight', 'nine', 'ten',
            'total', 'first', 'last', 'new', 'old', 'good', 'bad', 'big', 'small',
            'go', 'going', 'goes', 'went', 'gone', 'make', 'made', 'making',
            'take', 'took', 'taken', 'taking', 'give', 'gave', 'given', 'giving',
            # Additional stopwords to filter out
            'live', 'team', 'it', "it's", 'its', 'top', 'bottom', 'https', 'http',
            'come', 'coming', 'came', 'know', 'think', 'want', 'need', 'let', 'use',
            'way', 'find', 'found', 'still', 'back', 'well', 'long', 'right', 'left',
            # More common words to filter
            "we're", "we've", "they're", "you're", "i'm", "i've", "i'll", "you'll",
            'token', 'tokens', 'market', 'markets', 'join', 'joined', 'joining',
            'build', 'building', 'built', 'trade', 'trading', 'traded', 'trader',
            'buy', 'sell', 'sold', 'buying', 'selling', 'price', 'value', 'worth',
            'high', 'low', 'up', 'down', 'more', 'less', 'much', 'many', 'very',
            'really', 'actually', 'basically', 'simply', 'just', 'only', 'even',
            'here', 'there', 'where', 'when', 'what', 'which', 'who', 'why', 'how',
            # Additional common words from latest results
            'people', 'person', 'everyone', 'someone', 'anyone', 'nobody', 'everybody',
            'every', 'each', 'all', 'some', 'any', 'few', 'several', 'most', 'none',
            'launch', 'launched', 'launching', 'start', 'started', 'starting', 'begin',
            "don't", "doesn't", "didn't", "won't", "wouldn't", "couldn't", "shouldn't",
            "can't", "isn't", "aren't", "wasn't", "weren't", "hasn't", "haven't",
            'web3', 'web', 'internet', 'online', 'digital', 'virtual',
            'always', 'never', 'ever', 'already', 'yet', 'soon', 'later', 'now',
            # Common words that should be filtered when standalone
            'got', 'great', 'bad',
            # Additional stopwords requested by user
            'points', 'earn', 'alpha', 'beta', 'people', 'every', 'launch', "don't", 'web3',
            'it’s', 'we’re', 'don’t'
        }
        stopwords.update(social_media_en)

        self._stopwords_cache['english'] = stopwords
        return stopwords

    def get_stopwords(self, language: str = 'both') -> Set[str]:
        """Get stopwords for specified language(s) including custom stopwords
        
        Args:
            language: 'vietnamese', 'english', or 'both'
            
        Returns:
            Set of stopwords including custom ones
        """
        base_stopwords = set()

        if language == 'vietnamese':
            base_stopwords = self.get_vietnamese_stopwords()
        elif language == 'english':
            base_stopwords = self.get_english_stopwords()
        elif language == 'both':
            base_stopwords = self.get_vietnamese_stopwords() | self.get_english_stopwords()
        else:
            logger.warning(f"Unknown language: {language}, returning empty set")

        # Add custom stopwords
        custom = self._custom_stopwords.get(language, set())
        if language == 'both':
            custom = self._custom_stopwords['vietnamese'] | self._custom_stopwords['english'] | self._custom_stopwords[
                'both']

        return base_stopwords | custom

    def is_stopword(self, word: str, language: str = 'both') -> bool:
        """Check if a word is a stopword
        
        Args:
            word: Word to check
            language: Language to check against
            
        Returns:
            True if word is a stopword
        """
        stopwords = self.get_stopwords(language)
        return word.lower() in stopwords

    def filter_stopwords(self, words: list, language: str = 'both') -> list:
        """Filter stopwords from a list of words
        
        Args:
            words: List of words to filter
            language: Language to use for filtering
            
        Returns:
            List of words without stopwords
        """
        stopwords = self.get_stopwords(language)
        return [w for w in words if w.lower() not in stopwords]

    def add_custom_stopwords(self, words: Set[str], language: str = 'both'):
        """Add custom stopwords for a specific language
        
        Args:
            words: Set of words to add as stopwords
            language: Language to add stopwords to ('vietnamese', 'english', or 'both')
        """
        if language not in self._custom_stopwords:
            logger.warning(f"Unknown language: {language}")
            return

        self._custom_stopwords[language].update(words)
        logger.info(f"Added {len(words)} custom stopwords to {language}")

    def remove_custom_stopwords(self, words: Set[str], language: str = 'both'):
        """Remove custom stopwords for a specific language
        
        Args:
            words: Set of words to remove from stopwords
            language: Language to remove stopwords from
        """
        if language not in self._custom_stopwords:
            logger.warning(f"Unknown language: {language}")
            return

        self._custom_stopwords[language].difference_update(words)
        logger.info(f"Removed {len(words)} custom stopwords from {language}")

    def get_custom_stopwords(self, language: str = 'both') -> Set[str]:
        """Get custom stopwords for a specific language
        
        Args:
            language: Language to get custom stopwords for
            
        Returns:
            Set of custom stopwords
        """
        if language == 'both':
            return (self._custom_stopwords['vietnamese'] |
                    self._custom_stopwords['english'] |
                    self._custom_stopwords['both'])
        return self._custom_stopwords.get(language, set())

    def clear_custom_stopwords(self, language: str = None):
        """Clear custom stopwords
        
        Args:
            language: Language to clear (None to clear all)
        """
        if language is None:
            for lang in self._custom_stopwords:
                self._custom_stopwords[lang].clear()
            logger.info("Cleared all custom stopwords")
        elif language in self._custom_stopwords:
            self._custom_stopwords[language].clear()
            logger.info(f"Cleared custom stopwords for {language}")


# Singleton instance
stopwords_service = StopwordsService()
