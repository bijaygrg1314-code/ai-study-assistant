import streamlit as st
from utils.pdf_extractor import extract_text_from_pdf
from utils.preprocessor import preprocess_text
from views.summary import show_summary_page
from views.flashcards import show_flashcards_page
from views.quiz import show_quiz_page
from views.login import show_login_page
from views.history import show_history_page
from views.chat import show_chat_page
from views.analytics import show_analytics_page

st.set_page_config(
    page_title="AI Study Assistant",
    page_icon="🎓",
    layout="centered"
)

# Initialise session state
if "user" not in st.session_state:
    st.session_state.user = None
if "guest_mode" not in st.session_state:
    st.session_state.guest_mode = False
if "session_id" not in st.session_state:
    st.session_state.session_id = None
if "knowledge_base" not in st.session_state:
    st.session_state.knowledge_base = None

# Show login page if not logged in and not in guest mode
if not st.session_state.user and not st.session_state.guest_mode:
    show_login_page()
    st.stop()

# Sidebar
with st.sidebar:
    st.title("🎓 AI Study Assistant")
    st.divider()

    # User info
    if st.session_state.user:
        st.success(f"✅ Logged in")
        nav_options = [
            "🏠 Home",
            "📝 Summary",
            "🃏 Flashcards",
            "✅ Quiz",
            "💬 Document Q&A",
            "📊 Analytics",
            "📚 History"
        ]
    else:
        st.info("👤 Guest Mode")
        st.caption("Sign in to save sessions and track progress.")
        nav_options = [
            "🏠 Home",
            "📝 Summary",
            "🃏 Flashcards",
            "✅ Quiz",
            "💬 Document Q&A"
        ]

    # Material status
    if "study_text" in st.session_state and st.session_state.study_text:
        word_count = len(st.session_state.study_text.split())
        st.success("✅ Material loaded!")
        st.info(f"📄 {word_count} words ready")

        if "preprocessed" in st.session_state:
            prep = st.session_state.preprocessed
            st.caption(
                f"📊 Readability: {prep['readability']['level']}"
            )

        if st.button("🗑️ Clear Material", use_container_width=True):
            keys_to_clear = [
                "study_text", "preprocessed", "summary",
                "processed_flashcards", "processed_quiz",
                "session_id", "document_name", "loaded_summary",
                "loaded_flashcards", "knowledge_base",
                "chat_history", "study_plan", "local_analysis",
                "last_text"
            ]
            for key in keys_to_clear:
                if key in st.session_state:
                    del st.session_state[key]
            st.rerun()
    else:
        st.warning("⚠️ No material loaded")

    st.divider()
    page = st.radio("Navigate", nav_options)
    st.divider()

    if st.session_state.user:
        if st.button("🚪 Logout", use_container_width=True):
            from utils.auth import sign_out
            sign_out()
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.rerun()
    else:
        if st.button("🔐 Sign In", use_container_width=True):
            st.session_state.guest_mode = False
            st.rerun()

    st.caption("Built with ❤️ using Streamlit & Gemini AI")

