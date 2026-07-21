"""
local_nlp.py — Original AI/NLP work done entirely locally.
No API calls. All processing happens on the server using
scikit-learn, NLTK and pure Python algorithms.
"""

import re
import math
from collections import Counter, defaultdict
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np
import nltk

# Download required NLTK data silently
for resource in ['punkt', 'punkt_tab', 'stopwords']:
    try:
        nltk.data.find(f'tokenizers/{resource}')
    except LookupError:
        try:
            nltk.data.find(f'corpora/{resource}')
        except LookupError:
            nltk.download(resource, quiet=True)

from nltk.tokenize import sent_tokenize, word_tokenize
from nltk.corpus import stopwords


# ─────────────────────────────────────────────
# 1. EXTRACTIVE SUMMARISATION
# ─────────────────────────────────────────────

def extractive_summarise(text, num_sentences=5):
    """
    Perform extractive summarisation entirely locally using TF-IDF
    sentence scoring. No API call required.

    Algorithm:
    1. Tokenise text into sentences
    2. Build TF-IDF matrix across all sentences
    3. Score each sentence by its average TF-IDF weight
    4. Return top N sentences in original order
    """
    sentences = sent_tokenize(text)

    if len(sentences) <= num_sentences:
        return {
            "sentences": sentences,
            "scores": [1.0] * len(sentences),
            "summary": text
        }

    try:
        vectorizer = TfidfVectorizer(
            stop_words='english',
            ngram_range=(1, 2),
            max_features=500
        )
        tfidf_matrix = vectorizer.fit_transform(sentences)

        # Score each sentence by sum of its TF-IDF weights
        sentence_scores = np.array(
            tfidf_matrix.sum(axis=1)
        ).flatten()

        # Normalise scores to 0-1
        max_score = sentence_scores.max()
        if max_score > 0:
            sentence_scores = sentence_scores / max_score

        # Get top N sentence indices in original order
        top_indices = sorted(
            np.argsort(sentence_scores)[-num_sentences:].tolist()
        )

        top_sentences = [sentences[i] for i in top_indices]
        scores = [float(sentence_scores[i]) for i in top_indices]

        return {
            "sentences": top_sentences,
            "scores": scores,
            "summary": " ".join(top_sentences),
            "all_scores": sentence_scores.tolist(),
            "total_sentences": len(sentences)
        }

    except Exception as e:
        return {
            "sentences": sentences[:num_sentences],
            "scores": [1.0] * num_sentences,
            "summary": " ".join(sentences[:num_sentences])
        }


# ─────────────────────────────────────────────
# 2. LOCAL Q&A RETRIEVAL ENGINE
# ─────────────────────────────────────────────

def build_knowledge_base(text):
    """
    Build a local TF-IDF knowledge base from the document.
    This enables question answering without any API call.
    """
    sentences = sent_tokenize(text)

    # Group sentences into overlapping passages of 3 sentences
    passages = []
    for i in range(len(sentences)):
        passage = " ".join(sentences[max(0, i-1):i+2])
        passages.append(passage)

    if not passages:
        return None

    try:
        vectorizer = TfidfVectorizer(
            stop_words='english',
            ngram_range=(1, 2),
            max_features=1000
        )
        tfidf_matrix = vectorizer.fit_transform(passages)

        return {
            "passages": passages,
            "vectorizer": vectorizer,
            "tfidf_matrix": tfidf_matrix,
            "sentences": sentences
        }
    except Exception:
        return None


def answer_question_locally(question, knowledge_base, top_k=3):
    """
    Answer a question by finding the most relevant passages
    using cosine similarity. Pure local computation — no API.

    Returns the top K most relevant passages and a confidence score.
    """
    if not knowledge_base:
        return None

    try:
        vectorizer = knowledge_base["vectorizer"]
        tfidf_matrix = knowledge_base["tfidf_matrix"]
        passages = knowledge_base["passages"]

        # Vectorise the question using the same vocabulary
        question_vector = vectorizer.transform([question])

        # Compute cosine similarity between question and all passages
        similarities = cosine_similarity(
            question_vector, tfidf_matrix
        )[0]

        # Get top K most similar passages
        top_indices = np.argsort(similarities)[-top_k:][::-1]

        results = []
        for idx in top_indices:
            if similarities[idx] > 0.05:  # Minimum relevance threshold
                results.append({
                    "passage": passages[idx],
                    "confidence": float(similarities[idx]),
                    "index": int(idx)
                })

        if not results:
            return {
                "found": False,
                "message": "No relevant information found in the document.",
                "passages": []
            }

        return {
            "found": True,
            "top_passage": results[0]["passage"],
            "confidence": results[0]["confidence"],
            "passages": results,
            "confidence_label": get_confidence_label(
                results[0]["confidence"]
            )
        }

    except Exception as e:
        return None


