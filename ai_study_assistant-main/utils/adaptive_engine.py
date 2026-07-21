"""
adaptive_engine.py — Adaptive learning engine.
Implements SM-2 spaced repetition algorithm and adaptive
quiz difficulty selection. Pure Python — no API calls.
"""

import math
from datetime import datetime, timedelta
from collections import defaultdict


# ─────────────────────────────────────────────
# 1. SM-2 SPACED REPETITION ALGORITHM
# ─────────────────────────────────────────────

def sm2_update(card_data, quality):
    """
    Implement the SM-2 spaced repetition algorithm.

    quality: 0-5 rating where:
        5 = perfect recall
        4 = correct with hesitation
        3 = correct with difficulty
        2 = incorrect but remembered on seeing answer
        1 = incorrect, easy answer
        0 = complete blackout

    Returns updated card data with new interval and easiness.
    """
    # Get current values or set defaults
    easiness = card_data.get("easiness", 2.5)
    interval = card_data.get("interval", 1)
    repetitions = card_data.get("repetitions", 0)

    if quality >= 3:
        # Correct response
        if repetitions == 0:
            interval = 1
        elif repetitions == 1:
            interval = 6
        else:
            interval = round(interval * easiness)

        repetitions += 1

        # Update easiness factor
        easiness = easiness + (
            0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02)
        )
        easiness = max(1.3, easiness)  # Minimum easiness

    else:
        # Incorrect response — reset
        repetitions = 0
        interval = 1

    next_review = datetime.now() + timedelta(days=interval)

    return {
        "easiness": round(easiness, 2),
        "interval": interval,
        "repetitions": repetitions,
        "next_review": next_review.isoformat(),
        "next_review_days": interval,
        "last_quality": quality,
        "last_reviewed": datetime.now().isoformat()
    }


def get_due_cards(flashcards):
    """
    Return cards that are due for review based on
    their next_review date. Implements spaced repetition
    scheduling — cards appear at optimal intervals.
    """
    due = []
    not_due = []
    now = datetime.now()

    for card in flashcards:
        next_review_str = card.get("next_review")
        if not next_review_str:
            due.append(card)
            continue

        try:
            next_review = datetime.fromisoformat(next_review_str)
            if next_review <= now:
                due.append(card)
            else:
                days_until = (next_review - now).days
                card["days_until_review"] = days_until
                not_due.append(card)
        except Exception:
            due.append(card)

    return {
        "due": due,
        "not_due": not_due,
        "due_count": len(due),
        "upcoming_count": len(not_due)
    }


def prioritise_flashcards(flashcards, confidence_ratings):
    """
    Reprioritise flashcards based on user confidence ratings.
    Low confidence cards appear more frequently.

    confidence_ratings: dict of {card_index: rating (1-5)}
    """
    prioritised = []

    for i, card in enumerate(flashcards):
        confidence = confidence_ratings.get(i, 3)

        # Lower confidence = higher priority (appears more)
        if confidence <= 2:
            priority = "high"
            repetitions = 3
        elif confidence == 3:
            priority = "medium"
            repetitions = 2
        else:
            priority = "low"
            repetitions = 1

        for _ in range(repetitions):
            card_copy = card.copy()
            card_copy["priority"] = priority
            card_copy["confidence"] = confidence
            prioritised.append(card_copy)

    # Shuffle to mix priorities
    import random
    random.shuffle(prioritised)

    return prioritised


# ─────────────────────────────────────────────
# 2. ADAPTIVE QUIZ DIFFICULTY ENGINE
# ─────────────────────────────────────────────

def calculate_student_level(quiz_history):
    """
    Calculate student's current knowledge level
    based on past quiz performance.

    Returns: "beginner", "intermediate", or "advanced"
    """
    if not quiz_history:
        return "intermediate"

    # Use last 3 quiz attempts
    recent = quiz_history[-3:]
    avg_score = sum(q.get("percentage", 50) for q in recent) / len(recent)

    if avg_score >= 75:
        return "advanced"
    elif avg_score >= 50:
        return "intermediate"
    else:
        return "beginner"


