import streamlit as st
from utils.gemini_client import generate_quiz

def show_quiz_page():
    st.title("✅ Quiz Generator")

    # Check if study material is loaded
    if "study_text" not in st.session_state or not st.session_state.study_text:
        st.warning("⚠️ No study material loaded. Please go back to the home page first!")
        if st.button("⬅️ Go to Home"):
            st.session_state.page = "Home"
            st.rerun()
        return

    st.write("AI will generate a multiple choice quiz to test your understanding.")
    word_count = len(st.session_state.study_text.split())
    st.info(f"📄 Material loaded: **{word_count} words**")

    if st.button("✨ Generate Quiz", use_container_width=True):
        with st.spinner("AI is generating your quiz... 🤖"):
            result, error = generate_quiz(st.session_state.study_text)
            if error:
                st.error(f"Could not generate quiz: {error}")
            else:
                st.session_state.quiz = result.get("quiz", [])
                st.session_state.quiz_answers = {}
                st.session_state.quiz_submitted = False
                st.success(f"✅ {len(st.session_state.quiz)} questions generated!")

    # Display quiz if it exists
    if "quiz" in st.session_state and st.session_state.quiz:
        quiz = st.session_state.quiz
        submitted = st.session_state.get("quiz_submitted", False)

        st.divider()
        st.subheader("📝 Answer all questions then click Submit")

        # Display questions
        for i, q in enumerate(quiz):
            st.markdown(f"**Question {i+1}:** {q['question']}")
            answer = st.radio(
                f"Select your answer for Q{i+1}",
                q["options"],
                key=f"q_{i}",
                label_visibility="collapsed",
                disabled=submitted
            )
            st.session_state.quiz_answers[i] = answer
            st.write("")

        st.divider()

        # Submit button
        if not submitted:
            if st.button("🎯 Submit Quiz", use_container_width=True):
                st.session_state.quiz_submitted = True
                st.rerun()

        # Results
        if submitted:
            correct = 0
            total = len(quiz)

            for i, q in enumerate(quiz):
                user_answer = st.session_state.quiz_answers.get(i, "")
                is_correct = user_answer == q["correct_answer"]
                if is_correct:
                    correct += 1

            score_percent = round((correct / total) * 100)

            # Score display
            st.subheader("🏆 Your Results")
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Score", f"{correct}/{total}")
            with col2:
                st.metric("Percentage", f"{score_percent}%")
            with col3:
                if score_percent >= 80:
                    st.metric("Grade", "Excellent! 🌟")
                elif score_percent >= 60:
                    st.metric("Grade", "Good! 👍")
                else:
                    st.metric("Grade", "Keep Studying! 📚")

            # Score message
            if score_percent >= 80:
                st.success("🌟 Excellent work! You have a strong understanding of the material!")
            elif score_percent >= 60:
                st.info("👍 Good effort! Review the questions you missed and try again.")
            else:
                st.warning("📚 Keep studying! Go through the summary and flashcards to strengthen your understanding.")

            st.divider()

            # Detailed results
            st.subheader("📋 Detailed Results")
            for i, q in enumerate(quiz):
                user_answer = st.session_state.quiz_answers.get(i, "")
                is_correct = user_answer == q["correct_answer"]

                with st.expander(
                    f"{'✅' if is_correct else '❌'} Question {i+1}: {q['question']}"
                ):
                    st.write(f"**Your answer:** {user_answer}")
                    st.write(f"**Correct answer:** {q['correct_answer']}")
                    if not is_correct:
                        st.error(f"💡 **Explanation:** {q['explanation']}")
                    else:
                        st.success("Well done! ✅")

            st.divider()

            # Retry button
            if st.button("🔄 Retake Quiz", use_container_width=True):
                st.session_state.quiz_submitted = False
                st.session_state.quiz_answers = {}
                st.rerun()