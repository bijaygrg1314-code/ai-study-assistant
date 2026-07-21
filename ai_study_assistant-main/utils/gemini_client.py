import os
import json
import time
import streamlit as st
from google import genai
from dotenv import load_dotenv
from utils.preprocessor import get_most_relevant_chunk, extract_keywords

load_dotenv()


def get_secret(key):
    try:
        return st.secrets[key]
    except Exception:
        return os.getenv(key)


def get_client():
    """Create and return a Gemini client."""
    api_key = get_secret("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY not found in secrets or environment variables.")
    return genai.Client(api_key=api_key)


def call_gemini_with_retry(prompt, max_retries=3):
    """
    Call Gemini API with automatic retry logic.
    Handles 403, 429 and 503 errors gracefully.
    """
    client = get_client()
    last_error = None

    for attempt in range(max_retries):
        try:
            response = client.models.generate_content(
                model="gemini-3.1-flash-lite",
                contents=prompt
            )
            text = response.text.strip()
            text = text.replace("```json", "").replace("```", "").strip()
            return text, None

        except Exception as e:
            last_error = str(e)
            error_lower = last_error.lower()

            if "403" in last_error or "permission_denied" in error_lower:
                return None, "API access denied. Please check your Gemini API key in the app settings."

            elif "429" in last_error or "resource_exhausted" in error_lower:
                if attempt < max_retries - 1:
                    wait_time = (attempt + 1) * 10
                    time.sleep(wait_time)
                    continue
                return None, "The AI service is currently busy. Please wait a moment and try again."

            elif "503" in last_error or "unavailable" in error_lower:
                if attempt < max_retries - 1:
                    wait_time = (attempt + 1) * 5
                    time.sleep(wait_time)
                    continue
                return None, "The AI service is temporarily unavailable. Please try again in a few minutes."

            else:
                if attempt < max_retries - 1:
                    time.sleep(3)
                    continue
                return None, f"An unexpected error occurred. Please try again."

    return None, f"Failed after {max_retries} attempts. Please try again later."


def generate_summary(text):
    """Generate a structured summary with preprocessing."""
    try:
        keywords = extract_keywords(text, top_n=5)
        relevant_text = get_most_relevant_chunk(text, keywords, max_chunk_size=15000)

        prompt = f"""
        You are an expert study assistant. Analyse the following study material and generate
        a comprehensive, well-structured summary.

        Study Material:
        {relevant_text}

        Return ONLY a valid JSON object with exactly these fields:
        {{
            "title": "A suitable title for this study material",
            "overview": "A 2-3 sentence overview of the entire material",
            "key_points": ["5-8 key points from the material, each as a clear sentence"],
            "important_terms": [
                {{"term": "term name", "definition": "clear definition"}}
            ],
            "conclusion": "A 1-2 sentence conclusion summarizing the most important takeaway"
        }}

        Return only the JSON, no extra text.
        """

        raw_text, error = call_gemini_with_retry(prompt)
        if error:
            return None, error

        result = json.loads(raw_text)
        return result, None

    except json.JSONDecodeError:
        return None, "The AI returned an unexpected response. Please try again."
    except Exception as e:
        return None, f"An error occurred during summary generation. Please try again."


def generate_flashcards(text):
    """Generate flashcards with preprocessing."""
    try:
        keywords = extract_keywords(text, top_n=5)
        relevant_text = get_most_relevant_chunk(text, keywords, max_chunk_size=15000)

        prompt = f"""
        You are an expert study assistant. Generate flashcards from the following study material.

        Study Material:
        {relevant_text}

        Return ONLY a valid JSON object with exactly this structure:
        {{
            "flashcards": [
                {{
                    "question": "A clear, specific question",
                    "answer": "A concise, accurate answer"
                }}
            ]
        }}

        Generate between 8-12 flashcards covering the most important concepts.
        Make questions specific and answers concise but complete.
        Vary the question types — include definition, application and conceptual questions.
        Return only the JSON, no extra text.
        """

        raw_text, error = call_gemini_with_retry(prompt)
        if error:
            return None, error

        result = json.loads(raw_text)
        return result, None

    except json.JSONDecodeError:
        return None, "The AI returned an unexpected response. Please try again."
    except Exception as e:
        return None, f"An error occurred during flashcard generation. Please try again."


def generate_quiz(text):
    """Generate quiz questions with preprocessing."""
    try:
        keywords = extract_keywords(text, top_n=5)
        relevant_text = get_most_relevant_chunk(text, keywords, max_chunk_size=15000)

        prompt = f"""
        You are an expert study assistant. Generate a multiple choice quiz from the following study material.

        Study Material:
        {relevant_text}

        Return ONLY a valid JSON object with exactly this structure:
        {{
            "quiz": [
                {{
                    "question": "A clear question",
                    "options": ["A) option1", "B) option2", "C) option3", "D) option4"],
                    "correct_answer": "A) option1",
                    "explanation": "Brief explanation of why this is correct"
                }}
            ]
        }}

        Generate exactly 8 questions.
        Make sure correct_answer exactly matches one of the options.
        Cover different topics from the material.
        Include a mix of difficulty levels.
        Return only the JSON, no extra text.
        """

        raw_text, error = call_gemini_with_retry(prompt)
        if error:
            return None, error

        result = json.loads(raw_text)
        return result, None

    except json.JSONDecodeError:
        return None, "The AI returned an unexpected response. Please try again."
    except Exception as e:
        return None, f"An error occurred during quiz generation. Please try again."


def generate_resource_recommendations(keywords, topic_title):
    """
    Generate study resource recommendations based on keywords.
    Uses free URL construction — no additional API needed.
    """
    try:
        search_query = "+".join(keywords[:3])
        topic_encoded = topic_title.replace(" ", "+")

        resources = {
            "wikipedia": {
                "name": "Wikipedia",
                "url": f"https://en.wikipedia.org/wiki/Special:Search?search={search_query}",
                "description": "Free encyclopaedia articles on the topic",
                "icon": "📖"
            },
            "khan_academy": {
                "name": "Khan Academy",
                "url": f"https://www.khanacademy.org/search?search_again=1&page_search_query={search_query}",
                "description": "Free educational videos and exercises",
                "icon": "🎓"
            },
            "google_scholar": {
                "name": "Google Scholar",
                "url": f"https://scholar.google.com/scholar?q={search_query}",
                "description": "Academic research papers and articles",
                "icon": "🔬"
            },
            "youtube": {
                "name": "YouTube Educational",
                "url": f"https://www.youtube.com/results?search_query={search_query}+tutorial+explained",
                "description": "Video explanations and tutorials",
                "icon": "▶️"
            },
            "coursera": {
                "name": "Coursera",
                "url": f"https://www.coursera.org/search?query={search_query}",
                "description": "Online courses from top universities",
                "icon": "🏫"
            }
        }

        return resources, None

    except Exception as e:
        return None, "Could not generate recommendations."