# Page routing
if page == "🏠 Home":
    st.title("🎓 AI Study Assistant")
    st.subheader(
        "Turn your study material into powerful learning tools instantly!"
    )
    st.write(
        "Upload a PDF or paste your notes — AI generates "
        "summaries, flashcards, quizzes and more in seconds."
    )
    st.divider()

    # Feature cards
    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown("### 📝 Summary")
        st.write("Hybrid TF-IDF + Gemini pipeline")
    with col2:
        st.markdown("### 🃏 Flashcards")
        st.write("Difficulty ratings + spaced repetition")
    with col3:
        st.markdown("### ✅ Quiz")
        st.write("Adaptive difficulty + Bloom's taxonomy")

    col1, col2 = st.columns(2)
    with col1:
        st.markdown("### 💬 Document Q&A")
        st.write("RAG — local TF-IDF retrieval + AI refinement")
    with col2:
        st.markdown("### 📊 Analytics")
        st.write("Progress tracking + knowledge gap detection")

    st.divider()
    st.subheader("📂 Load Your Study Material")

    input_method = st.radio(
        "How would you like to input your study material?",
        ["📄 Upload PDF", "✏️ Paste Text"],
        horizontal=True
    )

    study_text = None

    if input_method == "📄 Upload PDF":
        uploaded_file = st.file_uploader(
            "Upload your PDF",
            type=["pdf"],
            help="Upload a PDF of your lecture notes or textbook chapter"
        )
        if uploaded_file:
            with st.spinner("Extracting text from PDF..."):
                text, error = extract_text_from_pdf(uploaded_file)
                if error:
                    st.error(f"❌ Could not read PDF: {error}")
                else:
                    study_text = text
                    st.session_state.document_name = uploaded_file.name
                    st.success(
                        f"✅ PDF loaded! ({len(text.split())} words extracted)"
                    )
                    with st.expander("Preview extracted text"):
                        st.write(
                            text[:1000] + "..." if len(text) > 1000 else text
                        )

    elif input_method == "✏️ Paste Text":
        study_text = st.text_area(
            "Paste your study notes here",
            placeholder="Paste your lecture notes, textbook content, or any study material...",
            height=300
        )
        if study_text:
            st.session_state.document_name = "Pasted Text"
            st.success(f"✅ Text loaded! ({len(study_text.split())} words)")

    if study_text:
        st.session_state.study_text = study_text

        # Reset knowledge base when new material is loaded
        if st.session_state.get("last_text") != study_text[:100]:
            st.session_state.knowledge_base = None
            if "chat_history" in st.session_state:
                del st.session_state["chat_history"]
            if "local_analysis" in st.session_state:
                del st.session_state["local_analysis"]

        # Run preprocessing
        if "preprocessed" not in st.session_state or \
                st.session_state.get("last_text") != study_text[:100]:
            with st.spinner("🔬 Running NLP analysis pipeline..."):
                st.session_state.preprocessed = preprocess_text(study_text)
                st.session_state.last_text = study_text[:100]

                # Auto create session when logged in
                if st.session_state.user and not st.session_state.session_id:
                    from utils.session_manager import save_study_session
                    prep = st.session_state.preprocessed
                    doc_name = st.session_state.get(
                        "document_name", "Pasted Text"
                    )
                    session_id, err = save_study_session(
                        user_id=st.session_state.user.id,
                        document_name=doc_name,
                        word_count=prep["statistics"]["word_count"],
                        readability_level=prep["readability"]["level"],
                        keywords=prep["keywords"][:5]
                    )
                    if session_id:
                        st.session_state.session_id = session_id

        prep = st.session_state.preprocessed
        st.divider()
        st.subheader("🔬 NLP Analysis Pipeline Results")
        st.caption(
            "Computed locally using TF-IDF, cosine similarity "
            "and statistical NLP — no API required"
        )

        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Words", prep["statistics"]["word_count"])
        with col2:
            st.metric(
                "Reading Time",
                f"{prep['statistics']['reading_time_minutes']} min"
            )
        with col3:
            st.metric("Readability", prep["readability"]["level"])
        with col4:
            st.metric("Sections", prep["chunk_count"])

        st.write(
            f"**Top Keywords (TF-IDF):** {', '.join(prep['keywords'][:8])}"
        )
        st.write(
            f"**Flesch Reading Ease:** {prep['readability']['flesch_ease']} — "
            f"{prep['readability']['description']}"
        )
        st.write(
            f"**Vocabulary Richness:** "
            f"{prep['statistics']['vocabulary_richness']}% unique words"
        )

        if prep["is_long_document"]:
            st.info(
                f"📄 Long document detected ({prep['chunk_count']} sections). "
                f"Intelligent TF-IDF chunking will select the most "
                f"relevant section for each AI generation task."
            )

        st.divider()
        st.success(
            "✅ Material loaded and analysed! "
            "Select a tool from the sidebar to get started 👈"
        )

elif page == "📝 Summary":
    show_summary_page(user=st.session_state.user)

elif page == "🃏 Flashcards":
    show_flashcards_page(user=st.session_state.user)

elif page == "✅ Quiz":
    show_quiz_page(user=st.session_state.user)

elif page == "💬 Document Q&A":
    show_chat_page(user=st.session_state.user)

elif page == "📊 Analytics":
    if st.session_state.user:
        show_analytics_page(user=st.session_state.user)
    else:
        st.warning("Please sign in to access Analytics.")
        st.info("Click 'Sign In' in the sidebar to create an account.")

elif page == "📚 History":
    if st.session_state.user:
        show_history_page(user=st.session_state.user)
    else:
        st.warning("Please sign in to view your history.")
