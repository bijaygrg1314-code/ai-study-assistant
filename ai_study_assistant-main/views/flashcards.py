import streamlit as st
from utils.gemini_client import generate_flashcards
from utils.postprocessor import process_flashcards
from utils.session_manager import save_flashcards


def show_flashcards_page(user=None):
    st.title("🃏 Flashcard Generator")

    if "study_text" not in st.session_state or not st.session_state.study_text:
        st.warning("⚠️ No study material loaded. Please go back to the home page first!")
        if st.button("⬅️ Go to Home"):
            st.session_state.page = "Home"
            st.rerun()
        return

    # Check for loaded flashcards from history
    if "loaded_flashcards" in st.session_state and st.session_state.loaded_flashcards:
        st.info("📚 Showing flashcards loaded from your history.")
        cards = st.session_state.loaded_flashcards
        display_loaded_flashcards(cards)
        if st.button("🔄 Generate New Flashcards"):
            del st.session_state.loaded_flashcards
            st.rerun()
        return

    word_count = len(st.session_state.study_text.split())
    st.info(f"📄 Material loaded: **{word_count} words**")

    if st.button("✨ Generate Flashcards", use_container_width=True):
        with st.spinner("AI is generating your flashcards... 🤖"):
            result, error = generate_flashcards(st.session_state.study_text)

            if error:
                st.error(f"❌ {error}")
            else:
                raw_cards = result.get("flashcards", [])
                processed = process_flashcards(raw_cards)
                st.session_state.processed_flashcards = processed
                st.session_state.current_card = 0
                st.session_state.show_answer = False

                # Save to database if user is logged in
                if user and "session_id" in st.session_state and st.session_state.session_id:
                    save_flashcards(
                        user.id,
                        st.session_state.session_id,
                        processed
                    )

                st.success(f"✅ {processed['total_cards']} flashcards generated!")

    # Display flashcards if they exist
    if "processed_flashcards" in st.session_state and st.session_state.processed_flashcards:
        processed = st.session_state.processed_flashcards
        flashcards = processed["flashcards"]

        # Difficulty and Blooms summary
        st.divider()
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Total Cards", processed["total_cards"])
        with col2:
            st.metric("Easy", processed["difficulty_summary"]["Easy"])
        with col3:
            st.metric("Medium", processed["difficulty_summary"]["Medium"])
        with col4:
            st.metric("Hard", processed["difficulty_summary"]["Hard"])

        # Blooms distribution
        with st.expander("🧠 Bloom's Taxonomy Distribution"):
            for level, count in processed["blooms_distribution"].items():
                st.write(f"**{level}:** {count} cards")

        st.divider()

        total = len(flashcards)
        current = st.session_state.get("current_card", 0)
        show_answer = st.session_state.get("show_answer", False)

        card = flashcards[current]

        st.subheader(f"Card {current + 1} of {total}")
        st.progress((current + 1) / total)

        # Difficulty and Blooms badges
        col1, col2, col3 = st.columns(3)
        with col1:
            difficulty = card["difficulty"]
            color = {"Easy": "🟢", "Medium": "🟡", "Hard": "🔴"}
            st.write(f"**Difficulty:** {color[difficulty]} {difficulty}")
        with col2:
            st.write(
                f"**Bloom's:** {card['blooms_emoji']} {card['blooms_level']}"
            )
        with col3:
            st.write(
                f"**Review in:** 📅 {card['spaced_repetition']['next_review']} day(s)"
            )

        # Question card
        st.markdown(f"""
            <div style="
                background: #1E1E2E;
                border-radius: 12px;
                padding: 30px;
                text-align: center;
                min-height: 150px;
                border: 2px solid #2563EB;
                margin: 10px 0;
            ">
                <h3 style="color: #2563EB;">❓ Question</h3>
                <p style="font-size: 18px; color: white;">{card['question']}</p>
            </div>
        """, unsafe_allow_html=True)

        # Show/Hide answer
        if st.button(
            "🙈 Hide Answer" if show_answer else "👁️ Show Answer",
            use_container_width=True
        ):
            st.session_state.show_answer = not show_answer
            st.rerun()

        if show_answer:
            st.markdown(f"""
                <div style="
                    background: #1E2E1E;
                    border-radius: 12px;
                    padding: 30px;
                    text-align: center;
                    min-height: 120px;
                    border: 2px solid #16A34A;
                    margin: 10px 0;
                ">
                    <h3 style="color: #16A34A;">✅ Answer</h3>
                    <p style="font-size: 18px; color: white;">{card['answer']}</p>
                </div>
            """, unsafe_allow_html=True)

            st.caption(
                f"💡 {card['blooms_description']} | "
                f"📅 Spaced repetition: {card['spaced_repetition']['description']}"
            )

        st.write("")

        # Navigation
        col1, col2, col3 = st.columns(3)
        with col1:
            if st.button(
                "⬅️ Previous",
                use_container_width=True,
                disabled=current == 0
            ):
                st.session_state.current_card = current - 1
                st.session_state.show_answer = False
                st.rerun()
        with col2:
            st.write(f"**{current + 1} / {total}**")
        with col3:
            if st.button(
                "Next ➡️",
                use_container_width=True,
                disabled=current == total - 1
            ):
                st.session_state.current_card = current + 1
                st.session_state.show_answer = False
                st.rerun()

        st.divider()

        # Sort options
        sort_option = st.selectbox(
            "Sort flashcards by",
            ["Default", "Difficulty (Easy first)",
             "Difficulty (Hard first)", "Bloom's Level"]
        )

        sorted_cards = flashcards.copy()
        if sort_option == "Difficulty (Easy first)":
            order = {"Easy": 0, "Medium": 1, "Hard": 2}
            sorted_cards.sort(key=lambda x: order[x["difficulty"]])
        elif sort_option == "Difficulty (Hard first)":
            order = {"Easy": 2, "Medium": 1, "Hard": 0}
            sorted_cards.sort(key=lambda x: order[x["difficulty"]])
        elif sort_option == "Bloom's Level":
            blooms_order = {
                "Remember": 0, "Understand": 1, "Apply": 2,
                "Analyse": 3, "Evaluate": 4, "Create": 5
            }
            sorted_cards.sort(
                key=lambda x: blooms_order.get(x["blooms_level"], 0)
            )

        # View all cards
        with st.expander("📋 View All Flashcards"):
            for i, fc in enumerate(sorted_cards):
                difficulty = fc["difficulty"]
                color = {"Easy": "🟢", "Medium": "🟡", "Hard": "🔴"}
                st.markdown(
                    f"**Q{i+1}** {color[difficulty]} "
                    f"{fc['blooms_emoji']} {fc['question']}"
                )
                st.markdown(f"**A{i+1}:** {fc['answer']}")
                st.caption(
                    f"Difficulty: {difficulty} | "
                    f"Bloom's: {fc['blooms_level']} | "
                    f"Review in: {fc['spaced_repetition']['next_review']} day(s)"
                )
                st.divider()


def display_loaded_flashcards(cards):
    """Display flashcards loaded from history."""
    st.subheader(f"🃏 {len(cards)} Saved Flashcards")
    for i, card in enumerate(cards):
        with st.expander(f"Card {i+1}: {card['question'][:50]}..."):
            st.write(f"**Question:** {card['question']}")
            st.write(f"**Answer:** {card['answer']}")
            st.write(f"**Difficulty:** {card['difficulty']}")
            st.write(f"**Bloom's Level:** {card['blooms_level']}")
