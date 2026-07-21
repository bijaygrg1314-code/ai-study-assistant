import re
import math
from collections import Counter
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import textstat
import nltk

# Download required NLTK data
try:
    nltk.data.find('tokenizers/punkt')
except LookupError:
    nltk.download('punkt', quiet=True)

try:
    nltk.data.find('tokenizers/punkt_tab')
except LookupError:
    nltk.download('punkt_tab', quiet=True)

try:
    nltk.data.find('corpora/stopwords')
except LookupError:
    nltk.download('stopwords', quiet=True)

from nltk.tokenize import sent_tokenize, word_tokenize
from nltk.corpus import stopwords


def get_text_statistics(text):
    """Calculate comprehensive text statistics."""
    sentences = sent_tokenize(text)
    words = word_tokenize(text.lower())
    words_only = [w for w in words if w.isalpha()]

    word_count = len(words_only)
    sentence_count = len(sentences)
    avg_sentence_length = round(word_count / sentence_count, 1) if sentence_count > 0 else 0
    unique_words = len(set(words_only))
    vocabulary_richness = round(unique_words / word_count * 100, 1) if word_count > 0 else 0
    reading_time_minutes = round(word_count / 200, 1)

    return {
        "word_count": word_count,
        "sentence_count": sentence_count,
        "avg_sentence_length": avg_sentence_length,
        "unique_words": unique_words,
        "vocabulary_richness": vocabulary_richness,
        "reading_time_minutes": reading_time_minutes
    }


def get_readability_score(text):
    """Calculate readability using Flesch-Kincaid grade level."""
    try:
        fk_grade = textstat.flesch_kincaid_grade(text)
        flesch_ease = textstat.flesch_reading_ease(text)

        if flesch_ease >= 70:
            level = "Easy"
            description = "Suitable for general readers"
        elif flesch_ease >= 50:
            level = "Moderate"
            description = "Suitable for high school level"
        elif flesch_ease >= 30:
            level = "Difficult"
            description = "Suitable for university level"
        else:
            level = "Very Difficult"
            description = "Suitable for advanced academic level"

        return {
            "flesch_ease": round(flesch_ease, 1),
            "fk_grade": round(fk_grade, 1),
            "level": level,
            "description": description
        }
    except Exception:
        return {
            "flesch_ease": 0,
            "fk_grade": 0,
            "level": "Unknown",
            "description": "Could not calculate readability"
        }


def extract_keywords(text, top_n=10):
    """Extract top keywords using TF-IDF."""
    try:
        stop_words = set(stopwords.words('english'))
        sentences = sent_tokenize(text)

        if len(sentences) < 2:
            words = word_tokenize(text.lower())
            words_filtered = [w for w in words if w.isalpha() and w not in stop_words and len(w) > 3]
            freq = Counter(words_filtered)
            return [word for word, count in freq.most_common(top_n)]

        vectorizer = TfidfVectorizer(
            stop_words='english',
            max_features=50,
            ngram_range=(1, 2)
        )
        tfidf_matrix = vectorizer.fit_transform(sentences)
        feature_names = vectorizer.get_feature_names_out()
        scores = tfidf_matrix.sum(axis=0).A1
        keyword_scores = list(zip(feature_names, scores))
        keyword_scores.sort(key=lambda x: x[1], reverse=True)

        return [kw for kw, score in keyword_scores[:top_n]]
    except Exception:
        words = word_tokenize(text.lower())
        words_filtered = [w for w in words if w.isalpha() and len(w) > 4]
        freq = Counter(words_filtered)
        return [word for word, _ in freq.most_common(top_n)]


def chunk_text_by_similarity(text, max_chunk_size=15000):
    """
    Intelligently chunk text using TF-IDF cosine similarity.
    Groups similar sentences together into coherent chunks.
    """
    if len(text) <= max_chunk_size:
        return [text]

    sentences = sent_tokenize(text)

    if len(sentences) < 3:
        return [text[:max_chunk_size]]

    try:
        vectorizer = TfidfVectorizer(stop_words='english')
        tfidf_matrix = vectorizer.fit_transform(sentences)
        similarity_matrix = cosine_similarity(tfidf_matrix)

        chunks = []
        current_chunk = [sentences[0]]
        current_length = len(sentences[0])

        for i in range(1, len(sentences)):
            avg_similarity = similarity_matrix[i, max(0, i-3):i].mean()
            sentence_length = len(sentences[i])

            if current_length + sentence_length > max_chunk_size or avg_similarity < 0.1:
                if current_chunk:
                    chunks.append(' '.join(current_chunk))
                current_chunk = [sentences[i]]
                current_length = sentence_length
            else:
                current_chunk.append(sentences[i])
                current_length += sentence_length

        if current_chunk:
            chunks.append(' '.join(current_chunk))

        return chunks if chunks else [text[:max_chunk_size]]

    except Exception:
        chunk_size = max_chunk_size
        return [text[i:i+chunk_size] for i in range(0, len(text), chunk_size)]


def get_most_relevant_chunk(text, query_keywords, max_chunk_size=15000):
    """
    Find the most relevant chunk of text for a given set of keywords
    using TF-IDF cosine similarity.
    """
    chunks = chunk_text_by_similarity(text, max_chunk_size)

    if len(chunks) == 1:
        return chunks[0]

    try:
        query = ' '.join(query_keywords)
        all_texts = chunks + [query]

        vectorizer = TfidfVectorizer(stop_words='english')
        tfidf_matrix = vectorizer.fit_transform(all_texts)

        query_vector = tfidf_matrix[-1]
        chunk_vectors = tfidf_matrix[:-1]
        similarities = cosine_similarity(query_vector, chunk_vectors)[0]

        most_relevant_idx = similarities.argmax()
        return chunks[most_relevant_idx]

    except Exception:
        return chunks[0]


def preprocess_text(text):
    """
    Full preprocessing pipeline.
    Returns all analysis results in one call.
    """
    cleaned_text = re.sub(r'\s+', ' ', text).strip()
    cleaned_text = re.sub(r'[^\w\s\.\,\!\?\;\:\-\(\)]', '', cleaned_text)

    statistics = get_text_statistics(cleaned_text)
    readability = get_readability_score(cleaned_text)
    keywords = extract_keywords(cleaned_text)
    chunks = chunk_text_by_similarity(cleaned_text)

    return {
        "cleaned_text": cleaned_text,
        "statistics": statistics,
        "readability": readability,
        "keywords": keywords,
        "chunks": chunks,
        "chunk_count": len(chunks),
        "is_long_document": len(chunks) > 1
    }
