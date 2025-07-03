# keyword_analysis_old.py - Bilingual Vietnamese + English Support

import re
from collections import Counter
from keybert import KeyBERT
from .mongo_client import MongoDBClient

# Initialize KeyBERT with multilingual model
try:
    # Use multilingual sentence transformer for both Vietnamese and English
    kw_model = KeyBERT(model='paraphrase-multilingual-MiniLM-L12-v2')
    print("✅ Using multilingual KeyBERT model (supports Vietnamese + English)")
except (ImportError, OSError, Exception) as e:
    # Fallback to default model if multilingual model fails
    try:
        kw_model = KeyBERT()
        print(f"⚠️ Using default KeyBERT model: {e}")
    except (ImportError, OSError) as fallback_error:
        print(f"❌ Failed to initialize KeyBERT: {fallback_error}")
        kw_model = None

# Vietnamese compound words/phrases that should be kept together
VIETNAMESE_COMPOUND_WORDS = {
    # Investment & Finance
    'đầu tư', 'tài chính', 'ngân hàng', 'chứng khoán', 'bất động sản', 'kinh doanh',
    'thương mại', 'xuất khẩu', 'nhập khẩu', 'thị trường', 'doanh nghiệp', 'công ty',

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

# English compound words/phrases that should be kept together
ENGLISH_COMPOUND_WORDS = {
    # Technology
    'artificial intelligence', 'machine learning', 'deep learning', 'big data', 'cloud computing',
    'internet of things', 'cyber security', 'data science', 'software development', 'web development',
    'mobile app', 'social media', 'digital marketing', 'e commerce', 'fintech',

    # Business & Finance
    'real estate', 'stock market', 'venture capital', 'private equity', 'market research',
    'business development', 'project management', 'supply chain', 'customer service',
    'human resources', 'marketing strategy', 'sales strategy',

    # Places
    'united states', 'new york', 'los angeles', 'san francisco', 'silicon valley',
    'hong kong', 'united kingdom', 'south korea', 'saudi arabia',

    # Education & Work
    'higher education', 'online learning', 'remote work', 'work from home',
    'job market', 'career development', 'professional development',

    # Health & Environment
    'climate change', 'renewable energy', 'sustainable development', 'public health',
    'mental health', 'health care', 'medical research',

    # Current Events & Politics
    'foreign policy', 'international relations', 'economic growth', 'trade war',
    'global economy', 'financial crisis', 'economic recovery'
}

# Single words that should be filtered out (too generic)
GENERIC_FILTER_WORDS = {
    # Vietnamese generic words
    'đầu', 'tư', 'công', 'nghệ', 'thành', 'phố', 'thị', 'trường', 'doanh', 'nghiệp',
    'phát', 'triển', 'kinh', 'tài', 'chính', 'ngân', 'hàng', 'chứng', 'khoán',
    'bất', 'động', 'sản', 'xuất', 'khẩu', 'nhập', 'việc', 'làm', 'sinh', 'viên',
    'học', 'sinh', 'giáo', 'viên', 'trường', 'đại', 'cao', 'đẳng', 'trung', 'cấp',
    'văn', 'hóa', 'truyền', 'thống', 'lịch', 'sử', 'du', 'lịch', 'ẩm', 'thực',

    # English generic words
    'real', 'estate', 'stock', 'market', 'business', 'development', 'management',
    'service', 'system', 'technology', 'digital', 'online', 'mobile', 'social',
    'media', 'data', 'information', 'research', 'study', 'analysis', 'report'
}

# Combined stopwords for Vietnamese and English
BILINGUAL_STOPWORDS = {
    # Vietnamese stopwords
    'và', 'của', 'có', 'được', 'là', 'với', 'cho', 'từ', 'một', 'những', 'các', 'này', 'đó',
    'khi', 'nào', 'như', 'để', 'trong', 'trên', 'về', 'sẽ', 'đã', 'bị', 'bằng', 'hay', 'hoặc',
    'mà', 'nếu', 'thì', 'vì', 'do', 'nên', 'tại', 'theo', 'lại', 'chỉ', 'cũng', 'đều', 'sau',
    'trước', 'giữa', 'dưới', 'trên', 'trong', 'ngoài', 'cùng', 'nhau', 'khác', 'nhiều', 'ít',
    'lớn', 'nhỏ', 'tốt', 'xấu', 'mới', 'cũ', 'rất', 'tất', 'cả', 'người', 'ngày', 'năm', 'mình',
    'không', 'thôi', 'ae', 'chưa', 'anh', 'em', 'nó', 'nhưng', 'còn', 'hơn', 'vào', 'rồi', 'dự',
    'giá', 'đang', 'sẽ', 'đã', 'cần', 'muốn', 'thích', 'ngày', 'tháng', 'năm', 'đến', 'nhìn',
    'thấy', 'xem',

    # English stopwords
    'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by',
    'from', 'up', 'about', 'into', 'through', 'during', 'before', 'after', 'above', 'below',
    'between', 'among', 'is', 'are', 'was', 'were', 'be', 'been', 'being', 'have', 'has', 'had',
    'do', 'does', 'did', 'will', 'would', 'could', 'should', 'may', 'might', 'must', 'can',
    'this', 'that', 'these', 'those', 'i', 'me', 'my', 'myself', 'we', 'our', 'ours', 'ourselves',
    'you', 'your', 'yours', 'yourself', 'yourselves', 'he', 'him', 'his', 'himself', 'she', 'her',
    'hers', 'herself', 'it', 'its', 'itself', 'they', 'them', 'their', 'theirs', 'themselves',
    'what', 'which', 'who', 'whom', 'whose', 'where', 'when', 'why', 'how', 'all', 'any', 'both',
    'each', 'few', 'more', 'most', 'other', 'some', 'such', 'no', 'nor', 'not', 'only', 'own',
    'same', 'so', 'than', 'too', 'very', 'just', 'now', 'get', 'go', 'make', 'see', 'come', 'know',
    'keep', 'need', 'want',

    # Common social media terms
    'rt', 'retweet', 'http', 'https', 'www', 'com', 'co', 'vn', 'org', 'net', 'like', 'follow',
    'share', 'via', 'cc', 'dm', 'pm', 'lol', 'omg', 'wtf', 'btw', 'fyi', 'imo', 'imho'
}


def detect_language(text):
    """Simple language detection for Vietnamese vs English"""
    if not text:
        return 'unknown'

    try:
        # Vietnamese character patterns
        vietnamese_chars = re.findall(r'[àáạảãâầấậẩẫăằắặẳẵèéẹẻẽêềếệểễìíịỉĩòóọỏõôồốộổỗơờớợởỡùúụủũưừứựửữỳýỵỷỹđĐ]',
                                      text.lower())
        vietnamese_words = len(
            re.findall(r'\b(và|của|có|được|là|với|cho|từ|một|những|các|này|đó|người|việt|nam)\b', text.lower()))

        # English patterns
        english_words = len(
            re.findall(r'\b(the|and|or|but|in|on|at|to|for|of|with|by|from|this|that|is|are|was|were)\b', text.lower()))

        # Simple scoring
        vietnamese_score = len(vietnamese_chars) * 2 + vietnamese_words
        english_score = english_words

        if vietnamese_score > english_score:
            return 'vietnamese'
        elif english_score > 0:
            return 'english'
        else:
            return 'mixed'
    except (AttributeError, TypeError) as e:
        print(f"⚠️ Language detection error: {e}")
        return 'unknown'


def extract_compound_words(text, language):
    """Extract compound words/phrases based on language"""
    compound_words_found = []

    if not text:
        return compound_words_found

    # Convert to lowercase for matching
    text_lower = text.lower()

    # Choose compound words dictionary based on language
    if language == 'vietnamese':
        compound_dict = VIETNAMESE_COMPOUND_WORDS
    elif language == 'english':
        compound_dict = ENGLISH_COMPOUND_WORDS
    else:
        # For mixed language, use both dictionaries
        compound_dict = VIETNAMESE_COMPOUND_WORDS.union(ENGLISH_COMPOUND_WORDS)

    # Sort compound words by length (longest first) to avoid partial matches
    sorted_compounds = sorted(compound_dict, key=len, reverse=True)

    for compound in sorted_compounds:
        # Use word boundaries to ensure we match complete phrases
        pattern = r'\b' + re.escape(compound) + r'\b'
        matches = re.findall(pattern, text_lower)
        if matches:
            compound_words_found.extend(matches)

    return compound_words_found


def preprocess_bilingual_text(text, language_hint=None):
    """Preprocess text for both Vietnamese and English"""
    if not text:
        return ""

    try:
        # Detect language if not provided
        if language_hint is None:
            language_hint = detect_language(text)

        # Remove URLs
        text = re.sub(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', '', text)

        # Remove mentions (but keep for hashtag processing)
        text = re.sub(r'@\w+', '', text)

        # Extract compound words first
        compound_words = extract_compound_words(text, language_hint)

        # Remove special characters but keep Vietnamese and English characters
        text = re.sub(r'[^\w\s\u00C0-\u024F\u1E00-\u1EFF]', ' ', text)

        # Remove extra whitespace
        text = ' '.join(text.split())

        # Convert to lowercase
        text = text.lower()

        return text, compound_words
    except (AttributeError, TypeError, re.error) as e:
        print(f"⚠️ Text preprocessing error: {e}")
        return ""


def extract_hashtags(texts):
    """Extract hashtags as potential keywords"""
    hashtags = []
    for text in texts:
        if not text:
            continue
        try:
            # Find hashtags (support both English and Vietnamese)
            tags = re.findall(r'#(\w+)', text, re.UNICODE)
            hashtags.extend(tags)
        except (AttributeError, TypeError, re.error) as e:
            print(f"⚠️ Hashtag extraction error: {e}")
            continue

    # Count hashtag frequency
    hashtag_counts = Counter(hashtags)
    return hashtag_counts.most_common()


def extract_bilingual_keywords_frequency(texts, top_n=20):
    """Frequency-based keyword extraction for both languages"""
    # Separate texts by language
    vietnamese_texts = []
    english_texts = []
    mixed_texts = []

    for text in texts:
        if not text:
            continue
        try:
            lang = detect_language(text)
            if lang == 'vietnamese':
                vietnamese_texts.append(text)
            elif lang == 'english':
                english_texts.append(text)
            else:
                mixed_texts.append(text)
        except (AttributeError, TypeError) as e:
            print(f"⚠️ Language classification error: {e}")
            mixed_texts.append(text)

    print(f"📊 Language distribution: VN={len(vietnamese_texts)}, EN={len(english_texts)}, Mixed={len(mixed_texts)}")

    all_keywords = []

    # Process each language group
    for lang, texts_group in [('vietnamese', vietnamese_texts), ('english', english_texts), ('mixed', mixed_texts)]:
        if not texts_group:
            continue

        try:
            # Extract compound words and single words
            all_compound_words = []
            all_single_words = []

            for text in texts_group:
                processed_text, compound_words = preprocess_bilingual_text(text, lang)

                # Add found compound words
                all_compound_words.extend(compound_words)

                # Extract meaningful single words (filtered)
                words = processed_text.split()
                meaningful_words = [
                    word for word in words
                    if (len(word) >= 4 and
                        word not in BILINGUAL_STOPWORDS and
                        word not in GENERIC_FILTER_WORDS)
                ]
                all_single_words.extend(meaningful_words)

            # Count frequencies
            compound_counts = Counter(all_compound_words)
            single_counts = Counter(all_single_words)

            # Add compound words (higher priority)
            for word, count in compound_counts.most_common(top_n // 3):
                all_keywords.append((word, count * 3, 'compound', lang))  # 3x weight for compounds

            # Add meaningful single words
            for word, count in single_counts.most_common(top_n // 3):
                # Skip if it's part of a compound word already found
                if not any(word in compound for compound, _, _, _ in all_keywords if compound):
                    all_keywords.append((word, count, 'single', lang))

        except (AttributeError, TypeError, ValueError) as e:
            print(f"⚠️ Phrase extraction error for {lang}: {e}")
            continue

    # Sort all keywords by frequency
    all_keywords.sort(key=lambda x: x[1], reverse=True)

    # Return top results with metadata
    return [(word, freq) for word, freq, word_type, lang in all_keywords[:top_n]]


def extract_keywords_keybert_bilingual(texts, top_n=10, per_text_top_k=10):
    """KeyBERT extraction optimized for bilingual content"""
    if kw_model is None:
        print("⚠️ KeyBERT model not available, skipping KeyBERT extraction")
        return []

    keybert_results = {}

    for text in texts[:300]:  # Limit for performance
        if not text or len(text.strip()) < 15:
            continue

        try:
            # Detect language and preprocess accordingly
            lang = detect_language(text)
            #processed_text = preprocess_bilingual_text(text, lang)
            # Use minimal preprocessing to preserve compound words
            clean_text = re.sub(r'http[s]?://\S+', '', text)  # Remove URLs
            clean_text = re.sub(r'@\w+', '', clean_text)      # Remove mentions
            clean_text = ' '.join(clean_text.split())         # Clean whitespace

            if len(clean_text.strip()) < 15:
                continue

            # Use different parameters based on language
            if lang == 'vietnamese':
                # Vietnamese works better with longer phrases
                ngram_range = (1, 4)
                diversity = 0.7
            elif lang == 'english':
                # English: standard + some longer phrases
                ngram_range = (1, 3)
                diversity = 0.6
            else:
                # Mixed: balanced approach
                ngram_range = (1, 3)
                diversity = 0.6

            keywords = kw_model.extract_keywords(
                clean_text,
                keyphrase_ngram_range=ngram_range,
                stop_words=list(BILINGUAL_STOPWORDS),
                top_n=per_text_top_k,
                use_mmr=True,
                diversity=diversity
            )

            for kw, score in keywords:
                # Filter out overly generic single words
                if len(kw.split()) == 1 and kw.lower() in GENERIC_FILTER_WORDS:
                    continue

                if kw in keybert_results:
                    keybert_results[kw] += score
                else:
                    keybert_results[kw] = score

        except (ValueError, AttributeError, TypeError, RuntimeError) as e:
            print(f"⚠️ KeyBERT extraction error: {e}")
            continue
        except Exception as e:
            # Catch any other unexpected errors from KeyBERT
            print(f"⚠️ Unexpected KeyBERT error: {e}")
            continue

    # Sort by score
    sorted_keywords = sorted(keybert_results.items(), key=lambda x: x[1], reverse=True)
    return sorted_keywords[:top_n]


def extract_keywords_hybrid_bilingual(texts, top_n=15):
    if not texts:
        return []

    # Method 1: Extract hashtags (universal for both languages)
    try:
        hashtag_counts = extract_hashtags(texts)
        print(f"📊 Found {len(hashtag_counts)} unique hashtags")
    except Exception as e:
        print(f"⚠️ Hashtag extraction failed: {e}")
        hashtag_counts = []

    # Method 2: Frequency-based extraction (language-aware)
    try:
        frequency_keywords = extract_bilingual_keywords_frequency(texts, top_n * 2)
        print(f"📊 Found {len(frequency_keywords)} frequency-based keywords")
    except Exception as e:
        print(f"⚠️ Frequency extraction failed: {e}")
        frequency_keywords = []

    # Method 3: KeyBERT extraction (multilingual)
    try:
        keybert_keywords = extract_keywords_keybert_bilingual(texts, top_n)
        print(f"📊 KeyBERT found {len(keybert_keywords)} keywords")
    except Exception as e:
        print(f"⚠️ KeyBERT extraction failed: {e}")
        keybert_keywords = []

    # Combine with weighted scoring
    combined_scores = {}

    # Add hashtags (high weight for social media relevance)
    for hashtag, count in hashtag_counts:
        combined_scores[f"#{hashtag}"] = count * 4

    # Add frequency-based keywords
    for word, count in frequency_keywords:
        weight = 4 if len(word.split()) > 1 else 2  # Higher weight for phrases
        if word in combined_scores:
            combined_scores[word] += count * weight
        else:
            combined_scores[word] = count * weight

    # Add KeyBERT results (convert scores to count-like numbers)
    for keyword, score in keybert_keywords:
        weight = 18 if len(keyword.split()) > 1 else 12  # Balanced weights
        if keyword in combined_scores:
            combined_scores[keyword] += score * weight
        else:
            combined_scores[keyword] = score * weight

    # Sort by combined score
    sorted_keywords = sorted(combined_scores.items(), key=lambda x: x[1], reverse=True)

    return sorted_keywords[:top_n]


def extract_keywords(texts, top_n=10, per_text_top_k=10, ngram_range=(1, 3)):
    counter = {}
    for text in texts:
        if not text.strip():
            continue
        keywords = kw_model.extract_keywords(
            text,
            keyphrase_ngram_range=ngram_range,
            stop_words=["english", "https"],
            top_n=per_text_top_k
        )
        for kw, _ in keywords:
            counter[kw] = counter.get(kw, 0) + 1
    return sorted(counter.items(), key=lambda x: x[1], reverse=True)[:top_n]


def run_keyword_analysis(top_n=10):
    """
    Analyze trending keywords from stored tweets
    Returns a dictionary with results for API consumption
    """
    try:
        mongo = MongoDBClient()
        texts = mongo.load_texts()
    except Exception as e:
        print(f"❌ Database connection error: {e}")
        return {
            "trending_keywords": [],
            "total_analyzed_texts": 0,
            "message": f"Database error: {e}",
            "error": True
        }

    if not texts:
        return {
            "trending_keywords": [],
            "total_analyzed_texts": 0,
            "message": "No tweets found in database"
        }

    # Use hybrid bilingual approach
    try:
        keywords = extract_keywords_hybrid_bilingual(texts, top_n)
    except Exception as e:
        print(f"❌ Keyword extraction error: {e}")
        return {
            "trending_keywords": [],
            "total_analyzed_texts": len(texts),
            "message": f"Keyword extraction failed: {e}",
            "error": True
        }

    print("Trending keywords:")
    for word, freq in keywords:
        print(f"{word}: {freq}")

    # Return the results for API response
    return {
        "trending_keywords": [
            {"keyword": word, "frequency": round(freq, 2) if isinstance(freq, float) else freq}
            for word, freq in keywords
        ],
        "total_analyzed_texts": len(texts),
        "message": f"Successfully analyzed {len(texts)} tweets"
    }
