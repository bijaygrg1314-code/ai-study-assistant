from utils.supabase_client import supabase
from datetime import datetime
import json


def save_study_session(user_id, document_name, word_count, readability_level, keywords):
    """Save a new study session to the database."""
    try:
        # Ensure profile exists first
        existing = supabase.table("profiles")\
            .select("id")\
            .eq("id", user_id)\
            .execute()

        if not existing.data:
            print(f"DEBUG: Profile missing for {user_id} — skipping session save")
            return None, "Profile not found"

        response = supabase.table("study_sessions").insert({
            "user_id": user_id,
            "document_name": document_name,
            "document_word_count": word_count,
            "readability_level": readability_level,
            "keywords": keywords,
            "created_at": datetime.now().isoformat()
        }).execute()
        print(f"DEBUG: Session saved: {response.data[0]['id']}")
        return response.data[0]["id"], None
    except Exception as e:
        print(f"DEBUG: Session save failed {e}")
        return None, str(e)



def save_summary(user_id, session_id, summary_data):
    """Save a generated summary to the database."""
    try:
        supabase.table("summaries").insert({
            "session_id": session_id,
            "user_id": user_id,
            "title": summary_data.get("title", ""),
            "overview": summary_data.get("overview", ""),
            "key_points": summary_data.get("key_points", []),
            "conclusion": summary_data.get("conclusion", ""),
            "created_at": datetime.now().isoformat()
        }).execute()
        print(f"DEBUG: Summary saved for session {session_id}")
        return True, None
    except Exception as e:
        return False, str(e)


def save_flashcards(user_id, session_id, processed_flashcards):
    """Save generated flashcards to the database."""
    try:
        cards = processed_flashcards.get("flashcards", [])
        for card in cards:
            supabase.table("flashcards").insert({
                "session_id": session_id,
                "user_id": user_id,
                "question": card.get("question", ""),
                "answer": card.get("answer", ""),
                "difficulty": card.get("difficulty", "Medium"),
                "blooms_level": card.get("blooms_level", "Understand"),
                "next_review_days": card.get("spaced_repetition", {}).get("next_review", 1),
                "created_at": datetime.now().isoformat()
            }).execute()
        return True, None
    except Exception as e:
        return False, str(e)


def save_quiz_result(user_id, session_id, score, total, percentage, blooms_dist, difficulty_dist):
    """Save quiz results to the database."""
    try:
        supabase.table("quiz_results").insert({
            "session_id": session_id,
            "user_id": user_id,
            "score": score,
            "total_questions": total,
            "percentage": percentage,
            "blooms_distribution": json.dumps(blooms_dist),
            "difficulty_distribution": json.dumps(difficulty_dist),
            "created_at": datetime.now().isoformat()
        }).execute()
        return True, None
    except Exception as e:
        return False, str(e)


def get_user_sessions(user_id, limit=10):
    """Get a user's past study sessions."""
    try:
        response = supabase.table("study_sessions")\
            .select("*")\
            .eq("user_id", user_id)\
            .order("created_at", desc=True)\
            .limit(limit)\
            .execute()
        return response.data, None
    except Exception as e:
        return [], str(e)


def get_session_summary(session_id):
    """Get the summary for a specific session."""
    try:
        response = supabase.table("summaries")\
            .select("*")\
            .eq("session_id", session_id)\
            .execute()
        return response.data[0] if response.data else None, None
    except Exception as e:
        return None, str(e)


def get_session_flashcards(session_id):
    """Get flashcards for a specific session."""
    try:
        response = supabase.table("flashcards")\
            .select("*")\
            .eq("session_id", session_id)\
            .execute()
        return response.data, None
    except Exception as e:
        return [], str(e)


def get_user_stats(user_id):
    """Get overall stats for a user."""
    try:
        sessions = supabase.table("study_sessions")\
            .select("id")\
            .eq("user_id", user_id)\
            .execute()

        quiz_results = supabase.table("quiz_results")\
            .select("percentage")\
            .eq("user_id", user_id)\
            .execute()

        flashcards = supabase.table("flashcards")\
            .select("id")\
            .eq("user_id", user_id)\
            .execute()

        total_sessions = len(sessions.data)
        total_flashcards = len(flashcards.data)

        avg_quiz_score = 0
        if quiz_results.data:
            scores = [r["percentage"] for r in quiz_results.data]
            avg_quiz_score = round(sum(scores) / len(scores), 1)

        return {
            "total_sessions": total_sessions,
            "total_flashcards": total_flashcards,
            "avg_quiz_score": avg_quiz_score,
            "total_quizzes": len(quiz_results.data)
        }, None
    except Exception as e:
        return None, str(e)
