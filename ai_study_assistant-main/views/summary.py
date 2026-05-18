import streamlit as st
from utils.gemini_client import generate_summary

def show_summary_page():
    st.title("📝 AI Summary Generator")

    # Check if study material is loaded
    if "study_text" not in st.session_state or not st.session_state.study_text:
        st.warning("⚠️ No study material loaded. Please go back to the home page and upload your material first!")
        if st.button("⬅️ Go to Home"):
            st.session_state.page = "Home"
            st.rerun()
        return

    st.write("AI will generate a structured summary of your study material.")
    word_count = len(st.session_state.study_text.split())
    st.info(f"📄 Material loaded: **{word_count} words**")

    if st.button("✨ Generate Summary", use_container_width=True):
        with st.spinner("AI is reading and summarizing your material... 🤖"):
            summary, error = generate_summary(st.session_state.study_text)

            if error:
                st.error(f"Could not generate summary: {error}")
            else:
                # Save to session state
                st.session_state.summary = summary
                st.success("Summary generated successfully! ✅")

    # Display summary if it exists
    if "summary" in st.session_state and st.session_state.summary:
        summary = st.session_state.summary

        # Title
        st.subheader(f"📚 {summary.get('title', 'Study Summary')}")

        # Overview
        st.subheader("🔍 Overview")
        st.write(summary.get("overview", ""))

        st.divider()

        # Key Points
        st.subheader("🎯 Key Points")
        for i, point in enumerate(summary.get("key_points", []), 1):
            st.write(f"**{i}.** {point}")

        st.divider()

        # Important Terms
        terms = summary.get("important_terms", [])
        if terms:
            st.subheader("📖 Important Terms")
            for item in terms:
                with st.expander(f"📌 {item.get('term', '')}"):
                    st.write(item.get("definition", ""))

        st.divider()

        # Conclusion
        st.subheader("💡 Conclusion")
        st.info(summary.get("conclusion", ""))