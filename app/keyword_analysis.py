# Enhanced Keyword Analysis with Better Vietnamese Support
import re
import os
from collections import Counter
from typing import List, Tuple, Dict, Any
import json
from .logger import setup_logger

# Set up logger for this module
logger = setup_logger(__name__)

# Load token configuration
TOKEN_CONFIG = None
try:
    config_path = os.path.join(os.path.dirname(__file__), 'token_config.json')
    with open(config_path, 'r') as f:
        TOKEN_CONFIG = json.load(f)
        logger.info("Token configuration loaded successfully")
except Exception as e:
    logger.warning(f"Could not load token configuration: {e}")
    # Default configuration if file not found
    TOKEN_CONFIG = {
        "high_score_token_pattern": {
            "pattern": "$[A-Za-z0-9]{2,5}",
            "score_multiplier": 10
        },
        "stop_high_score_tokens": {
            "tokens": ["$btc", "$eth", "$usdt", "$usdc"]
        }
    }

# Unified NLP service for both languages
try:
    from .services.unified_nlp_service import unified_nlp_service

    UNIFIED_NLP_AVAILABLE = True
except ImportError:
    unified_nlp_service = None
    UNIFIED_NLP_AVAILABLE = False
    logger.warning("Unified NLP service not available")

# Fallback Vietnamese NLP tools
try:
    from pyvi import ViTokenizer

    PYVI_AVAILABLE = True
except ImportError:
    ViTokenizer = None
    PYVI_AVAILABLE = False
    logger.warning("pyvi not installed. Install with: pip install pyvi")

try:
    # Temporarily disable underthesea to avoid NLTK wordnet issues
    # from underthesea import word_tokenize
    # UNDERTHESEA_AVAILABLE = True
    word_tokenize = None
    UNDERTHESEA_AVAILABLE = False
except ImportError:
    word_tokenize = None
    UNDERTHESEA_AVAILABLE = False
    logger.warning("underthesea not installed. Install with: pip install underthesea")

# Import stopwords service
try:
    from .services.stopwords_service import stopwords_service

    STOPWORDS_SERVICE_AVAILABLE = True
except ImportError:
    stopwords_service = None
    STOPWORDS_SERVICE_AVAILABLE = False
    logger.warning("Stopwords service not available")

# KeyBERT for semantic extraction
try:
    from keybert import KeyBERT

    # Model options for multilingual support:
    # 1. 'paraphrase-multilingual-MiniLM-L12-v2' - Good balance of speed and quality
    # 2. 'paraphrase-multilingual-mpnet-base-v2' - Better quality, slower
    # 3. 'all-MiniLM-L12-v2' - English-focused but faster
    # 4. 'sentence-transformers/stsb-xlm-r-multilingual' - Good for Asian languages

    # Use mpnet for better quality if you have the resources
    kw_model = KeyBERT(model='paraphrase-multilingual-mpnet-base-v2')
    KEYBERT_AVAILABLE = True
except (ImportError, OSError, ValueError):
    try:
        # Fallback to MiniLM if mpnet fails
        kw_model = KeyBERT(model='paraphrase-multilingual-MiniLM-L12-v2')
        KEYBERT_AVAILABLE = True
    except:
        KEYBERT_AVAILABLE = False
        kw_model = None

# AI Integration (optional)
try:
    import openai

    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

try:
    import anthropic

    CLAUDE_AVAILABLE = True
except ImportError:
    CLAUDE_AVAILABLE = False

try:
    import google.generativeai as genai

    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False