def get_adaptive_difficulty_prompt(student_level, weak_topics=None):
    """
    Generate a difficulty-adjusted prompt modifier
    based on student level. Used to guide Gemini
    to generate appropriately difficult questions.
    """
    if student_level == "beginner":
        difficulty_instruction = """
        Generate questions at EASY difficulty:
        - Focus on Remember and Understand levels of Bloom's taxonomy
        - Ask about definitions, basic facts and simple concepts
        - Use straightforward language
        - Avoid complex multi-step reasoning
        """
    elif student_level == "advanced":
        difficulty_instruction = """
        Generate questions at HARD difficulty:
        - Focus on Analyse, Evaluate and Create levels of Bloom's taxonomy
        - Ask about relationships between concepts, applications and implications
        - Include questions requiring multi-step reasoning
        - Challenge students to evaluate and critique ideas
        """
    else:
        difficulty_instruction = """
        Generate questions at MEDIUM difficulty:
        - Mix of Remember, Understand and Apply levels
        - Balance factual and conceptual questions
        - Include some application-based scenarios
        """

    weak_topics_instruction = ""
    if weak_topics:
        weak_topics_instruction = f"""
        Pay special attention to these topics where the student is weak:
        {', '.join(weak_topics)}
        Include at least 2-3 questions on these topics.
        """

    return difficulty_instruction + weak_topics_instruction


def detect_knowledge_gaps(quiz_history, flashcard_history):
    """
    Detect knowledge gaps by analysing quiz and
    flashcard performance across sessions.
    Returns topics and Bloom's levels where student struggles.
    """
    weak_blooms = defaultdict(list)
    weak_topics = []

    # Analyse quiz history
    for quiz in quiz_history:
        blooms_performance = quiz.get("blooms_distribution", {})
        for level, data in blooms_performance.items():
            if isinstance(data, dict):
                pct = data.get("percentage", 100)
            else:
                pct = 100
            weak_blooms[level].append(pct)

    # Find consistently weak Bloom's levels
    weak_blooms_levels = []
    for level, scores in weak_blooms.items():
        avg = sum(scores) / len(scores)
        if avg < 60:
            weak_blooms_levels.append({
                "level": level,
                "avg_score": round(avg, 1)
            })

    # Analyse flashcard confidence
    low_confidence_topics = []
    for card in flashcard_history:
        confidence = card.get("confidence", 3)
        if confidence <= 2:
            topic = card.get("blooms_level", "Unknown")
            low_confidence_topics.append(topic)

    return {
        "weak_blooms_levels": weak_blooms_levels,
        "low_confidence_topics": low_confidence_topics,
        "has_gaps": len(weak_blooms_levels) > 0 or len(
            low_confidence_topics
        ) > 0
    }


# ─────────────────────────────────────────────
# 3. STUDY PLAN GENERATOR
# ─────────────────────────────────────────────

