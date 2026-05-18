import streamlit as st
from utils.pdf_extractor import extract_text_from_pdf
from views.summary import show_summary_page
from views.flashcards import show_flashcards_page
from views.quiz import show_quiz_page

st.set_page_config(
    page_title="AI Study Assistant",
    page_icon="🎓",
    layout="centered"
)

# Sidebar navigation
with st.sidebar:
    st.title("🎓 AI Study Assistant")
    st.divider()

    # Show material status
    if "study_text" in st.session_state and st.session_state.study_text:
        st.success("✅ Material loaded!")
        word_count = len(st.session_state.study_text.split())
        st.info(f"📄 {word_count} words ready")
        if st.button("🗑️ Clear Material", use_container_width=True):
            del st.session_state.study_text
            if "summary" in st.session_state:
                del st.session_state.summary
            if "flashcards" in st.session_state:
                del st.session_state.flashcards
            if "quiz" in st.session_state:
                del st.session_state.quiz
            st.rerun()
    else:
        st.warning("⚠️ No material loaded")

    st.divider()
    page = st.radio("Navigate", [
        "🏠 Home",
        "📝 Summary",
        "🃏 Flashcards",
        "✅ Quiz"
    ])
    st.divider()
    st.caption("Built with ❤️ using Streamlit & Gemini AI")

# Home page
if page == "🏠 Home":
    # Hero section
    st.title("🎓 AI Study Assistant")
    st.subheader("Turn your study material into powerful learning tools instantly!")
    st.write("Upload a PDF or paste your notes — AI generates summaries, flashcards and quizzes in seconds.")

    st.divider()

    # Feature highlights
    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown("### 📝 Summary")
        st.write("Condenses lengthy notes into clear, structured key points")
    with col2:
        st.markdown("### 🃏 Flashcards")
        st.write("Creates interactive question & answer cards for active recall")
    with col3:
        st.markdown("### ✅ Quiz")
        st.write("Generates multiple choice questions to test your knowledge")

    st.divider()

    # Input section
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
                    st.error(f"Could not read PDF: {error}")
                else:
                    study_text = text
                    st.success(f"✅ PDF loaded! ({len(text.split())} words extracted)")
                    with st.expander("Preview extracted text"):
                        st.write(text[:1000] + "..." if len(text) > 1000 else text)

    elif input_method == "✏️ Paste Text":
        study_text = st.text_area(
            "Paste your study notes here",
            placeholder="Paste your lecture notes, textbook content, or any study material...",
            height=300
        )
        if study_text:
            st.success(f"✅ Text loaded! ({len(study_text.split())} words)")

    if study_text:
        st.session_state.study_text = study_text
        st.divider()
        st.success("✅ Material loaded! Select a tool from the sidebar to get started 👈")

elif page == "📝 Summary":
    show_summary_page()
    
elif page == "🃏 Flashcards":
    show_flashcards_page()

elif page == "✅ Quiz":
    show_quiz_page()