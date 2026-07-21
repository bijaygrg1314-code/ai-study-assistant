"""
analytics.py — Learning Analytics Dashboard.
Shows progress tracking, knowledge gaps, learning velocity
and study recommendations. All computed locally.
"""

import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
from utils.adaptive_engine import (
    calculate_learning_velocity,
    calculate_retention_rate,
    detect_knowledge_gaps,
    generate_study_plan,
    calculate_student_level
)
from utils.local_nlp import segment_topics
from utils.session_manager import (
    get_user_sessions,
    get_user_stats
)
from utils.supabase_client import supabase
from datetime import datetime


def get_user_quiz_history(user_id):
    """Fetch all quiz results for a user."""
    try:
        response = supabase.table("quiz_results")\
            .select("*")\
            .eq("user_id", user_id)\
            .order("created_at", desc=False)\
            .execute()
        return response.data or []
    except Exception:
        return []


def get_user_flashcard_history(user_id):
    """Fetch all flashcards for a user."""
    try:
        response = supabase.table("flashcards")\
            .select("*")\
            .eq("user_id", user_id)\
            .execute()
        return response.data or []
    except Exception:
        return []


def show_analytics_page(user=None):
    st.title("📊 Learning Analytics Dashboard")
    st.write(
        "Track your progress, identify knowledge gaps and "
        "get personalised study recommendations."
    )

    if not user:
        st.warning(
            "⚠️ Please sign in to access your learning analytics. "
            "Guest mode does not save session data."
        )
        return

    # Fetch all user data
    quiz_history = get_user_quiz_history(user.id)
    flashcard_history = get_user_flashcard_history(user.id)
    stats, _ = get_user_stats(user.id)
    sessions, _ = get_user_sessions(user.id, limit=20)

    # ── Overview Metrics ──
    st.subheader("📈 Overview")
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric(
            "Study Sessions",
            stats["total_sessions"] if stats else 0
        )
    with col2:
        st.metric(
            "Quizzes Taken",
            stats["total_quizzes"] if stats else 0
        )
    with col3:
        st.metric(
            "Flashcards Created",
            stats["total_flashcards"] if stats else 0
        )
    with col4:
        st.metric(
            "Avg Quiz Score",
            f"{stats['avg_quiz_score']}%" if stats else "N/A"
        )

    if not quiz_history and not flashcard_history:
        st.divider()
        st.info(
            "📚 No study data yet. Complete some quizzes and "
            "flashcard sessions to see your analytics here!"
        )
        show_empty_state_tips()
        return

    st.divider()

    # ── Quiz Performance Over Time ──
    if quiz_history:
        st.subheader("📉 Quiz Performance Over Time")

        quiz_df = pd.DataFrame([
            {
                "Session": i + 1,
                "Score (%)": q.get("percentage", 0),
                "Date": datetime.fromisoformat(
                    q["created_at"]
                ).strftime("%b %d") if q.get("created_at") else f"Session {i+1}"
            }
            for i, q in enumerate(quiz_history)
        ])

        fig = px.line(
            quiz_df,
            x="Session",
            y="Score (%)",
            markers=True,
            title="Your Quiz Scores Over Time",
            color_discrete_sequence=["#2563EB"]
        )
        fig.update_layout(
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            yaxis_range=[0, 100],
            font=dict(color="white")
        )
        fig.add_hline(
            y=70,
            line_dash="dash",
            line_color="green",
            annotation_text="Pass threshold (70%)"
        )
        st.plotly_chart(fig, use_container_width=True)

        # Learning velocity
        velocity = calculate_learning_velocity(quiz_history)
        col1, col2, col3 = st.columns(3)
        with col1:
            trend_emoji = {
                "improving": "📈",
                "declining": "📉",
                "stable": "➡️",
                "insufficient_data": "❓"
            }.get(velocity["trend"], "❓")
            st.metric(
                "Progress Trend",
                f"{trend_emoji} {velocity['trend'].title()}"
            )
        with col2:
            st.metric(
                "Best Score",
                f"{velocity.get('best_score', 0)}%"
            )
        with col3:
            improvement = velocity.get("improvement", 0)
            st.metric(
                "Overall Improvement",
                f"{'+' if improvement >= 0 else ''}{improvement}%"
            )

        st.info(f"💡 {velocity['message']}")

        st.divider()

        # ── Bloom's Taxonomy Performance ──
        st.subheader("🧠 Performance by Cognitive Level")
        st.write(
            "This shows how well you perform at each level "
            "of Bloom's Taxonomy across all your quizzes."
        )

        blooms_data = aggregate_blooms_performance(quiz_history)

        if blooms_data:
            blooms_df = pd.DataFrame(blooms_data)
            fig_blooms = px.bar(
                blooms_df,
                x="Level",
                y="Avg Score (%)",
                color="Avg Score (%)",
                color_continuous_scale=[
                    [0, "#EF4444"],
                    [0.5, "#F59E0B"],
                    [1, "#10B981"]
                ],
                title="Average Score by Bloom's Taxonomy Level",
                text="Avg Score (%)"
            )
            fig_blooms.update_traces(texttemplate='%{text}%')
            fig_blooms.update_layout(
                plot_bgcolor="rgba(0,0,0,0)",
                paper_bgcolor="rgba(0,0,0,0)",
                font=dict(color="white"),
                coloraxis_showscale=False
            )
            fig_blooms.add_hline(
                y=70,
                line_dash="dash",
                line_color="green"
            )
            st.plotly_chart(fig_blooms, use_container_width=True)

        st.divider()

    # ── Flashcard Retention ──
    if flashcard_history:
        st.subheader("🃏 Flashcard Retention Analysis")

        retention = calculate_retention_rate(flashcard_history)

        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric(
                "Retention Rate",
                f"{retention['retention_rate']}%"
            )
        with col2:
            st.metric(
                "High Confidence Cards",
                retention["high_confidence_cards"]
            )
        with col3:
            st.metric(
                "Total Cards Reviewed",
                retention["total_cards"]
            )

        st.info(f"💡 {retention['message']}")

        # Difficulty breakdown
        difficulty_counts = {"Easy": 0, "Medium": 0, "Hard": 0}
        for card in flashcard_history:
            diff = card.get("difficulty", "Medium")
            difficulty_counts[diff] = difficulty_counts.get(diff, 0) + 1

        fig_diff = px.pie(
            values=list(difficulty_counts.values()),
            names=list(difficulty_counts.keys()),
            title="Flashcard Difficulty Distribution",
            color_discrete_map={
                "Easy": "#10B981",
                "Medium": "#F59E0B",
                "Hard": "#EF4444"
            }
        )
        fig_diff.update_layout(
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            font=dict(color="white")
        )
        st.plotly_chart(fig_diff, use_container_width=True)

        st.divider()

    # ── Knowledge Gap Detection ──
    st.subheader("🎯 Knowledge Gap Analysis")
    st.write(
        "Identifies areas where you consistently struggle "
        "based on quiz and flashcard performance."
    )

    gaps = detect_knowledge_gaps(quiz_history, flashcard_history)

    if gaps["has_gaps"]:
        col1, col2 = st.columns(2)

        with col1:
            if gaps["weak_blooms_levels"]:
                st.write("**Weak Cognitive Levels:**")
                for item in gaps["weak_blooms_levels"]:
                    st.error(
                        f"❌ {item['level']} — "
                        f"avg score: {item['avg_score']}%"
                    )
            else:
                st.success("✅ No weak cognitive levels detected!")

        with col2:
            if gaps["low_confidence_topics"]:
                from collections import Counter
                topic_counts = Counter(gaps["low_confidence_topics"])
                st.write("**Low Confidence Areas:**")
                for topic, count in topic_counts.most_common(5):
                    st.warning(f"⚠️ {topic} ({count} low-confidence cards)")
            else:
                st.success("✅ No low confidence areas detected!")
    else:
        st.success(
            "✅ No significant knowledge gaps detected! "
            "Keep up the good work."
        )

    st.divider()

    # ── Personalised Study Plan ──
    st.subheader("📅 Your Personalised Study Plan")
    st.write(
        "Generated based on your document analysis and "
        "performance history. Powered by local adaptive algorithm."
    )

    student_level = calculate_student_level(quiz_history)
    st.write(f"**Your current level:** {student_level.title()}")

    if "study_text" in st.session_state and st.session_state.study_text:
        if st.button(
            "🗓️ Generate 7-Day Study Plan",
            use_container_width=True
        ):
            with st.spinner("Generating personalised study plan..."):
                segments = segment_topics(
                    st.session_state.study_text
                )
                keywords = []
                if "preprocessed" in st.session_state:
                    keywords = st.session_state.preprocessed.get(
                        "keywords", []
                    )
                readability = "Moderate"
                if "preprocessed" in st.session_state:
                    readability = st.session_state.preprocessed.get(
                        "readability", {}
                    ).get("level", "Moderate")

                plan = generate_study_plan(
                    topic_segments=segments,
                    keywords=keywords,
                    readability_level=readability,
                    student_level=student_level,
                    days=7
                )
                st.session_state.study_plan = plan

        if "study_plan" in st.session_state:
            plan = st.session_state.study_plan
            for day_plan in plan:
                with st.expander(
                    f"📅 Day {day_plan['day']} — "
                    f"Est. {day_plan['estimated_time']}"
                ):
                    for activity in day_plan["activities"]:
                        st.write(
                            f"{activity['icon']} **{activity['type']}:** "
                            f"{activity['description']} "
                            f"({activity['duration']})"
                        )
                    st.caption(f"💡 Tip: {day_plan['tip']}")
    else:
        st.info(
            "Upload a document on the Home page to generate "
            "a personalised study plan."
        )

    st.divider()

    # ── Study Activity Timeline ──
    if sessions:
        st.subheader("📆 Study Activity Timeline")

        timeline_data = []
        for session in sessions:
            try:
                date = datetime.fromisoformat(
                    session["created_at"]
                ).strftime("%b %d, %Y")
                timeline_data.append({
                    "Date": date,
                    "Document": session.get(
                        "document_name", "Unknown"
                    )[:30],
                    "Words": session.get("document_word_count", 0),
                    "Readability": session.get("readability_level", "Unknown")
                })
            except Exception:
                continue

        if timeline_data:
            timeline_df = pd.DataFrame(timeline_data)
            st.dataframe(
                timeline_df,
                use_container_width=True,
                hide_index=True
            )