class EnhancedKeywordAnalyzer:
    """Enhanced bilingual keyword analyzer with better Vietnamese support"""

    def __init__(self, use_ai=False, ai_provider=None, api_key=None):
        self.use_ai = use_ai
        # Get AI provider from env if not specified
        self.ai_provider = ai_provider or os.getenv("AI_PROVIDER", "claude")

        # Get the appropriate API key based on provider
        if self.ai_provider == "gemini":
            self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        else:
            self.api_key = api_key or os.getenv(f"{self.ai_provider.upper()}_API_KEY")

        # Initialize Gemini if using it
        if self.ai_provider == "gemini" and GEMINI_AVAILABLE and self.api_key:
            genai.configure(api_key=self.api_key)

        # Initialize stopwords using the service if available
        if STOPWORDS_SERVICE_AVAILABLE:
            self.vietnamese_stopwords = stopwords_service.get_vietnamese_stopwords()
            self.english_stopwords = stopwords_service.get_english_stopwords()
            # Get combined stopwords for more comprehensive filtering
            self.all_stopwords = stopwords_service.get_stopwords('both')
        else:
            # Fallback to basic stopwords
            self.vietnamese_stopwords = {
                'và', 'của', 'có', 'được', 'là', 'với', 'cho', 'từ', 'một', 'những',
                'các', 'này', 'đó', 'khi', 'nào', 'như', 'để', 'trong', 'trên', 'về',
                'sẽ', 'đã', 'bị', 'bằng', 'hay', 'hoặc', 'mà', 'nếu', 'thì', 'vì',
                'do', 'nên', 'tại', 'theo', 'lại', 'chỉ', 'cũng', 'đều', 'rất',
                'không', 'thôi', 'chưa', 'nhưng', 'còn', 'hơn', 'vào', 'rồi', 'tôi',
                'bạn', 'nó', 'họ', 'người', 'đang', 'rồi', 'mình', 'triệu', 'tỷ'
            }
            self.english_stopwords = {
                'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
                'of', 'with', 'by', 'from', 'up', 'about', 'into', 'through', 'during',
                'is', 'are', 'was', 'were', 'be', 'been', 'being', 'have', 'has', 'had',
                'do', 'does', 'did', 'will', 'would', 'could', 'should', 'may', 'might',
                'co', 'http', 'https', 'your', 'gm', 'gn', 'you', 'i', 'I', 'our', 'their',
                'they', 'he', 'she', 'this', 'that', 'we', 'day', 'month', 'year', 'just',
                'yes', 'no', 'now', 'minute', 'second', 'then', 'say', '&amp;', 'can',
                'time', 'amp', 'ae', 'next'  # Added ae and next to fallback
            }
            self.all_stopwords = self.vietnamese_stopwords | self.english_stopwords

        # Important Vietnamese compound words (expanded)
        self.vietnamese_compounds = {
            # Investment & Finance
            'đầu tư', 'tài chính', 'ngân hàng', 'chứng khoán', 'bất động sản', 'kinh doanh',
            'thương mại', 'xuất khẩu', 'nhập khẩu', 'thị trường', 'doanh nghiệp', 'công ty',
            
            # Project-related compounds
            'dự án mới', 'dự án đầu tư', 'dự án công nghệ', 'dự án blockchain', 'dự án crypto',
            'dự án phát triển', 'dự án khởi nghiệp', 'dự án bất động sản', 'dự án xây dựng',
            'dự án hợp tác', 'dự án nghiên cứu', 'dự án cộng đồng', 'dự án web3',

            # Technology
            'công nghệ', 'trí tuệ nhân tạo', 'học máy', 'dữ liệu lớn', 'điện toán đám mây',
            'internet vạn vật', 'blockchain', 'tiền điện tử', 'khởi nghiệp', 'startup',
            'phần mềm', 'ứng dụng', 'website', 'di động', 'smartphone', 'máy tính',

            # Places & Geography
            'việt nam', 'hà nội', 'thành phố hồ chí minh', 'tp hồ chí minh', 'tp hcm',
            'đà nẵng', 'hải phòng', 'cần thơ', 'nha trang', 'vũng tàu', 'đà lạt',
            'quảng ninh', 'vịnh hạ long', 'sapa', 'phú quốc', 'côn đảo',

            # Education & Work
            'giáo dục', 'đại học', 'trường học', 'sinh viên', 'học sinh', 'giáo viên',
            'nghiên cứu', 'khoa học', 'công việc', 'việc làm', 'tuyển dụng', 'nhân viên',
            'lương thưởng', 'kỹ năng', 'kinh nghiệm', 'phát triển nghề nghiệp',

            # Culture & Society
            'văn hóa', 'truyền thống', 'lịch sử', 'du lịch', 'ẩm thực', 'món ăn',
            'tết nguyên đán', 'lễ hội', 'âm nhạc', 'điện ảnh', 'thể thao', 'bóng đá',
            'sức khỏe', 'y tế', 'bệnh viện', 'thuốc men', 'môi trường', 'biến đổi khí hậu',

            # Government & Politics
            'chính phủ', 'chính sách', 'luật pháp', 'quốc hội', 'bộ trưởng', 'thủ tướng',
            'chủ tịch nước', 'đảng cộng sản', 'nhà nước', 'chính trị', 'ngoại giao',

            # Media & Communication
            'truyền thông', 'báo chí', 'mạng xã hội', 'facebook', 'tiktok', 'youtube',
            'instagram', 'zalo', 'messenger', 'tin tức', 'thông tin', 'báo cáo'
        }

        # Add common English compound words/phrases (for crypto/tech content)
        self.english_compounds = {
            # Crypto & Finance
            'artificial intelligence', 'machine learning', 'deep learning', 'neural network',
            'smart contract', 'decentralized finance', 'non fungible token', 'nft marketplace',
            'crypto currency', 'digital asset', 'blockchain technology', 'web3 ecosystem',
            'bull market', 'bear market', 'market cap', 'trading volume', 'price action',
            'technical analysis', 'fundamental analysis', 'risk management', 'portfolio management',
            'ai agent', 'ai agents', 'crypto agent', 'trading bot', 'defi protocol',
            'layer 2', 'layer two', 'gas fee', 'gas fees', 'wallet address', 'private key',
            'public key', 'seed phrase', 'liquidity pool', 'yield farming', 'staking rewards',
            'market maker', 'limit order', 'stop loss', 'take profit', 'all time high',
            'all time low', 'fear and greed', 'diamond hands', 'paper hands', 'moon shot',
            
            # New crypto compound words with context keywords
            'future of finance', 'future of crypto', 'future of defi', 'future of web3',
            'future of blockchain', 'future trading', 'futures contract', 'futures market',
            'bullish sentiment', 'bullish trend', 'bullish signal', 'bullish divergence',
            'bullish pattern', 'bullish breakout', 'bullish momentum', 'bullish on crypto',
            'community governance', 'community driven', 'community owned', 'community vote',
            'community proposal', 'community fund', 'community rewards', 'community airdrop',
            'points system', 'loyalty points', 'reward points', 'staking points',
            'farming points', 'referral points', 'ecosystem points', 'governance points',
            'virgen points', 'bnb chain', 'ai powered', 'ai powered humanoid', 
            'ai powered humanoid robots', 'decentralized community', 'web3 community',
            'crypto community', 'defi community', 'nft community', 'dao community',

            # Tech & Development  
            'open source', 'software development', 'cloud computing', 'data science',
            'user experience', 'user interface', 'mobile app', 'web application',
            'api integration', 'database management', 'version control', 'code review',
            'machine intelligence', 'natural language', 'computer vision', 'edge computing',

            # Business & Marketing
            'social media', 'content marketing', 'digital marketing', 'brand awareness',
            'customer service', 'user engagement', 'conversion rate', 'growth hacking',
            'product launch', 'market research', 'competitive analysis', 'business model',
            'go to market', 'product market fit', 'venture capital', 'series a'
        }

    def segment_vietnamese_text(self, text: str) -> str:
        """Properly segment Vietnamese text to preserve compound words"""
        if not text:
            return ""

        # Use unified NLP service if available
        if UNIFIED_NLP_AVAILABLE:
            try:
                result = unified_nlp_service.process_vietnamese(text)
                return ' '.join(result['tokens'])
            except Exception as e:
                logger.error(f"Unified NLP service error: {e}")

        # Try pyvi as fallback
        if PYVI_AVAILABLE:
            try:
                return ViTokenizer.tokenize(text)
            except Exception as e:
                logger.error(f"PyVi error: {e}")

        # Fallback to underthesea
        if UNDERTHESEA_AVAILABLE:
            try:
                return word_tokenize(text, format="text")
            except Exception as e:
                logger.error(f"Underthesea error: {e}")

        # Last resort: manual compound preservation
        return self._manual_compound_preservation(text)

    def _manual_compound_preservation(self, text: str, language: str = 'vietnamese') -> str:
        """Manually preserve known compound words"""
        text_lower = text.lower()

        # Choose compound list based on language
        if language == 'english':
            compounds = self.english_compounds
        else:
            compounds = self.vietnamese_compounds

        # Sort compounds by length (longest first) to avoid partial replacements
        sorted_compounds = sorted(compounds, key=len, reverse=True)

        # Replace compounds with underscored versions
        for compound in sorted_compounds:
            if compound in text_lower:
                # Replace with underscored version to preserve as single token
                text = re.sub(
                    r'\b' + re.escape(compound) + r'\b',
                    compound.replace(' ', '_'),
                    text,
                    flags=re.IGNORECASE
                )

        return text

    def _is_time_or_number(self, word: str) -> bool:
        """Check if a word is time-related or a number"""
        word_lower = word.lower()

        # Time-related words to skip
        time_words = {
            'monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday',
            'january', 'february', 'march', 'april', 'may', 'june', 'july', 'august',
            'september', 'october', 'november', 'december',
            'today', 'tomorrow', 'yesterday', 'week', 'month', 'year', 'time',
            'day', 'minute', 'second', 'hour', 'morning', 'afternoon', 'evening', 'night',
            'am', 'pm', 'date', 'dates', 'daily', 'weekly', 'monthly', 'yearly',
            # Vietnamese time words
            'thứ', 'tháng', 'năm', 'ngày', 'giờ', 'phút', 'giây', 'sáng', 'chiều', 'tối',
            'hôm', 'nay', 'qua', 'mai', 'tuần', 'buổi'
        }

        # Check if it's a time word
        if word_lower in time_words:
            return True

        # Check if it's a number or date pattern
        if re.match(r'^\d+$', word):  # Pure number
            return True
        if re.match(r'^\d{1,2}[/-]\d{1,2}([/-]\d{2,4})?$', word):  # Date format
            return True
        if re.match(r'^\d{1,2}:\d{2}', word):  # Time format
            return True

        return False
    
    def _is_mostly_numbers(self, phrase: str) -> bool:
        """Check if a phrase is mostly numbers"""
        tokens = phrase.replace('_', ' ').split()
        number_tokens = sum(1 for token in tokens if re.match(r'^\d+$', token))
        # If more than 50% of tokens are numbers, consider it mostly numbers
        return len(tokens) > 0 and number_tokens / len(tokens) > 0.5
    
    def _is_substring_duplicate(self, keyword: str, existing_keywords: set) -> bool:
        """Check if keyword is a substring of or contains existing keywords"""
        keyword_lower = keyword.lower()
        for existing in existing_keywords:
            existing_lower = existing.lower()
            # Check if one is substring of the other (with significant overlap)
            if len(keyword_lower) > 10 and len(existing_lower) > 10:
                if keyword_lower in existing_lower or existing_lower in keyword_lower:
                    # Allow if they differ by more than just 1-2 words
                    diff_len = abs(len(keyword_lower.split()) - len(existing_lower.split()))
                    if diff_len <= 1:
                        return True
        return False
    
    def _is_high_score_token(self, keyword: str) -> bool:
        """Check if a keyword matches the high score token pattern (e.g., $XXX)"""
        if not TOKEN_CONFIG:
            return False
        
        pattern = TOKEN_CONFIG.get("high_score_token_pattern", {}).get("pattern", "")
        if not pattern:
            return False
        
        # Check if the keyword matches the pattern
        return bool(re.match(f"^{pattern}$", keyword, re.IGNORECASE))
    
    def _should_skip_high_score(self, keyword: str) -> bool:
        """Check if a high score token should be skipped (e.g., common tokens like $BTC)"""
        if not TOKEN_CONFIG:
            return False
        
        stop_tokens = TOKEN_CONFIG.get("stop_high_score_tokens", {}).get("tokens", [])
        return keyword.lower() in [t.lower() for t in stop_tokens]
    
    def _should_prefer_compound(self, keyword: str, all_keywords: list) -> bool:
        """Check if a single word should be skipped in favor of compound versions"""
        if ' ' in keyword or '_' in keyword:
            return False  # Already a compound
        
        keyword_lower = keyword.lower()
        
        # Check if this single word appears as the start of many compounds
        compound_count = sum(
            1 for kw, _ in all_keywords[:200]  # Check top candidates
            if kw.lower().startswith(f"{keyword_lower} ") and 
            not self._is_mostly_numbers(kw)
        )
        
        # If there are multiple compound versions, prefer those
        return compound_count >= 2
    
    def _process_and_filter_keywords(self, sorted_keywords: list, top_n: int) -> list:
        """Process keywords with filtering and duplicate removal"""
        processed = []
        added_lower = set()
        
        # Stop compound words to filter out
        stop_compounds = {'https co', 'anh em', 'dự án'}
        
        # Process all candidates
        for keyword, score in sorted_keywords:
            kw_lower = keyword.lower()
            
            # Filter stop compounds
            if kw_lower in stop_compounds:
                continue
            
            # Basic filters
            # Skip stopword filter for high score tokens
            if not self._is_high_score_token(keyword) and kw_lower in self.all_stopwords:
                continue
            if self._is_mostly_numbers(keyword):
                continue
            
            # Skip single words if compounds exist
            if self._should_prefer_compound(keyword, sorted_keywords):
                continue
            
            # Enhanced duplicate detection
            skip = False
            to_remove = set()
            
            # Split into words for better comparison
            kw_words = set(kw_lower.replace('_', ' ').split())
            
            for existing in list(added_lower):
                ex_words = set(existing.replace('_', ' ').split())
                
                # Calculate overlap between keyword sets
                overlap = kw_words & ex_words
                
                if overlap:
                    # If one keyword is a subset of another
                    if kw_words.issubset(ex_words):
                        # Skip this keyword, we already have a more complete version
                        skip = True
                        break
                    elif ex_words.issubset(kw_words):
                        # Remove the existing shorter keyword
                        to_remove.add(existing)
                    # If keywords share most words (>60% overlap)
                    elif len(overlap) >= 0.6 * max(len(kw_words), len(ex_words)):
                        # Keep the existing one, skip this one
                        skip = True
                        break
            
            if skip:
                continue
                
            # Remove shorter versions
            if to_remove:
                processed = [p for p in processed if p['keyword'].lower() not in to_remove]
                added_lower -= to_remove
            
            # Apply compound word bonus only
            # (High score tokens already have their scores boosted during extraction)
            if ' ' in keyword or '_' in keyword:
                score *= 4.0  # Compound word bonus
            
            processed.append({
                'keyword': keyword,
                'score': round(score, 2),
                'type': 'compound' if ' ' in keyword or '_' in keyword else 'single'
            })
            added_lower.add(kw_lower)
        
        # Sort and return top N
        processed.sort(key=lambda x: x['score'], reverse=True)
        return processed[:top_n]

    def detect_language(self, text: str) -> str:
        """Improved language detection"""
        if not text:
            return 'unknown'

        # Count Vietnamese-specific characters
        vietnamese_chars = len(re.findall(
            r'[àáạảãâầấậẩẫăằắặẳẵèéẹẻẽêềếệểễìíịỉĩòóọỏõôồốộổỗơờớợởỡùúụủũưừứựửữỳýỵỷỹđĐ]',
            text
        ))

        # Count common Vietnamese words
        vietnamese_words = len(re.findall(
            r'\b(và|của|có|được|là|với|cho|từ|một|những|các|này|đó|việt|nam)\b',
            text.lower()
        ))

        # Count common English words
        english_words = len(re.findall(
            r'\b(the|and|or|but|in|on|at|to|for|of|with|by|from|this|that|is|are|was|were)\b',
            text.lower()
        ))

        # Calculate scores
        vietnamese_score = vietnamese_chars * 2 + vietnamese_words * 3
        english_score = english_words * 3

        if vietnamese_score > english_score * 1.5:
            return 'vietnamese'
        elif english_score > vietnamese_score:
            return 'english'
        else:
            return 'mixed'

    def extract_keywords_frequency(self, texts: List[str], top_n: int = 20) -> List[Tuple[str, int]]:
        """Extract keywords using frequency analysis with proper segmentation"""
        keyword_counter = Counter()
        hashtag_counter = Counter()
        high_score_multiplier = TOKEN_CONFIG.get("high_score_token_pattern", {}).get("score_multiplier", 10) if TOKEN_CONFIG else 10

        for text in texts:
            if not text:
                continue

            # Extract hashtags first
            hashtags = re.findall(r'#(\w+)', text)
            hashtag_counter.update(hashtags)
            
            # Extract and score high score tokens (e.g., $XXX)
            if TOKEN_CONFIG:
                pattern = TOKEN_CONFIG.get("high_score_token_pattern", {}).get("pattern", "")
                if pattern:
                    # Find all tokens matching the pattern
                    high_score_tokens = re.findall(f'({pattern})', text, re.IGNORECASE)
                    # Add them with multiplied score
                    for token in high_score_tokens:
                        if not self._should_skip_high_score(token):
                            # Apply multiplier directly during counting
                            keyword_counter[token] += high_score_multiplier
                            logger.debug(f"High score token found: {token} (multiplier: {high_score_multiplier})")
                        else:
                            # Normal count for stop tokens
                            keyword_counter[token] += 1
                            logger.debug(f"Stop token found: {token} (normal count)")

            # Detect language
            lang = self.detect_language(text)

            # Clean text
            text = re.sub(r'http[s]?://\S+', '', text)  # Remove URLs
            text = re.sub(r'https?\s+co\S*', '', text)  # Remove broken URLs like "https co"
            text = re.sub(r'@\w+', '', text)  # Remove mentions

            # Segment text based on language
            if lang == 'vietnamese':
                segmented_text = self.segment_vietnamese_text(text)
                tokens = segmented_text.split()

                # Filter stopwords and short tokens
                # Use all_stopwords if available for more comprehensive filtering
                stopwords_to_use = self.all_stopwords if hasattr(self, 'all_stopwords') else self.vietnamese_stopwords
                meaningful_tokens = [
                    token for token in tokens
                    if (token.lower() not in stopwords_to_use and
                        (len(token) > 2 or '_' in token) and  # Keep compound words
                        not self._is_time_or_number(token.replace('_', ' ')))  # Skip time/number words
                ]
            else:
                # English or mixed - preserve compound words
                text_with_compounds = self._manual_compound_preservation(text, language='english')
                tokens = text_with_compounds.lower().split()
                # Use all_stopwords if available for more comprehensive filtering
                stopwords_to_use = self.all_stopwords if hasattr(self, 'all_stopwords') else self.english_stopwords
                meaningful_tokens = [
                    token for token in tokens
                    if (token.lower() not in stopwords_to_use and
                        (len(token) > 2 or '_' in token) and  # Keep compound words
                        not self._is_time_or_number(token.replace('_', ' ')))  # Skip time/number words
                ]

            # Update counter
            keyword_counter.update(meaningful_tokens)

        # Combine results with weights
        combined_results = []

        # Add hashtags (high weight)
        for tag, count in hashtag_counter.most_common(top_n // 3):
            combined_results.append((f"#{tag}", count * 3))

        # Add keywords
        for keyword, count in keyword_counter.most_common(top_n * 2):
            # Skip time/number words for single words
            if '_' not in keyword and self._is_time_or_number(keyword):
                continue

            # Restore underscores to spaces for display
            display_keyword = keyword.replace('_', ' ')

            # Apply weights based on type
            if '_' in keyword:
                # Compound words get 5x weight
                weight = 5
            else:
                # Single words get 1x weight (high score tokens already have their multiplier)
                weight = 1
            
            combined_results.append((display_keyword, count * weight))

        # Sort by weighted count and return top N
        combined_results.sort(key=lambda x: x[1], reverse=True)
        return combined_results[:top_n]

    def extract_keywords_keybert(self, texts: List[str], top_n: int = 15) -> List[Tuple[str, float]]:
        """Extract keywords using KeyBERT with language-aware processing"""
        if not KEYBERT_AVAILABLE or not kw_model:
            return []

        all_keywords = Counter()

        # Process texts in batches based on language
        vietnamese_texts = []
        english_texts = []

        for text in texts[:250]:  # Limit for performance
            if not text or len(text.strip()) < 20:
                continue

            lang = self.detect_language(text)
            if lang == 'vietnamese':
                vietnamese_texts.append(text)
            else:
                english_texts.append(text)

        # Process Vietnamese texts
        if vietnamese_texts:
            for text in vietnamese_texts:
                try:
                    # Segment Vietnamese text
                    segmented = self.segment_vietnamese_text(text)

                    # Extract keywords with Vietnamese-optimized parameters
                    keywords = kw_model.extract_keywords(
                        segmented,
                        keyphrase_ngram_range=(2, 4),  # Longer phrases for Vietnamese
                        stop_words=list(self.vietnamese_stopwords),
                        top_n=top_n,  # Get more candidates
                        use_mmr=True,
                        diversity=0.85  # Very high diversity to reduce redundancy
                    )

                    for kw, score in keywords:
                        display_kw = kw.replace('_', ' ')
                        all_keywords[display_kw] += score

                except Exception as e:
                    logger.error(f"KeyBERT error (Vietnamese): {e}")

        # Process English texts
        if english_texts:
            for text in english_texts:
                try:
                    keywords = kw_model.extract_keywords(
                        text,
                        keyphrase_ngram_range=(2, 4),
                        stop_words=list(self.english_stopwords),
                        top_n=top_n,  # Get more candidates
                        use_mmr=True,
                        diversity=0.7  # Higher diversity to reduce redundancy
                    )

                    for kw, score in keywords:
                        all_keywords[kw] += score

                except Exception as e:
                    logger.error(f"KeyBERT error (English): {e}")

        # Sort and return top keywords
        sorted_keywords = sorted(all_keywords.items(), key=lambda x: x[1], reverse=True)
        return sorted_keywords[:top_n]

    def extract_keywords_unified_nlp(self, texts: List[str], top_n: int = 20) -> List[Tuple[str, float]]:
        """Extract keywords using unified NLP service for both languages"""
        if not UNIFIED_NLP_AVAILABLE:
            return []

        try:
            # Use the unified NLP service to extract keywords
            result = unified_nlp_service.extract_keywords(texts, top_n)

            # Convert to expected format
            keywords = [
                (kw['keyword'], kw['score'])
                for kw in result.get('keywords', [])
            ]

            # Log language distribution
            lang_dist = result.get('language_distribution', {})
            if lang_dist:
                logger.info(f"Language distribution: {lang_dist}")

            return keywords

        except Exception as e:
            logger.error(f"Unified NLP extraction error: {e}")
            return []

    def extract_keywords_ai(self, texts: List[str], top_n: int = 15) -> List[Tuple[str, float]]:
        """Extract keywords using AI for better context understanding"""
        if not self.use_ai or not self.api_key:
            return []

        # Prepare sample texts
        sample_texts = texts[:500]  # Limit to control token usage

        prompt = f"""Analyze these social media texts (Vietnamese and English) and extract {top_n} trending keywords/topics.

Requirements:
1. Keep Vietnamese compound words together (e.g., "công nghệ", "đầu tư")
2. Focus on meaningful trends, not just frequent words
3. Include relevant hashtags
4. Return keywords that represent actual discussions

Texts:
{' | '.join(sample_texts)}

Return {top_n} keywords in JSON format:
{{"keywords": [{{"keyword": "example", "score": 0.9}}, ...]}}"""

        try:
            if self.ai_provider == "openai" and OPENAI_AVAILABLE and openai is not None:
                client = openai.OpenAI(api_key=self.api_key)
                response = client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.3,
                    max_tokens=1000
                )
                result = response.choices[0].message.content

            elif self.ai_provider == "claude" and CLAUDE_AVAILABLE and anthropic is not None:
                client = anthropic.Anthropic(api_key=self.api_key)
                response = client.messages.create(
                    model="claude-3-5-haiku-20241022",  # Fast & Cheap, $0.80/$4 per million tokens
                    max_tokens=1000,
                    temperature=0.3,
                    messages=[{"role": "user", "content": prompt}]
                )
                result = response.content[0].text

            elif self.ai_provider == "gemini" and GEMINI_AVAILABLE and genai is not None:
                model = genai.GenerativeModel('gemini-1.5-flash')  # Fast & cheap model
                response = model.generate_content(
                    prompt,
                    generation_config=genai.types.GenerationConfig(
                        temperature=0.3,
                        max_output_tokens=1000,
                    )
                )
                result = response.text
            else:
                return []

            # Parse JSON response
            data = json.loads(result)
            keywords = [(item["keyword"], item["score"]) for item in data["keywords"]]
            return keywords[:top_n]

        except Exception as e:
            logger.error(f"AI extraction error: {e}")
            return []

    def extract_keywords_hybrid(self, texts: List[str], top_n: int = 15) -> Dict:
        """Hybrid approach combining all methods"""
        results = {
            "keywords": [],
            "method": "hybrid",
            "total_texts": len(texts),
            "language_distribution": {}
        }

        if not texts:
            return results

        # Analyze language distribution
        lang_counts = Counter()
        for text in texts:
            lang_counts[self.detect_language(text)] += 1
        results["language_distribution"] = dict(lang_counts)

        # Method 1: Frequency-based extraction
        freq_keywords = self.extract_keywords_frequency(texts, top_n * 2)

        # Method 2: KeyBERT extraction
        keybert_keywords = self.extract_keywords_keybert(texts, top_n)

        # Method 3: Unified NLP extraction (for both Vietnamese and English texts)
        unified_nlp_keywords = []
        if UNIFIED_NLP_AVAILABLE:
            unified_nlp_keywords = self.extract_keywords_unified_nlp(texts, top_n)

        # Method 4: AI extraction (if enabled)
        ai_keywords = []
        if self.use_ai:
            ai_keywords = self.extract_keywords_ai(texts, top_n)
            results["ai_used"] = True

        # Combine results with weighted scoring and early deduplication
        combined_scores = {}
        
        # Helper function for early deduplication
        def should_add_keyword(new_kw, existing_keywords):
            new_lower = new_kw.lower().strip()
            new_words = set(new_lower.replace('_', ' ').split())
            
            for existing in existing_keywords:
                existing_lower = existing.lower()
                existing_words = set(existing_lower.replace('_', ' ').split())
                
                # Check overlap
                overlap = new_words & existing_words
                
                if overlap:
                    # Skip if new keyword is subset of existing
                    if new_words.issubset(existing_words):
                        return False
                    # Remove existing if it's subset of new
                    elif existing_words.issubset(new_words):
                        del combined_scores[existing]
                    # Skip if high overlap (>70%)
                    elif len(overlap) >= 0.7 * max(len(new_words), len(existing_words)):
                        return False
            return True

        # Add frequency keywords (already includes high score token multiplier)
        for keyword, count in freq_keywords:
            if should_add_keyword(keyword, list(combined_scores.keys())):
                combined_scores[keyword] = count

        # Add KeyBERT keywords (higher weight)
        for keyword, score in keybert_keywords:
            if should_add_keyword(keyword, list(combined_scores.keys())):
                if keyword in combined_scores:
                    combined_scores[keyword] += score * 100
                else:
                    combined_scores[keyword] = score * 100

        # Add Unified NLP keywords (high weight for both languages)
        for keyword, score in unified_nlp_keywords:
            if should_add_keyword(keyword, list(combined_scores.keys())):
                if keyword in combined_scores:
                    combined_scores[keyword] += score * 150
                else:
                    combined_scores[keyword] = score * 150

        # Add AI keywords (highest weight if available)
        for keyword, score in ai_keywords:
            if should_add_keyword(keyword, list(combined_scores.keys())):
                if keyword in combined_scores:
                    combined_scores[keyword] += score * 200
                else:
                    combined_scores[keyword] = score * 200

        # Sort and prepare final results
        sorted_keywords = sorted(combined_scores.items(), key=lambda x: x[1], reverse=True)

        # Debug: Log compound words found
        compound_words_found = [(kw, score) for kw, score in sorted_keywords if ' ' in kw or '_' in kw]
        if compound_words_found:
            logger.debug(f"Compound words found: {compound_words_found[:10]}")

        # Use the new comprehensive filtering method
        results["keywords"] = self._process_and_filter_keywords(sorted_keywords, top_n)
        return results

    def extract_topics_bertopic(self, texts: List[str], top_n_topics: int = 10) -> Dict[str, Any]:
        """Extract topics using BERTopic for semantic clustering"""
        try:
            from .services.topic_modeling_service import topic_modeling_service

            # Initialize the service
            topic_modeling_service.initialize()

            # Extract trending topics
            trending_topics = topic_modeling_service.extract_trending_topics(
                documents=texts,
                top_n=top_n_topics
            )

            # Get detailed topic information
            topics_info = topic_modeling_service.get_topic_info()

            return {
                "trending_topics": trending_topics,
                "topics_count": len(topics_info),
                "topics_info": topics_info[:top_n_topics]
            }

        except Exception as e:
            logger.error(f"BERTopic extraction failed: {e}")
            return {
                "trending_topics": [],
                "topics_count": 0,
                "topics_info": []
            }


