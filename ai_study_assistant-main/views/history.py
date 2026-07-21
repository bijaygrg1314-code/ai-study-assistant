import streamlit as st
from utils.session_manager import (
    get_user_sessions,
    get_session_summary,
    get_session_flashcards,
    get_user_stats
)
from datetime import datetime


def show_history_page(user):
    st.title("📚 Study History")
    st.write("View and reload your past study sessions.")

    # User stats
    stats, error = get_user_stats(user.id)
    if stats:
        st.subheader("📊 Your Overall Stats")
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Total Sessions", stats["total_sessions"])
        with col2:
            st.metric("Flashcards Created", stats["total_flashcards"])
        with col3:
            st.metric("Quizzes Taken", stats["total_quizzes"])
        with col4:
            st.metric("Avg Quiz Score", f"{stats['avg_quiz_score']}%")

    st.divider()

    # Past sessions
    st.subheader("📋 Past Sessions")
    sessions, error = get_user_sessions(user.id)

    if error:
        st.error(f"Could not load sessions: {error}")
        return

    if not sessions:
        st.info("No study sessions yet. Upload a document to get started! 📄")
        return

    for session in sessions:
        date = datetime.fromisoformat(
            session["created_at"]
        ).strftime("%B %d, %Y %I:%M %p")

        with st.expander(
            f"📄 {session['document_name']} — {date}"
        ):
            col1, col2, col3 = st.columns(3)
            with col1:
                st.write(f"**Words:** {session['document_word_count']}")
            with col2:
                st.write(f"**Readability:** {session['readability_level']}")
            with col3:
                keywords = session.get("keywords", [])
                st.write(f"**Keywords:** {', '.join(keywords[:3])}")

            col1, col2 = st.columns(2)

            with col1:
                if st.button(
                    "📝 Load Summary",
                    key=f"sum_{session['id']}"
                ):
                    summary, err = get_session_summary(session["id"])
                    if summary:
                        st.session_state.loaded_summary = summary
                        st.success("Summary loaded! Go to Summary page. ✅")
                    else:
                        st.warning("No summary saved for this session.")

            with col2:
                if st.button(
                    "🃏 Load Flashcards",
                    key=f"flash_{session['id']}"
                ):
                    cards, err = get_session_flashcards(session["id"])
                    if cards:
                        st.session_state.loaded_flashcards = cards
                        st.success("Flashcards loaded! Go to Flashcards page. ✅")
                    else:
                        st.warning("No flashcards saved for this session.")