def aggregate_blooms_performance(quiz_history):
    """Aggregate Bloom's performance across all quizzes."""
    blooms_scores = {}
    blooms_counts = {}

    for quiz in quiz_history:
        dist = quiz.get("blooms_distribution", {})
        if isinstance(dist, str):
            import json
            try:
                dist = json.loads(dist)
            except Exception:
                continue

        for level, data in dist.items():
            if isinstance(data, dict):
                pct = data.get("percentage", 0)
            else:
                pct = 0

            if level not in blooms_scores:
                blooms_scores[level] = 0
                blooms_counts[level] = 0

            blooms_scores[level] += pct
            blooms_counts[level] += 1

    result = []
    for level in blooms_scores:
        avg = round(
            blooms_scores[level] / blooms_counts[level], 1
        )
        result.append({
            "Level": level,
            "Avg Score (%)": avg
        })

    return result


def show_empty_state_tips():
    """Show tips when no data is available yet."""
    st.subheader("🚀 How to Get Started")
    col1, col2, col3 = st.columns(3)

    with col1:
        st.info(
            "**Step 1: Upload Material**\n\n"
            "Go to the Home page and upload a PDF "
            "or paste your study notes."
        )
    with col2:
        st.info(
            "**Step 2: Generate Tools**\n\n"
            "Create a summary, flashcards and take "
            "a quiz on your material."
        )
    with col3:
        st.info(
            "**Step 3: Track Progress**\n\n"
            "Come back here after each session to "
            "see your improvement over time."
        )
