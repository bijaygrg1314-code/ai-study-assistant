import re
from collections import Counter


# Bloom's Taxonomy keyword mapping
BLOOMS_KEYWORDS = {
    "Remember": [
        "what", "who", "when", "where", "which", "define", "list",
        "name", "recall", "identify", "state", "recognise", "label"
    ],
    "Understand": [
        "explain", "describe", "summarise", "interpret", "classify",
        "compare", "discuss", "distinguish", "estimate", "predict"
    ],
    "Apply": [
        "how", "use", "apply", "demonstrate", "calculate", "solve",
        "implement", "construct", "produce", "show", "compute"
    ],
    "Analyse": [
        "why", "analyse", "examine", "differentiate", "relate",
        "break down", "contrast", "investigate", "determine", "conclude"
    ],
    "Evaluate": [
        "assess", "judge", "evaluate", "justify", "critique",
        "argue", "defend", "recommend", "select", "prioritise"
    ],
    "Create": [
        "design", "create", "develop", "formulate", "propose",
        "construct", "generate", "plan", "produce", "invent"
    ]
}

BLOOMS_COLORS = {
    "Remember": "🔵",
    "Understand": "🟢",
    "Apply": "🟡",
    "Analyse": "🟠",
    "Evaluate": "🔴",
    "Create": "🟣"
}

# Spaced repetition intervals in days
SPACED_REPETITION_INTERVALS = {
    "Easy": [1, 3, 7, 14, 30],
    "Medium": [1, 2, 4, 8, 16],
    "Hard": [1, 1, 2, 4, 8]
}


def classify_blooms_level(question_text):
    """
    Classify a question into Bloom's Taxonomy level
    based on keyword matching.
    """
    question_lower = question_text.lower()
    scores = {}

    for level, keywords in BLOOMS_KEYWORDS.items():
        score = sum(1 for kw in keywords if kw in question_lower)
        scores[level] = score

    best_level = max(scores, key=scores.get)

    if scores[best_level] == 0:
        if any(w in question_lower for w in ["what is", "what are", "which"]):
            best_level = "Remember"
        elif any(w in question_lower for w in ["how", "why"]):
            best_level = "Analyse"
        else:
            best_level = "Understand"

    return {
        "level": best_level,
        "emoji": BLOOMS_COLORS[best_level],
        "description": get_blooms_description(best_level)
    }


def get_blooms_description(level):
    """Return a short description of each Bloom's level."""
    descriptions = {
        "Remember": "Tests recall of facts and basic concepts",
        "Understand": "Tests comprehension and interpretation",
        "Apply": "Tests application of knowledge to situations",
        "Analyse": "Tests ability to break down and examine",
        "Evaluate": "Tests critical judgement and assessment",
        "Create": "Tests ability to produce something new"
    }
    return descriptions.get(level, "")


def calculate_difficulty(text, answer_text=""):
    """
    Calculate difficulty score of a question or flashcard.
    Based on word complexity, length and answer complexity.
    Returns Easy, Medium or Hard.
    """
    combined = text + " " + answer_text
    words = combined.split()
    total_words = len(words)

    long_words = sum(1 for w in words if len(w) > 7)
    long_word_ratio = long_words / total_words if total_words > 0 else 0

    sentences = re.split(r'[.!?]', combined)
    avg_sentence_length = total_words / len(sentences) if sentences else total_words

    technical_indicators = [
        "coefficient", "derivative", "integral", "hypothesis",
        "algorithm", "theorem", "equilibrium", "coefficient",
        "methodology", "implementation", "mechanism", "analysis",
        "synthesis", "evaluation", "correlation", "statistical"
    ]
    technical_count = sum(
        1 for indicator in technical_indicators
        if indicator in combined.lower()
    )

    difficulty_score = (
        (long_word_ratio * 40) +
        (min(avg_sentence_length / 30, 1) * 30) +
        (min(technical_count / 3, 1) * 30)
    )

    if difficulty_score < 30:
        return "Easy"
    elif difficulty_score < 60:
        return "Medium"
    else:
        return "Hard"


def get_spaced_repetition_schedule(difficulty):
    """
    Return recommended review intervals based on difficulty.
    Based on SM-2 spaced repetition algorithm principles.
    """
    intervals = SPACED_REPETITION_INTERVALS.get(difficulty, [1, 2, 4, 8, 16])
    return {
        "difficulty": difficulty,
        "next_review": intervals[0],
        "schedule": intervals,
        "description": f"Review again in {intervals[0]} day{'s' if intervals[0] > 1 else ''}"
    }