def get_confidence_label(score):
    """Convert numerical confidence to human-readable label."""
    if score >= 0.5:
        return "High confidence"
    elif score >= 0.2:
        return "Moderate confidence"
    elif score >= 0.05:
        return "Low confidence"
    else:
        return "Not found"


# ─────────────────────────────────────────────
# 3. CONCEPT EXTRACTION & CO-OCCURRENCE
# ─────────────────────────────────────────────

def extract_concepts(text, top_n=15):
    """
    Extract key concepts using TF-IDF and build a
    co-occurrence network. Entirely local processing.
    """
    stop_words = set(stopwords.words('english'))
    sentences = sent_tokenize(text)

    # Extract important terms using TF-IDF
    try:
        vectorizer = TfidfVectorizer(
            stop_words='english',
            ngram_range=(1, 2),
            max_features=200
        )
        tfidf_matrix = vectorizer.fit_transform(sentences)
        feature_names = vectorizer.get_feature_names_out()
        scores = np.array(
            tfidf_matrix.sum(axis=0)
        ).flatten()

        # Get top concepts
        top_indices = np.argsort(scores)[-top_n:][::-1]
        concepts = [
            {
                "term": feature_names[i],
                "score": float(scores[i]),
                "frequency": int(
                    text.lower().count(feature_names[i])
                )
            }
            for i in top_indices
        ]

    except Exception:
        # Fallback: simple word frequency
        words = word_tokenize(text.lower())
        words = [
            w for w in words
            if w.isalpha() and w not in stop_words and len(w) > 4
        ]
        freq = Counter(words)
        concepts = [
            {"term": w, "score": c, "frequency": c}
            for w, c in freq.most_common(top_n)
        ]

    # Build co-occurrence network
    cooccurrence = build_cooccurrence_network(
        sentences, [c["term"] for c in concepts[:10]]
    )

    return {
        "concepts": concepts,
        "cooccurrence": cooccurrence
    }


def build_cooccurrence_network(sentences, terms):
    """
    Build a co-occurrence network showing which concepts
    appear together in the same sentences.
    """
    cooccurrence = defaultdict(int)

    for sentence in sentences:
        sentence_lower = sentence.lower()
        present_terms = [
            t for t in terms if t in sentence_lower
        ]

        for i in range(len(present_terms)):
            for j in range(i + 1, len(present_terms)):
                pair = tuple(sorted([
                    present_terms[i], present_terms[j]
                ]))
                cooccurrence[pair] += 1

    return [
        {
            "term1": pair[0],
            "term2": pair[1],
            "strength": count
        }
        for pair, count in sorted(
            cooccurrence.items(),
            key=lambda x: x[1],
            reverse=True
        )[:15]
    ]


# ─────────────────────────────────────────────
# 4. SENTENCE IMPORTANCE SCORING
# ─────────────────────────────────────────────

def score_sentences(text):
    """
    Score every sentence in the document for importance.
    Uses TF-IDF weights + position weighting.
    Entirely local — no API.
    """
    sentences = sent_tokenize(text)
    if len(sentences) < 2:
        return []

    try:
        vectorizer = TfidfVectorizer(stop_words='english')
        tfidf_matrix = vectorizer.fit_transform(sentences)
        tfidf_scores = np.array(
            tfidf_matrix.sum(axis=1)
        ).flatten()

        # Normalise
        max_score = tfidf_scores.max()
        if max_score > 0:
            tfidf_scores = tfidf_scores / max_score

        # Position weighting — first and last sentences more important
        position_weights = []
        n = len(sentences)
        for i in range(n):
            if i < n * 0.2 or i > n * 0.8:
                position_weights.append(1.2)
            else:
                position_weights.append(1.0)

        # Combined score
        final_scores = [
            float(tfidf_scores[i]) * position_weights[i]
            for i in range(n)
        ]

        return [
            {
                "sentence": sentences[i],
                "score": final_scores[i],
                "position": i,
                "importance": get_importance_label(final_scores[i])
            }
            for i in range(n)
        ]

    except Exception:
        return [
            {
                "sentence": s,
                "score": 0.5,
                "position": i,
                "importance": "Medium"
            }
            for i, s in enumerate(sentences)
        ]


