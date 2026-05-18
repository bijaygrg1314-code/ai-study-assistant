import streamlit as st
from utils.gemini_client import generate_flashcards

def show_flashcards_page():
    st.title("🃏 Flashcard Generator")

    # Check if study material is loaded
    if "study_text" not in st.session_state or not st.session_state.study_text:
        st.warning("⚠️ No study material loaded. Please go back to the home page first!")
        if st.button("⬅️ Go to Home"):
            st.session_state.page = "Home"
            st.rerun()
        return

    st.write("AI will generate flashcards from your study material for active recall practice.")
    word_count = len(st.session_state.study_text.split())
    st.info(f"📄 Material loaded: **{word_count} words**")

    if st.button("✨ Generate Flashcards", use_container_width=True):
        with st.spinner("AI is generating your flashcards... 🤖"):
            result, error = generate_flashcards(st.session_state.study_text)
            if error:
                st.error(f"Could not generate flashcards: {error}")
            else:
                st.session_state.flashcards = result.get("flashcards", [])
                st.session_state.current_card = 0
                st.session_state.show_answer = False
                st.success(f"✅ {len(st.session_state.flashcards)} flashcards generated!")

    # Display flashcards if they exist
    if "flashcards" in st.session_state and st.session_state.flashcards:
        flashcards = st.session_state.flashcards
        total = len(flashcards)
        current = st.session_state.get("current_card", 0)
        show_answer = st.session_state.get("show_answer", False)

        st.divider()
        st.subheader(f"Card {current + 1} of {total}")

        # Progress bar
        st.progress((current + 1) / total)

        # Flashcard display
        card = flashcards[current]
        st.markdown("""
            <style>
            .flashcard {
                background: #1E1E2E;
                border-radius: 12px;
                padding: 30px;
                text-align: center;
                min-height: 200px;
                display: flex;
                flex-direction: column;
                justify-content: center;
                border: 1px solid #7C3AED;
            }
            </style>
        """, unsafe_allow_html=True)

        # Question
        st.markdown(f"""
            <div class="flashcard">
                <h3 style="color: #2563EB;">❓ Question</h3>
                <p style="font-size: 18px;">{card['question']}</p>
            </div>
        """, unsafe_allow_html=True)

        # Show/Hide answer button
        st.write("")
        if st.button(
            "🙈 Hide Answer" if show_answer else "👁️ Show Answer",
            use_container_width=True
        ):
            st.session_state.show_answer = not show_answer
            st.rerun()

        # Answer
        if show_answer:
            st.markdown(f"""
                <div class="flashcard" style="border-color: #16A34A; margin-top: 10px;">
                    <h3 style="color: #16A34A;">✅ Answer</h3>
                    <p style="font-size: 18px;">{card['answer']}</p>
                </div>
            """, unsafe_allow_html=True)

        st.write("")

        # Navigation buttons
        col1, col2, col3 = st.columns(3)
        with col1:
            if st.button("⬅️ Previous", use_container_width=True, disabled=current == 0):
                st.session_state.current_card = current - 1
                st.session_state.show_answer = False
                st.rerun()
        with col2:
            st.write(f"**{current + 1} / {total}**")
        with col3:
            if st.button("Next ➡️", use_container_width=True, disabled=current == total - 1):
                st.session_state.current_card = current + 1
                st.session_state.show_answer = False
                st.rerun()

        st.divider()

        # All flashcards view
        with st.expander("📋 View All Flashcards"):
            for i, fc in enumerate(flashcards):
                st.markdown(f"**Q{i+1}:** {fc['question']}")
                st.markdown(f"**A{i+1}:** {fc['answer']}")
                st.divider()