def process_flashcards(flashcards):
    """
    Post-process a list of flashcards.
    Adds difficulty, Bloom's level and spaced repetition schedule.
    """
    processed = []
    difficulty_counts = Counter()

    for card in flashcards:
        question = card.get("question", "")
        answer = card.get("answer", "")

        blooms = classify_blooms_level(question)
        difficulty = calculate_difficulty(question, answer)
        schedule = get_spaced_repetition_schedule(difficulty)
        difficulty_counts[difficulty] += 1

        processed.append({
            "question": question,
            "answer": answer,
            "blooms_level": blooms["level"],
            "blooms_emoji": blooms["emoji"],
            "blooms_description": blooms["description"],
            "difficulty": difficulty,
            "spaced_repetition": schedule
        })

    difficulty_summary = {
        "Easy": difficulty_counts["Easy"],
        "Medium": difficulty_counts["Medium"],
        "Hard": difficulty_counts["Hard"]
    }

    blooms_distribution = Counter(
        card["blooms_level"] for card in processed
    )

    return {
        "flashcards": processed,
        "difficulty_summary": dict(difficulty_summary),
        "blooms_distribution": dict(blooms_distribution),
        "total_cards": len(processed)
    }


def process_quiz_questions(questions):
    """
    Post-process quiz questions.
    Adds Bloom's taxonomy level and difficulty to each question.
    """
    processed = []
    blooms_counts = Counter()
    difficulty_counts = Counter()

    for q in questions:
        question_text = q.get("question", "")
        correct_answer = q.get("correct_answer", "")
        explanation = q.get("explanation", "")

        blooms = classify_blooms_level(question_text)
        difficulty = calculate_difficulty(question_text, correct_answer)

        blooms_counts[blooms["level"]] += 1
        difficulty_counts[difficulty] += 1

        processed.append({
            "question": question_text,
            "options": q.get("options", []),
            "correct_answer": correct_answer,
            "explanation": explanation,
            "blooms_level": blooms["level"],
            "blooms_emoji": blooms["emoji"],
            "blooms_description": blooms["description"],
            "difficulty": difficulty
        })

    return {
        "questions": processed,
        "blooms_distribution": dict(blooms_counts),
        "difficulty_distribution": dict(difficulty_counts),
        "total_questions": len(processed)
    }


def generate_performance_report(quiz_results, processed_questions):
    """
    Generate a detailed performance report after quiz submission.
    Shows breakdown by Bloom's level and difficulty.
    """
    correct_by_blooms = Counter()
    total_by_blooms = Counter()
    correct_by_difficulty = Counter()
    total_by_difficulty = Counter()

    for i, q in enumerate(processed_questions["questions"]):
        blooms = q["blooms_level"]
        difficulty = q["difficulty"]
        is_correct = quiz_results.get(i, False)

        total_by_blooms[blooms] += 1
        total_by_difficulty[difficulty] += 1

        if is_correct:
            correct_by_blooms[blooms] += 1
            correct_by_difficulty[difficulty] += 1

    blooms_performance = {}
    for level in total_by_blooms:
        total = total_by_blooms[level]
        correct = correct_by_blooms[level]
        blooms_performance[level] = {
            "correct": correct,
            "total": total,
            "percentage": round(correct / total * 100) if total > 0 else 0
        }

    difficulty_performance = {}
    for diff in total_by_difficulty:
        total = total_by_difficulty[diff]
        correct = correct_by_difficulty[diff]
        difficulty_performance[diff] = {
            "correct": correct,
            "total": total,
            "percentage": round(correct / total * 100) if total > 0 else 0
        }

    weakest_area = min(
        blooms_performance,
        key=lambda x: blooms_performance[x]["percentage"]
    ) if blooms_performance else None

    return {
        "blooms_performance": blooms_performance,
        "difficulty_performance": difficulty_performance,
        "weakest_area": weakest_area,
        "recommendation": get_study_recommendation(weakest_area)
    }


def get_study_recommendation(weakest_blooms_level):
    """Return a study recommendation based on weakest Bloom's area."""
    recommendations = {
        "Remember": "Focus on memorisation techniques — try flashcards and repetition.",
        "Understand": "Try explaining concepts in your own words to deepen understanding.",
        "Apply": "Practice with worked examples and problem-solving exercises.",
        "Analyse": "Break topics into components and look for patterns and relationships.",
        "Evaluate": "Practice critical thinking by comparing different viewpoints.",
        "Create": "Challenge yourself to design solutions or create summaries from scratch."
    }
    return recommendations.get(
        weakest_blooms_level,
        "Keep practising regularly using spaced repetition."
    )
