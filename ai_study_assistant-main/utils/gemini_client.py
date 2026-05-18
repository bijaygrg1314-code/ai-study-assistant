import os
import streamlit as st
from google import genai
from dotenv import load_dotenv
import json

load_dotenv()

def get_secret(key):
    try:
        return st.secrets[key]
    except:
        return os.getenv(key)

client = genai.Client(api_key=get_secret("GEMINI_API_KEY"))

def generate_summary(text):
    prompt = f"""
    You are an expert study assistant. Analyze the following study material and generate
    a comprehensive, well-structured summary.
    
    Study Material:
    {text[:4000]}
    
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
    try:
        response = client.models.generate_content(
            model="gemini-3.1-flash-lite-preview",
            contents=prompt
        )
        text_response = response.text.strip()
        text_response = text_response.replace("```json", "").replace("```", "").strip()
        result = json.loads(text_response)
        return result, None
    except Exception as e:
        return None, str(e)
    
def generate_flashcards(text):
    prompt = f"""
    You are an expert study assistant. Generate flashcards from the following study material.
    
    Study Material:
    {text[:4000]}
    
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
    Return only the JSON, no extra text.
    """
    try:
        response = client.models.generate_content(
            model="gemini-3.1-flash-lite-preview",
            contents=prompt
        )
        text_response = response.text.strip()
        text_response = text_response.replace("```json", "").replace("```", "").strip()
        result = json.loads(text_response)
        return result, None
    except Exception as e:
        return None, str(e)
    
def generate_quiz(text):
    prompt = f"""
    You are an expert study assistant. Generate a multiple choice quiz from the following study material.
    
    Study Material:
    {text[:4000]}
    
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
    Return only the JSON, no extra text.
    """
    try:
        response = client.models.generate_content(
            model="gemini-3.1-flash-lite-preview",
            contents=prompt
        )
        text_response = response.text.strip()
        text_response = text_response.replace("```json", "").replace("```", "").strip()
        result = json.loads(text_response)
        return result, None
    except Exception as e:
        return None, str(e)