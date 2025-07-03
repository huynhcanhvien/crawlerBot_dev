"""
Unified NLP service for English and Vietnamese without VnCoreNLP
Uses spaCy for English and pyvi for Vietnamese
"""

import re
import logging
import os
import json
from typing import List, Dict, Set
from collections import Counter
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer

# Vietnamese processing
try:
    from pyvi import ViTokenizer, ViPosTagger

    PYVI_AVAILABLE = True
except ImportError:
    PYVI_AVAILABLE = False

# English processing
try:
    import spacy

    SPACY_AVAILABLE = True
except ImportError:
    SPACY_AVAILABLE = False

try:
    import nltk
    from nltk.tokenize import word_tokenize
    from nltk.corpus import stopwords
    from nltk.stem import PorterStemmer, WordNetLemmatizer
    from nltk import pos_tag

    NLTK_AVAILABLE = True
except ImportError:
    NLTK_AVAILABLE = False

# Language detection
try:
    from langdetect import detect_langs, LangDetectException

    LANGDETECT_AVAILABLE = True
except ImportError:
    LANGDETECT_AVAILABLE = False

logger = logging.getLogger(__name__)

# Load token configuration
TOKEN_CONFIG = None
try:
    config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'token_config.json')
    with open(config_path, 'r') as f:
        TOKEN_CONFIG = json.load(f)
except Exception as e:
    logger.warning(f"Could not load token configuration: {e}")