def get_importance_label(score):
    """Convert importance score to label."""
    if score >= 0.7:
        return "High"
    elif score >= 0.4:
        return "Medium"
    else:
        return "Low"


# ─────────────────────────────────────────────
# 5. TOPIC SEGMENTATION
# ─────────────────────────────────────────────

def segment_topics(text, num_topics=4):
    """
    Segment the document into topic sections using
    TF-IDF similarity between consecutive sentence groups.
    Detects topic shifts locally — no API needed.
    """
    sentences = sent_tokenize(text)

    if len(sentences) < num_topics * 2:
        return [{
            "topic_id": 1,
            "sentences": sentences,
            "keywords": extract_section_keywords(text)
        }]

    try:
        vectorizer = TfidfVectorizer(stop_words='english')
        tfidf_matrix = vectorizer.fit_transform(sentences)

        # Compute similarity between adjacent sentences
        similarities = []
        for i in range(len(sentences) - 1):
            sim = cosine_similarity(
                tfidf_matrix[i], tfidf_matrix[i + 1]
            )[0][0]
            similarities.append(float(sim))

        # Find topic boundaries where similarity drops
        boundary_size = len(sentences) // num_topics
        boundaries = [0]

        for i in range(boundary_size, len(similarities) - boundary_size, boundary_size):
            window = similarities[
                max(0, i - 2):min(len(similarities), i + 3)
            ]
            min_idx = window.index(min(window)) + max(0, i - 2)
            boundaries.append(min_idx + 1)

        boundaries.append(len(sentences))
        boundaries = sorted(list(set(boundaries)))

        # Build topic segments
        segments = []
        for i in range(len(boundaries) - 1):
            start = boundaries[i]
            end = boundaries[i + 1]
            segment_sentences = sentences[start:end]
            segment_text = " ".join(segment_sentences)

            segments.append({
                "topic_id": i + 1,
                "sentences": segment_sentences,
                "sentence_count": len(segment_sentences),
                "keywords": extract_section_keywords(segment_text),
                "start_sentence": start,
                "end_sentence": end
            })

        return segments

    except Exception:
        chunk_size = len(sentences) // num_topics
        segments = []
        for i in range(num_topics):
            start = i * chunk_size
            end = start + chunk_size if i < num_topics - 1 else len(sentences)
            segment_sentences = sentences[start:end]
            segments.append({
                "topic_id": i + 1,
                "sentences": segment_sentences,
                "sentence_count": len(segment_sentences),
                "keywords": [],
                "start_sentence": start,
                "end_sentence": end
            })
        return segments


def extract_section_keywords(text, top_n=5):
    """Extract keywords from a text section."""
    try:
        stop_words = set(stopwords.words('english'))
        words = word_tokenize(text.lower())
        words = [
            w for w in words
            if w.isalpha() and w not in stop_words and len(w) > 4
        ]
        freq = Counter(words)
        return [w for w, _ in freq.most_common(top_n)]
    except Exception:
        return []


# ─────────────────────────────────────────────
# 6. FULL LOCAL ANALYSIS PIPELINE
# ─────────────────────────────────────────────

def run_full_local_analysis(text):
    """
    Run the complete local NLP pipeline on a document.
    Returns all analysis results in one call.
    This is the core original AI work of the application.
    """
    results = {}

    # Step 1: Extractive summarisation
    results["extractive_summary"] = extractive_summarise(
        text, num_sentences=5
    )

    # Step 2: Build knowledge base for Q&A
    results["knowledge_base"] = build_knowledge_base(text)

    # Step 3: Concept extraction
    results["concepts"] = extract_concepts(text)

    # Step 4: Sentence importance scoring
    results["sentence_scores"] = score_sentences(text)

    # Step 5: Topic segmentation
    results["topic_segments"] = segment_topics(text)

    return results
