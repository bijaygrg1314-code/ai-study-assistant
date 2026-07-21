import streamlit as st
from utils.gemini_client import generate_quiz
from utils.postprocessor import process_quiz_questions, generate_performance_report
from utils.session_manager import save_quiz_result


def show_quiz_page(user=None):
    st.title("✅ Quiz Generator")

    if "study_text" not in st.session_state or not st.session_state.study_text:
        st.warning("⚠️ No study material loaded. Please go back to the home page first!")
        if st.button("⬅️ Go to Home"):
            st.session_state.page = "Home"
            st.rerun()
        return

    word_count = len(st.session_state.study_text.split())
    st.info(f"📄 Material loaded: **{word_count} words**")

    if st.button("✨ Generate Quiz", use_container_width=True):
        with st.spinner("AI is generating your quiz... 🤖"):
            result, error = generate_quiz(st.session_state.study_text)

            if error:
                st.error(f"❌ {error}")
            else:
                raw_questions = result.get("quiz", [])
                processed = process_quiz_questions(raw_questions)
                st.session_state.processed_quiz = processed
                st.session_state.quiz_answers = {}
                st.session_state.quiz_submitted = False
                st.success(
                    f"✅ {processed['total_questions']} questions generated!"
                )

                # Show Blooms distribution
                with st.expander("🧠 Question Analysis"):
                    col1, col2 = st.columns(2)
                    with col1:
                        st.write("**Bloom's Taxonomy Distribution:**")
                        for level, count in processed["blooms_distribution"].items():
                            st.write(f"• {level}: {count} questions")
                    with col2:
                        st.write("**Difficulty Distribution:**")
                        for diff, count in processed["difficulty_distribution"].items():
                            color = {"Easy": "🟢", "Medium": "🟡", "Hard": "🔴"}
                            st.write(f"• {color[diff]} {diff}: {count} questions")

    # Display quiz
    if "processed_quiz" in st.session_state and st.session_state.processed_quiz:
        processed = st.session_state.processed_quiz
        questions = processed["questions"]
        submitted = st.session_state.get("quiz_submitted", False)

        st.divider()
        st.subheader("📝 Answer all questions then click Submit")

        for i, q in enumerate(questions):
            difficulty = q["difficulty"]
            color = {"Easy": "🟢", "Medium": "🟡", "Hard": "🔴"}

            st.markdown(
                f"**Question {i+1}:** {q['question']}  "
                f"{color[difficulty]} {difficulty} | "
                f"{q['blooms_emoji']} {q['blooms_level']}"
            )

            answer = st.radio(
                f"Select answer for Q{i+1}",
                q["options"],
                key=f"q_{i}",
                label_visibility="collapsed",
                disabled=submitted
            )
            st.session_state.quiz_answers[i] = answer
            st.write("")

        st.divider()

        if not submitted:
            if st.button("🎯 Submit Quiz", use_container_width=True):
                st.session_state.quiz_submitted = True
                st.rerun()

        if submitted:
            correct = 0
            total = len(questions)
            quiz_results = {}

            for i, q in enumerate(questions):
                user_answer = st.session_state.quiz_answers.get(i, "")
                is_correct = user_answer == q["correct_answer"]
                quiz_results[i] = is_correct
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

            if score_percent >= 80:
                st.success("🌟 Excellent work! Strong understanding of the material!")
            elif score_percent >= 60:
                st.info("👍 Good effort! Review the questions you missed.")
            else:
                st.warning("📚 Keep studying! Use the flashcards to strengthen understanding.")

            # Performance report
            st.divider()
            performance = generate_performance_report(quiz_results, processed)

            st.subheader("📊 Performance by Cognitive Level")
            col1, col2 = st.columns(2)

            with col1:
                st.write("**Bloom's Taxonomy Performance:**")
                for level, data in performance["blooms_performance"].items():
                    pct = data["percentage"]
                    bar = "🟩" * (pct // 20) + "⬜" * (5 - pct // 20)
                    st.write(
                        f"**{level}:** {bar} {data['correct']}/{data['total']} ({pct}%)"
                    )

            with col2:
                st.write("**Difficulty Performance:**")
                for diff, data in performance["difficulty_performance"].items():
                    color = {"Easy": "🟢", "Medium": "🟡", "Hard": "🔴"}
                    st.write(
                        f"**{color[diff]} {diff}:** "
                        f"{data['correct']}/{data['total']} ({data['percentage']}%)"
                    )

            if performance["weakest_area"]:
                st.divider()
                st.subheader("💡 Study Recommendation")
                st.info(
                    f"**Weakest area:** {performance['weakest_area']}\n\n"
                    f"{performance['recommendation']}"
                )

            # Save quiz result
            if user and "session_id" in st.session_state and st.session_state.session_id:
                save_quiz_result(
                    user_id=user.id,
                    session_id=st.session_state.session_id,
                    score=correct,
                    total=total,
                    percentage=score_percent,
                    blooms_dist=performance["blooms_performance"],
                    difficulty_dist=performance["difficulty_performance"]
                )

            st.divider()

            # Detailed results
            st.subheader("📋 Detailed Results")
            for i, q in enumerate(questions):
                user_answer = st.session_state.quiz_answers.get(i, "")
                is_correct = user_answer == q["correct_answer"]

                with st.expander(
                    f"{'✅' if is_correct else '❌'} Q{i+1}: {q['question'][:60]}..."
                ):
                    st.write(f"**Your answer:** {user_answer}")
                    st.write(f"**Correct answer:** {q['correct_answer']}")
                    st.write(
                        f"**Bloom's Level:** {q['blooms_emoji']} {q['blooms_level']}"
                    )
                    st.write(f"**Difficulty:** {q['difficulty']}")
                    if not is_correct:
                        st.error(f"💡 **Explanation:** {q['explanation']}")
                    else:
                        st.success("Well done! ✅")

            # Retake
            if st.button("🔄 Retake Quiz", use_container_width=True):
                st.session_state.quiz_submitted = False
                st.session_state.quiz_answers = {}
                st.rerun()
