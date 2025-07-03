import os
import logging
from typing import List, Dict, Tuple, Optional, Any
import numpy as np
from collections import Counter
from datetime import datetime, timedelta
import warnings

logger = logging.getLogger(__name__)

try:
    from bertopic import BERTopic
    from sentence_transformers import SentenceTransformer
    from sklearn.feature_extraction.text import CountVectorizer

    BERTOPIC_AVAILABLE = True
    try:
        from bertopic.representation import KeyBERTInspired
        from bertopic.vectorizers import ClassTfidfTransformer

        BERTOPIC_ADVANCED = True
    except ImportError:
        BERTOPIC_ADVANCED = False
        logger.warning("BERTopic advanced features not available")
except ImportError:
    BERTOPIC_AVAILABLE = False
    BERTOPIC_ADVANCED = False
    logger.warning("BERTopic not available. Install with: pip install bertopic")


class TopicModelingService:
    """Service for topic modeling and keyword clustering using BERTopic"""

    def __init__(self,
                 embedding_model: str = "paraphrase-multilingual-MiniLM-L12-v2",
                 min_topic_size: int = 10,
                 nr_topics: Optional[int] = None):
        """Initialize the topic modeling service
        
        Args:
            embedding_model: Sentence transformer model for embeddings
            min_topic_size: Minimum cluster size for HDBSCAN
            nr_topics: Number of topics to reduce to (None for automatic)
        """
        self.embedding_model_name = embedding_model
        self.min_topic_size = min_topic_size
        self.nr_topics = nr_topics
        self.topic_model = None
        self._initialized = False

        # Import stopwords service
        try:
            from .stopwords_service import stopwords_service
            self.stopwords_service = stopwords_service
        except ImportError:
            self.stopwords_service = None
            logger.warning("Stopwords service not available")

    def initialize(self):
        """Initialize the BERTopic model"""
        if not BERTOPIC_AVAILABLE:
            logger.error("BERTopic is not available")
            return

        if self._initialized:
            return

        try:
            # Suppress the sklearn stopwords warning since we handle them correctly
            warnings.filterwarnings('ignore', 
                                  message='Your stop_words may be inconsistent with your preprocessing',
                                  category=UserWarning,
                                  module='sklearn')
            # Initialize embedding model
            embedding_model = SentenceTransformer(self.embedding_model_name)

            # Configure vectorizer with custom tokenizer for Vietnamese
            # Use a custom tokenizer that preserves Vietnamese diacritics
            import re
            def vietnamese_aware_tokenizer(text):
                # Simple tokenizer that preserves Vietnamese characters
                # Split on whitespace and punctuation, but preserve Vietnamese diacritics
                tokens = re.findall(r'\b[\w\u00C0-\u1EF9]+\b', text.lower())
                return tokens

            # Get stopwords
            stop_words_set = set()
            if self.stopwords_service:
                # Get all stopwords
                all_stopwords = self.stopwords_service.get_stopwords('both')
                # Process them through the same tokenizer to ensure consistency
                for word in all_stopwords:
                    # Tokenize each stopword using the same tokenizer
                    tokens = vietnamese_aware_tokenizer(word)
                    stop_words_set.update(tokens)
            
            # Create a custom analyzer that handles stopwords after tokenization
            def vietnamese_analyzer(text):
                tokens = vietnamese_aware_tokenizer(text)
                # Filter out stopwords
                return [token for token in tokens if token not in stop_words_set]

            vectorizer_model = CountVectorizer(
                analyzer=vietnamese_analyzer,
                ngram_range=(1, 3),
                min_df=2
            )

            # Configure representation model if available
            representation_model = None
            if BERTOPIC_ADVANCED:
                representation_model = KeyBERTInspired()

            # Initialize BERTopic with available features
            bertopic_params = {
                "embedding_model": embedding_model,
                "vectorizer_model": vectorizer_model,
                "min_topic_size": self.min_topic_size,
                "nr_topics": self.nr_topics,
                "calculate_probabilities": True,
                "verbose": False
            }

            if representation_model:
                bertopic_params["representation_model"] = representation_model

            self.topic_model = BERTopic(**bertopic_params)

            self._initialized = True
            logger.info("BERTopic initialized successfully")

        except Exception as e:
            logger.error(f"Failed to initialize BERTopic: {e}")
            self.topic_model = None

    def fit_transform(self, documents: List[str],
                      embeddings: Optional[np.ndarray] = None) -> Tuple[List[int], Optional[Any]]:
        """Fit the topic model and transform documents
        
        Args:
            documents: List of text documents
            embeddings: Pre-computed embeddings (optional)
            
        Returns:
            Tuple of (topics, probabilities)
        """
        if not self._initialized:
            self.initialize()

        if self.topic_model is None:
            return [], None

        try:
            topics, probs = self.topic_model.fit_transform(documents, embeddings)
            return topics, probs
        except Exception as e:
            logger.error(f"Topic modeling failed: {e}")
            return [], None

    def get_topics_with_keywords(self, num_words: int = 10) -> Dict[int, List[Tuple[str, float]]]:
        """Get topics with their top keywords
        
        Args:
            num_words: Number of words per topic
            
        Returns:
            Dictionary mapping topic_id to list of (word, score) tuples
        """
        if self.topic_model is None:
            return {}

        try:
            topics = self.topic_model.get_topics()
            result = {}

            for topic_id, words in topics.items():
                if topic_id != -1:  # Skip outlier topic
                    result[topic_id] = words[:num_words]

            return result
        except Exception as e:
            logger.error(f"Failed to get topics: {e}")
            return {}

    def get_topic_info(self) -> List[Dict[str, Any]]:
        """Get detailed information about all topics
        
        Returns:
            List of topic information dictionaries
        """
        if self.topic_model is None:
            return []

        try:
            topic_info = self.topic_model.get_topic_info()

            # Convert to list of dicts
            result = []
            for _, row in topic_info.iterrows():
                if row['Topic'] != -1:  # Skip outlier topic
                    result.append({
                        'topic_id': int(row['Topic']),
                        'count': int(row['Count']),
                        'name': row.get('Name', f"Topic {row['Topic']}"),
                        'representative_docs': row.get('Representative_Docs', [])[:3]
                    })

            return result
        except Exception as e:
            logger.error(f"Failed to get topic info: {e}")
            return []

    def extract_trending_topics(self, documents: List[str],
                                timestamps: Optional[List[datetime]] = None,
                                window_days: int = 7,
                                top_n: int = 10) -> List[Dict[str, Any]]:
        """Extract trending topics from documents
        
        Args:
            documents: List of text documents
            timestamps: Document timestamps (uses current time if None)
            window_days: Time window for trend analysis
            top_n: Number of top trending topics
            
        Returns:
            List of trending topics with metadata
        """
        if not documents:
            return []

        # Initialize if needed
        if not self._initialized:
            self.initialize()

        if self.topic_model is None:
            return []

        try:
            # Fit the model
            topics, probs = self.fit_transform(documents)

            # Get topic information
            topics_info = self.get_topics_with_keywords()

            # If timestamps provided, analyze temporal trends
            if timestamps and len(timestamps) == len(documents):
                # Group documents by time window
                now = datetime.now()
                cutoff = now - timedelta(days=window_days)

                recent_topics = []
                for i, (topic, timestamp) in enumerate(zip(topics, timestamps)):
                    if timestamp >= cutoff and topic != -1:
                        recent_topics.append(topic)

                # Count topic frequencies in recent window
                topic_counts = Counter(recent_topics)
            else:
                # Count all topics
                topic_counts = Counter([t for t in topics if t != -1])

            # Build trending topics list
            trending = []
            for topic_id, count in topic_counts.most_common(top_n):
                if topic_id in topics_info:
                    keywords = topics_info[topic_id]
                    trending.append({
                        'topic_id': topic_id,
                        'frequency': count,
                        'keywords': [{'word': word, 'score': float(score)}
                                     for word, score in keywords[:5]],
                        'top_words': [word for word, _ in keywords[:3]]
                    })

            return trending

        except Exception as e:
            logger.error(f"Failed to extract trending topics: {e}")
            return []

    def find_topics(self, search_term: str, top_n: int = 5) -> List[Tuple[int, float]]:
        """Find topics most similar to a search term
        
        Args:
            search_term: Term to search for
            top_n: Number of similar topics to return
            
        Returns:
            List of (topic_id, similarity_score) tuples
        """
        if self.topic_model is None:
            return []

        try:
            similar_topics, similarity = self.topic_model.find_topics(search_term, top_n=top_n)
            return list(zip(similar_topics, similarity))
        except Exception as e:
            logger.error(f"Failed to find similar topics: {e}")
            return []

    def update_topics(self, documents: List[str], topics: List[int]) -> bool:
        """Update topic model with new documents
        
        Args:
            documents: New documents
            topics: Topics for the new documents
            
        Returns:
            Success status
        """
        if self.topic_model is None:
            return False

        try:
            self.topic_model.update_topics(documents, topics=topics)
            return True
        except Exception as e:
            logger.error(f"Failed to update topics: {e}")
            return False

    def visualize_topics(self) -> Optional[str]:
        """Generate topic visualization HTML
        
        Returns:
            HTML string for visualization or None
        """
        if self.topic_model is None:
            return None

        try:
            fig = self.topic_model.visualize_topics()
            return fig.to_html()
        except Exception as e:
            logger.error(f"Failed to visualize topics: {e}")
            return None

    def save_model(self, path: str):
        """Save the topic model to disk
        
        Args:
            path: Path to save the model
        """
        if self.topic_model is None:
            logger.warning("No model to save")
            return

        try:
            self.topic_model.save(path)
            logger.info(f"Topic model saved to {path}")
        except Exception as e:
            logger.error(f"Failed to save model: {e}")

    def load_model(self, path: str):
        """Load a topic model from disk
        
        Args:
            path: Path to load the model from
        """
        if not BERTOPIC_AVAILABLE:
            logger.error("BERTopic is not available")
            return

        try:
            self.topic_model = BERTopic.load(path)
            self._initialized = True
            logger.info(f"Topic model loaded from {path}")
        except Exception as e:
            logger.error(f"Failed to load model: {e}")


# Singleton instance
topic_modeling_service = TopicModelingService()