class UnifiedNLPService:
    """Unified NLP service for both English and Vietnamese text processing"""

    def __init__(self):
        self.en_nlp = None
        
        # Import stopwords service
        try:
            from .stopwords_service import stopwords_service
            self.stopwords_service = stopwords_service
            self.vi_stopwords = stopwords_service.get_vietnamese_stopwords()
            self.en_stopwords = stopwords_service.get_english_stopwords()
        except ImportError:
            logger.warning("Stopwords service not available, using fallback")
            self.stopwords_service = None
            self.vi_stopwords = self._load_vietnamese_stopwords()
            self.en_stopwords = self._load_english_stopwords()

        # Initialize English NLP
        if SPACY_AVAILABLE:
            try:
                self.en_nlp = spacy.load("en_core_web_sm")
                logger.info("Loaded spaCy English model")
            except:
                logger.warning("spaCy English model not found. Install with: python -m spacy download en_core_web_sm")

        # Initialize NLTK components
        if NLTK_AVAILABLE:
            try:
                # Download required NLTK data
                nltk.download('punkt', quiet=True)
                nltk.download('punkt_tab', quiet=True)  # New tokenizer data
                nltk.download('averaged_perceptron_tagger', quiet=True)
                nltk.download('averaged_perceptron_tagger_eng', quiet=True)
                nltk.download('wordnet', quiet=True)
                nltk.download('stopwords', quiet=True)
                self.stemmer = PorterStemmer()
                self.lemmatizer = WordNetLemmatizer()
            except Exception as e:
                logger.warning(f"Failed to download NLTK data: {e}")

        # Get all stopwords (including social media) from stopwords service
        if self.stopwords_service:
            all_stopwords = self.stopwords_service.get_stopwords('both')
            self.social_stopwords = all_stopwords
        else:
            # Fallback social media stopwords
            self.social_stopwords = {
                'http', 'https', 'www', 'com', 'co', 't', 's', 've', 'll', 're', 'd', 'm',
                'ur', 'u', 'gonna', 'gotta', 'wanna', 'kinda', 'sorta', 'lol', 'lmao',
                'btw', 'omg', 'wtf', 'idk', 'imo', 'tbh', 'smh', 'dm', 'rt', 'cc',
                'amp', 'gt', 'lt', 'via', 'de', 'en', 'la', 'el', 'un', 'uma', 'ae', 'next'
            }

        # Vietnamese compound words to preserve
        self.vi_compounds = {
            # Technology
            'công_nghệ', 'trí_tuệ_nhân_tạo', 'học_máy', 'big_data', 'blockchain',
            'tiền_điện_tử', 'phần_mềm', 'ứng_dụng', 'startup', 'khởi_nghiệp',

            # Business
            'đầu_tư', 'tài_chính', 'ngân_hàng', 'chứng_khoán', 'bất_động_sản',
            'kinh_doanh', 'thương_mại', 'xuất_khẩu', 'nhập_khẩu', 'thị_trường',

            # Places
            'việt_nam', 'hà_nội', 'sài_gòn', 'đà_nẵng', 'nha_trang', 'phú_quốc',

            # Culture
            'văn_hóa', 'du_lịch', 'ẩm_thực', 'âm_nhạc', 'điện_ảnh', 'thể_thao'
        }

    def _load_vietnamese_stopwords(self) -> Set[str]:
        """Load comprehensive Vietnamese stopwords"""
        return {
            'và', 'của', 'có', 'được', 'là', 'với', 'cho', 'từ', 'một', 'những',
            'các', 'này', 'đó', 'khi', 'nào', 'như', 'để', 'trong', 'trên', 'về',
            'sẽ', 'đã', 'bị', 'bằng', 'hay', 'hoặc', 'mà', 'nếu', 'thì', 'vì',
            'do', 'nên', 'tại', 'theo', 'lại', 'chỉ', 'cũng', 'đều', 'rất',
            'không', 'thôi', 'chưa', 'nhưng', 'còn', 'hơn', 'vào', 'rồi', 'tôi',
            'bạn', 'nó', 'họ', 'người', 'đang', 'mình', 'ra', 'đi', 'lên', 'xuống',
            'qua', 'sang', 'tới', 'lui', 'nữa', 'thêm', 'bớt', 'vẫn', 'cả',
            'chúng', 'ta', 'chúng_ta', 'chúng_tôi', 'anh', 'chị', 'em', 'ông', 'bà',
            'cái', 'con', 'cuộc', 'việc', 'điều', 'năm', 'tháng', 'ngày', 'giờ',
            'mua', 'mình', 'triệu', 'tỷ', 'thôi', 'họ', 'nó'
        }

    def _load_english_stopwords(self) -> Set[str]:
        """Load comprehensive English stopwords"""
        base_stopwords = {
            'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
            'of', 'with', 'by', 'from', 'up', 'about', 'into', 'through', 'during',
            'is', 'are', 'was', 'were', 'be', 'been', 'being', 'have', 'has', 'had',
            'do', 'does', 'did', 'will', 'would', 'could', 'should', 'may', 'might',
            'must', 'shall', 'can', 'need', 'ought', 'used', 'get', 'got', 'getting',
            'i', 'me', 'my', 'myself', 'we', 'our', 'ours', 'ourselves', 'you', 'your',
            'yours', 'yourself', 'yourselves', 'he', 'him', 'his', 'himself', 'she',
            'her', 'hers', 'herself', 'it', 'its', 'itself', 'they', 'them', 'their',
            'theirs', 'themselves', 'what', 'which', 'who', 'whom', 'this', 'that',
            'these', 'those', 'am', 'as', 'such', 'if', 'so', 'than', 'too', 'very',
            'just', 'now', 'here', 'there', 'when', 'where', 'why', 'how', 'all',
            'any', 'both', 'each', 'few', 'more', 'most', 'other', 'some', 'such',
            'no', 'nor', 'not', 'only', 'own', 'same', 'then', 'also', 'back',
            'after', 'before', 'because', 'since', 'while', 'although', 'though'
        }

        # Add NLTK stopwords if available
        if NLTK_AVAILABLE:
            try:
                base_stopwords.update(stopwords.words('english'))
            except:
                pass

        return base_stopwords

    def detect_language(self, text: str) -> str:
        """Detect language of text using multiple methods"""
        if not text or len(text.strip()) < 3:
            return 'unknown'

        # Method 1: Use langdetect if available
        if LANGDETECT_AVAILABLE:
            try:
                langs = detect_langs(text)
                if langs and langs[0].prob > 0.8:
                    lang_code = langs[0].lang
                    if lang_code == 'vi':
                        return 'vietnamese'
                    elif lang_code in ['en', 'eng']:
                        return 'english'
            except LangDetectException:
                pass

        # Method 2: Character and word-based detection
        # Vietnamese character pattern
        vi_char_pattern = r'[àáạảãâầấậẩẫăằắặẳẵèéẹẻẽêềếệểễìíịỉĩòóọỏõôồốộổỗơờớợởỡùúụủũưừứựửữỳýỵỷỹđĐ]'
        vi_chars = len(re.findall(vi_char_pattern, text))

        # Common Vietnamese words
        vi_words = len(re.findall(
            r'\b(và|của|có|được|là|với|cho|từ|một|những|các|này|đó|việt|nam|người|không|trong|để|nhưng)\b',
            text.lower()
        ))

        # Common English words
        en_words = len(re.findall(
            r'\b(the|and|or|but|in|on|at|to|for|of|with|by|from|this|that|is|are|was|were|have|has|had)\b',
            text.lower()
        ))

        # Calculate scores
        vi_score = vi_chars * 3 + vi_words * 2
        en_score = en_words * 2

        # Determine language
        if vi_score > en_score * 1.2:
            return 'vietnamese'
        elif en_score > vi_score:
            return 'english'
        elif vi_score > 0 and en_score > 0:
            return 'mixed'
        else:
            return 'unknown'

    def process_vietnamese(self, text: str) -> Dict[str, any]:
        """Process Vietnamese text using pyvi"""
        result = {
            'tokens': [],
            'keywords': [],
            'pos_tags': [],
            'entities': []
        }

        if not PYVI_AVAILABLE:
            # Fallback to simple tokenization
            tokens = text.lower().split()
            result['tokens'] = tokens
            result['keywords'] = [t for t in tokens if t not in self.vi_stopwords and len(t) > 2]
            return result

        try:
            # Tokenize with pyvi
            tokenized = ViTokenizer.tokenize(text)

            # POS tagging
            pos_tagged = ViPosTagger.postagging(tokenized)

            if len(pos_tagged) >= 2:
                words, tags = pos_tagged
                result['tokens'] = words
                result['pos_tags'] = list(zip(words, tags))

                # Extract keywords based on POS tags
                meaningful_tags = {'N', 'Np', 'V', 'A', 'M',
                                   'R'}  # Nouns, Proper nouns, Verbs, Adjectives, Numbers, Adverbs

                for word, tag in zip(words, tags):
                    word_lower = word.lower()
                    # Keep if meaningful tag and not stopword
                    if tag in meaningful_tags and word_lower not in self.vi_stopwords:
                        # Check if it's a compound word
                        if '_' in word:
                            result['keywords'].append(word_lower)
                        elif len(word_lower) > 2:  # Skip very short words
                            result['keywords'].append(word_lower)

                # Extract entities (simple approach for Vietnamese)
                current_entity = []
                for word, tag in zip(words, tags):
                    if tag == 'Np':  # Proper noun
                        current_entity.append(word)
                    else:
                        if current_entity:
                            entity = ' '.join(current_entity)
                            if len(entity.split()) >= 2 or entity[0].isupper():
                                result['entities'].append(entity)
                            current_entity = []

                # Don't forget last entity
                if current_entity:
                    entity = ' '.join(current_entity)
                    if len(entity.split()) >= 2 or entity[0].isupper():
                        result['entities'].append(entity)

        except Exception as e:
            logger.error(f"Vietnamese processing error: {e}")
            # Fallback
            tokens = text.lower().split()
            result['tokens'] = tokens
            result['keywords'] = [t for t in tokens if t not in self.vi_stopwords and len(t) > 2]

        return result

    def process_english(self, text: str) -> Dict[str, any]:
        """Process English text using spaCy or NLTK"""
        result = {
            'tokens': [],
            'keywords': [],
            'pos_tags': [],
            'entities': []
        }

        # Use spaCy if available
        if self.en_nlp:
            try:
                doc = self.en_nlp(text)

                # Extract tokens and POS tags
                for token in doc:
                    result['tokens'].append(token.text.lower())
                    result['pos_tags'].append((token.text, token.pos_))

                    # Extract keywords
                    if (token.pos_ in ['NOUN', 'PROPN', 'VERB', 'ADJ'] and
                            not token.is_stop and
                            token.text.lower() not in self.en_stopwords and
                            len(token.text) > 2):
                        result['keywords'].append(token.lemma_.lower())

                # Extract entities
                for ent in doc.ents:
                    result['entities'].append((ent.text, ent.label_))

                return result
            except Exception as e:
                logger.error(f"spaCy processing error: {e}")

        # Fallback to NLTK
        if NLTK_AVAILABLE:
            try:
                # Tokenize
                tokens = word_tokenize(text.lower())
                result['tokens'] = tokens

                # POS tagging
                pos_tags = pos_tag(tokens)
                result['pos_tags'] = pos_tags

                # Extract keywords
                meaningful_tags = {
                    'NN', 'NNS', 'NNP', 'NNPS',  # Nouns
                    'VB', 'VBD', 'VBG', 'VBN', 'VBP', 'VBZ',  # Verbs
                    'JJ', 'JJR', 'JJS'  # Adjectives
                }

                for word, tag in pos_tags:
                    if (tag in meaningful_tags and
                            word not in self.en_stopwords and
                            len(word) > 2 and
                            word.isalpha()):
                        # Lemmatize or stem
                        try:
                            lemma = self.lemmatizer.lemmatize(word)
                            result['keywords'].append(lemma)
                        except:
                            result['keywords'].append(word)

            except Exception as e:
                logger.error(f"NLTK processing error: {e}")

        # Final fallback
        if not result['tokens']:
            tokens = text.lower().split()
            result['tokens'] = tokens
            result['keywords'] = [
                t for t in tokens
                if t not in self.en_stopwords and len(t) > 2 and t.isalpha()
            ]

        return result
    
    def _extract_high_score_tokens(self, text: str) -> List[str]:
        """Extract high score tokens (e.g., $XXX) from text"""
        high_score_tokens = []
        if TOKEN_CONFIG:
            pattern = TOKEN_CONFIG.get("high_score_token_pattern", {}).get("pattern", "")
            stop_tokens = set(t.lower() for t in TOKEN_CONFIG.get("stop_high_score_tokens", {}).get("tokens", []))
            
            if pattern:
                # Find all tokens matching the pattern
                tokens = re.findall(f'({pattern})', text, re.IGNORECASE)
                # Filter out stop tokens
                high_score_tokens = [t for t in tokens if t.lower() not in stop_tokens]
        
        return high_score_tokens

    def extract_keywords(self, texts: List[str], top_n: int = 20) -> Dict[str, any]:
        """Extract keywords from mixed language texts"""
        all_keywords = []
        language_stats = Counter()
        all_entities = []
        high_score_token_counts = Counter()
        high_score_multiplier = TOKEN_CONFIG.get("high_score_token_pattern", {}).get("score_multiplier", 10) if TOKEN_CONFIG else 10

        for text in texts:
            # Extract high score tokens first (before cleaning)
            high_score_tokens = self._extract_high_score_tokens(text)
            for token in high_score_tokens:
                high_score_token_counts[token] += high_score_multiplier
            # Clean text
            text = self._clean_text(text)
            if not text:
                continue

            # Detect language
            lang = self.detect_language(text)
            language_stats[lang] += 1

            # Process based on language
            if lang == 'vietnamese':
                result = self.process_vietnamese(text)
            elif lang == 'english':
                result = self.process_english(text)
            else:
                # For mixed or unknown, try both
                vi_result = self.process_vietnamese(text)
                en_result = self.process_english(text)
                result = {
                    'keywords': vi_result['keywords'] + en_result['keywords'],
                    'entities': vi_result['entities'] + en_result['entities']
                }

            all_keywords.extend(result['keywords'])
            all_entities.extend(result.get('entities', []))

        # Count keyword frequencies
        keyword_counts = Counter(all_keywords)
        
        # Merge high score token counts with boosted scores
        for token, count in high_score_token_counts.items():
            keyword_counts[token] += count

        # Filter out noise
        filtered_keywords = {
            word: count for word, count in keyword_counts.items()
            if count > 1 or '_' in word or (TOKEN_CONFIG and re.match(TOKEN_CONFIG.get("high_score_token_pattern", {}).get("pattern", ""), word, re.IGNORECASE))  # Keep compounds and high score tokens
        }

        # Calculate TF-IDF scores
        keyword_scores = self._calculate_tfidf_scores(filtered_keywords, texts)

        # Sort and get top keywords
        sorted_keywords = sorted(
            keyword_scores.items(),
            key=lambda x: x[1],
            reverse=True
        )[:top_n]

        return {
            'keywords': [
                {
                    'keyword': word,
                    'score': score,
                    'frequency': filtered_keywords.get(word, 0),
                    'type': 'compound' if '_' in word else 'single'
                }
                for word, score in sorted_keywords
            ],
            'language_distribution': dict(language_stats),
            'entities': Counter(all_entities).most_common(10),
            'total_texts': len(texts),
            'total_keywords_extracted': len(all_keywords)
        }

    def _clean_text(self, text: str) -> str:
        """Clean text for processing"""
        # Remove URLs
        text = re.sub(r'http[s]?://\S+', '', text)
        # Remove mentions
        text = re.sub(r'@\w+', '', text)
        # Keep hashtag content
        text = re.sub(r'#(\w+)', r'\1', text)
        # Remove extra whitespace
        text = ' '.join(text.split())
        return text

    def _calculate_tfidf_scores(self, keyword_counts: Dict[str, int], texts: List[str]) -> Dict[str, float]:
        """Calculate TF-IDF scores for keywords"""
        try:
            # Create a custom analyzer that preserves our keywords
            def custom_analyzer(text):
                return [w for w in keyword_counts.keys() if w in text.lower()]

            # Use TfidfVectorizer
            vectorizer = TfidfVectorizer(
                analyzer=custom_analyzer,
                max_features=len(keyword_counts)
            )

            # Fit and transform
            tfidf_matrix = vectorizer.fit_transform(texts)

            # Get feature names
            feature_names = vectorizer.get_feature_names_out()

            # Calculate average TF-IDF scores
            avg_scores = np.mean(tfidf_matrix.toarray(), axis=0)

            # Create score dictionary
            scores = {}
            for i, word in enumerate(feature_names):
                # Combine TF-IDF with frequency
                freq_score = keyword_counts[word] / len(texts)
                tfidf_score = avg_scores[i]
                combined_score = 0.6 * tfidf_score + 0.4 * freq_score
                scores[word] = combined_score

            return scores

        except Exception as e:
            logger.error(f"TF-IDF calculation error: {e}")
            # Fallback to frequency-based scoring
            total_texts = len(texts)
            return {
                word: count / total_texts
                for word, count in keyword_counts.items()
            }


# Singleton instance
unified_nlp_service = UnifiedNLPService()