def generate_study_plan(
    topic_segments, keywords, readability_level,
    student_level, days=7
):
    """
    Generate a personalised day-by-day study plan
    based on document analysis and student level.
    Pure Python — no API needed.
    """
    plan = []
    total_segments = len(topic_segments)

    # Adjust pacing based on student level and readability
    if student_level == "beginner" or readability_level in [
        "Very Difficult", "Difficult"
    ]:
        review_frequency = 2  # Review every 2 days
    else:
        review_frequency = 3  # Review every 3 days

    for day in range(1, days + 1):
        activities = []

        # Assign topic segments across the week
        if day <= total_segments:
            segment = topic_segments[day - 1]
            segment_keywords = segment.get("keywords", keywords[:5])

            activities.append({
                "type": "Study",
                "description": f"Study Topic {day}: "
                               f"{', '.join(segment_keywords[:3])}",
                "duration": "30-45 minutes",
                "icon": "📖"
            })

            activities.append({
                "type": "Flashcards",
                "description": "Generate and review flashcards for today's topic",
                "duration": "15-20 minutes",
                "icon": "🃏"
            })

        elif day % review_frequency == 0:
            activities.append({
                "type": "Review",
                "description": "Spaced repetition review of due flashcards",
                "duration": "20 minutes",
                "icon": "🔄"
            })

            activities.append({
                "type": "Quiz",
                "description": "Take an adaptive quiz on all covered material",
                "duration": "15 minutes",
                "icon": "✅"
            })
        else:
            activities.append({
                "type": "Practice",
                "description": "Review weak areas identified from previous quizzes",
                "duration": "25 minutes",
                "icon": "🎯"
            })

        # Add a tip based on student level
        if student_level == "beginner":
            tip = "Focus on understanding definitions before moving on."
        elif student_level == "advanced":
            tip = "Try to connect concepts across different sections."
        else:
            tip = "Test yourself before reviewing your notes."

        plan.append({
            "day": day,
            "activities": activities,
            "tip": tip,
            "estimated_time": sum_durations(activities)
        })

    return plan


def sum_durations(activities):
    """Estimate total study time for a day's activities."""
    total_min = 0
    for activity in activities:
        duration = activity.get("duration", "20 minutes")
        try:
            nums = [
                int(n) for n in duration.replace("-", " ").split()
                if n.isdigit()
            ]
            if nums:
                total_min += sum(nums) // len(nums)
        except Exception:
            total_min += 20
    return f"{total_min} minutes"


# ─────────────────────────────────────────────
# 4. PERFORMANCE ANALYTICS
# ─────────────────────────────────────────────

def calculate_learning_velocity(quiz_history):
    """
    Calculate how quickly the student is improving
    across quiz attempts. Returns trend and velocity.
    """
    if len(quiz_history) < 2:
        return {
            "trend": "insufficient_data",
            "velocity": 0,
            "message": "Complete at least 2 quizzes to see your progress trend."
        }

    scores = [q.get("percentage", 0) for q in quiz_history]

    # Calculate velocity as average improvement per session
    improvements = [
        scores[i + 1] - scores[i]
        for i in range(len(scores) - 1)
    ]
    velocity = sum(improvements) / len(improvements)

    if velocity > 5:
        trend = "improving"
        message = f"Great progress! You are improving by {abs(round(velocity, 1))}% per session."
    elif velocity < -5:
        trend = "declining"
        message = f"Your scores have dropped by {abs(round(velocity, 1))}% per session. Focus on review."
    else:
        trend = "stable"
        message = "Your performance is consistent. Try harder questions to challenge yourself."

    return {
        "trend": trend,
        "velocity": round(velocity, 2),
        "scores": scores,
        "message": message,
        "best_score": max(scores),
        "latest_score": scores[-1],
        "improvement": round(scores[-1] - scores[0], 1)
    }


def calculate_retention_rate(flashcard_sessions):
    """
    Calculate flashcard retention rate across sessions.
    Based on SM-2 algorithm performance.
    """
    if not flashcard_sessions:
        return {
            "retention_rate": 0,
            "message": "No flashcard data yet."
        }

    high_confidence = sum(
        1 for card in flashcard_sessions
        if card.get("confidence", 0) >= 4
    )
    total = len(flashcard_sessions)
    retention = round(high_confidence / total * 100, 1) if total > 0 else 0

    if retention >= 80:
        message = "Excellent retention! Your spaced repetition is working well."
    elif retention >= 60:
        message = "Good retention. Keep reviewing cards on schedule."
    else:
        message = "Low retention. Increase your review frequency."

    return {
        "retention_rate": retention,
        "high_confidence_cards": high_confidence,
        "total_cards": total,
        "message": message
    }