# Convenience function for easy integration
def analyze_trending_keywords(texts: List[str] = None, top_n: int = 20,
                              use_ai: bool = False, ai_provider: str = None,
                              api_key: str = None, tweets_per_user: int = None,
                              save_to_db: bool = True, root_user_id: str = None,
                              limit: int = None, use_percentage: bool = False,
                              percent_tweets: int = 40, time_filter_enabled: bool = False,
                              days_recent: int = 30) -> Dict:
    """
    Main function to analyze trending keywords from texts

    Args:
        texts: List of text documents (tweets, posts, etc.). If None, loads from DB
        top_n: Number of top keywords to return
        use_ai: Whether to use AI for enhanced extraction
        ai_provider: "openai", "claude", or "gemini" (defaults to env var AI_PROVIDER)
        api_key: API key for AI provider (optional, can use env var)
        tweets_per_user: If provided, loads N recent tweets per user from DB
        save_to_db: Whether to save results to database
        root_user_id: Root user ID to filter tweets by (for multi-user support)
        limit: Maximum number of tweets to load (None = no limit for root_user)
        use_percentage: Whether to use percentage-based tweet selection
        percent_tweets: Percentage of recent tweets to analyze per user (0-100)
        time_filter_enabled: Whether to filter tweets by time
        days_recent: Number of recent days to consider for analysis

    Returns:
        Dictionary with keywords and metadata
    """
    # Load texts from database if not provided
    if texts is None:
        from .mongo_client import MongoDBClient
        mongo = MongoDBClient()

        if tweets_per_user or use_percentage:
            # Load tweets per user with new configuration options
            texts = mongo.load_recent_texts_per_user(
                tweets_per_user=tweets_per_user,
                root_user_id=root_user_id,
                use_percentage=use_percentage,
                percent_tweets=percent_tweets,
                time_filter_enabled=time_filter_enabled,
                days_recent=days_recent
            )
        else:
            # Filter by root_user_id if provided
            if root_user_id:
                query = {"root_user_id": root_user_id}
                # If limit is None and root_user_id is specified, get all tweets for that root user
                if limit is None:
                    docs = mongo.col.find(query).sort("created_at", -1)
                else:
                    docs = mongo.col.find(query).sort("created_at", -1).limit(limit)
                texts = [doc["text"] for doc in docs if "text" in doc]
            else:
                # Default limit for general queries
                texts = mongo.load_texts(limit=limit or 600)

    if not texts:
        return {
            "keywords": [],
            "total_analyzed_texts": 0,
            "method": "none",
            "ai_used": False,
            "message": "No texts found for analysis"
        }

    analyzer = EnhancedKeywordAnalyzer(
        use_ai=use_ai,
        ai_provider=ai_provider,
        api_key=api_key
    )

    results = analyzer.extract_keywords_hybrid(texts, top_n)
    results["total_analyzed_texts"] = len(texts)

    # Add topic modeling results
    topics_results = analyzer.extract_topics_bertopic(texts, top_n_topics=10)
    results["topics"] = topics_results

    # Save to database if requested
    if save_to_db and results.get("keywords") and root_user_id:
        from .mongo_client import MongoDBClient
        mongo = MongoDBClient()
        mongo.save_trending_keywords(
            keywords=results["keywords"],
            root_user_id=root_user_id,
            method=results.get("method", "hybrid"),
            ai_used=results.get("ai_used", False),
            topics=results.get("topics", None)
        )

    return results


# Example usage
if __name__ == "__main__":
    # Test with sample Vietnamese/English texts
    sample_texts = [
        "Công nghệ blockchain và trí tuệ nhân tạo đang thay đổi ngành tài chính Việt Nam #fintech #AI",
        "Thị trường bất động sản Hà Nội tăng trưởng mạnh trong quý 3 #batdongsan #hanoi",
        "Machine learning applications in healthcare showing promising results #ML #healthtech",
        "Đầu tư vào startup công nghệ tại Việt Nam đạt kỷ lục mới #startup #investment",
        "Chính sách mới về chuyển đổi số cho doanh nghiệp vừa và nhỏ #digitaltransformation"
    ]

    # Extract keywords without AI
    results = analyze_trending_keywords(sample_texts, top_n=10, use_ai=False)

    logger.info("Trending Keywords (No AI):")
    for kw_data in results["keywords"]:
        logger.info(f"- {kw_data['keyword']}: {kw_data['score']} ({kw_data['type']})")

    logger.info(f"Language distribution: {results['language_distribution']}")

    # Extract with AI (if API key is available)
    # results_ai = analyze_trending_keywords(sample_texts, top_n=10, use_ai=True)
