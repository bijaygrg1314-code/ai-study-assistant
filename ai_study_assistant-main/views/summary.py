import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
from utils.gemini_client import generate_summary, generate_resource_recommendations
from utils.preprocessor import preprocess_text
from utils.local_nlp import run_full_local_analysis, extract_concepts
from utils.session_manager import save_study_session, save_summary


def show_summary_page(user=None):
    st.title("📝 Hybrid Summary Pipeline")
    st.markdown(
        "> **How it works:** Stage 1 uses classical NLP (TF-IDF extractive "
        "summarisation) to identify the most statistically important sentences "
        "locally. Stage 2 uses Google Gemini AI to restructure and enrich "
        "those findings into a coherent, readable summary. "
        "Neither technique alone produces the best result — "
        "the hybrid pipeline combines statistical precision with AI fluency."
    )

    if "study_text" not in st.session_state or not st.session_state.study_text:
        st.warning("⚠️ No study material loaded. Please go to the Home page first!")
        if st.button("⬅️ Go to Home"):
            st.session_state.page = "Home"
            st.rerun()
        return

    # Check for loaded summary from history
    if "loaded_summary" in st.session_state and st.session_state.loaded_summary:
        st.info("📚 Showing summary loaded from your history.")
        display_summary(st.session_state.loaded_summary)
        if st.button("🔄 Generate New Summary"):
            del st.session_state.loaded_summary
            st.rerun()
        return

    # ── Pipeline Diagram ──
    st.divider()
    show_pipeline_diagram()
    st.divider()

    # ── Stage 1: Local NLP ──
    st.subheader("🔬 Stage 1 — Local TF-IDF Extractive Summarisation")
    st.caption(
        "Runs entirely on the server. No internet connection or API key required. "
        "Uses Term Frequency-Inverse Document Frequency (TF-IDF) to rank "
        "every sentence in your document by statistical importance."
    )

    if "local_analysis" not in st.session_state:
        with st.spinner("⚙️ Running local NLP pipeline..."):
            st.session_state.local_analysis = run_full_local_analysis(
                st.session_state.study_text
            )

    local = st.session_state.local_analysis
    extractive = local["extractive_summary"]
    concepts = local["concepts"]
    segments = local["topic_segments"]

    # Pipeline metrics
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric(
            "Total Sentences",
            extractive.get("total_sentences", 0)
        )
    with col2:
        st.metric(
            "Sentences Selected",
            len(extractive.get("sentences", []))
        )
    with col3:
        st.metric(
            "Concepts Extracted",
            len(concepts.get("concepts", []))
        )
    with col4:
        st.metric(
            "Topic Segments",
            len(segments)
        )

    # ── Sentence Score Visualisation ──
    st.write("#### 📊 Sentence Importance Scores (TF-IDF)")
    st.caption(
        "Every sentence in your document was scored. "
        "The highlighted bars were selected for the extractive summary."
    )

    all_scores = extractive.get("all_scores", [])
    sentences = extractive.get("sentences", [])
    selected_indices = []

    if all_scores:
        # Find which sentences were selected
        from nltk.tokenize import sent_tokenize
        all_sentences = sent_tokenize(st.session_state.study_text)
        selected_indices = [
            i for i, s in enumerate(all_sentences)
            if s in sentences
        ]

        # Build dataframe for chart
        chart_data = pd.DataFrame({
            "Sentence": [f"S{i+1}" for i in range(len(all_scores))],
            "TF-IDF Score": [round(s, 4) for s in all_scores],
            "Selected": [
                "Selected ✅" if i in selected_indices else "Not Selected"
                for i in range(len(all_scores))
            ]
        })

        fig = px.bar(
            chart_data,
            x="Sentence",
            y="TF-IDF Score",
            color="Selected",
            color_discrete_map={
                "Selected ✅": "#2563EB",
                "Not Selected": "#374151"
            },
            title=f"TF-IDF Score for All {len(all_scores)} Sentences",
            height=300
        )
        fig.update_layout(
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            font=dict(color="white"),
            showlegend=True,
            xaxis=dict(showticklabels=False)
        )
        st.plotly_chart(fig, use_container_width=True)

    # ── Extracted Sentences ──
    with st.expander("📄 Extracted Sentences with Scores", expanded=True):
        st.caption(
            "These sentences scored highest in TF-IDF ranking. "
            "The score reflects how distinctive and important "
            "each sentence is relative to the whole document."
        )
        for i, sentence in enumerate(sentences, 1):
            score = extractive.get("scores", [])[i-1] \
                if i-1 < len(extractive.get("scores", [])) else 0

            col1, col2 = st.columns([5, 1])
            with col1:
                st.markdown(
                    f"<div style='background:#1E293B;padding:10px;"
                    f"border-left:3px solid #2563EB;"
                    f"border-radius:4px;margin:5px 0'>"
                    f"<small style='color:#94A3B8'>Sentence {i} — "
                    f"TF-IDF Score: {round(score, 3)}</small><br>"
                    f"{sentence}"
                    f"</div>",
                    unsafe_allow_html=True
                )
            with col2:
                st.progress(float(score))
                st.caption(f"{round(score * 100)}%")

    # ── Concept Network ──
    with st.expander("🔗 Extracted Concepts & Co-occurrence Network"):
        st.caption(
            "Key concepts identified using TF-IDF bigram extraction. "
            "Co-occurrence links show which concepts appear "
            "together in the same sentences."
        )
        top_concepts = concepts.get("concepts", [])[:10]
        if top_concepts:
            concept_cols = st.columns(5)
            for i, concept in enumerate(top_concepts):
                with concept_cols[i % 5]:
                    st.markdown(
                        f"<div style='background:#1E3A5F;padding:6px;"
                        f"border-radius:8px;text-align:center;"
                        f"margin:3px;font-size:12px'>"
                        f"🔑 {concept['term']}<br>"
                        f"<small>score: {round(concept['score'], 2)}"
                        f"</small></div>",
                        unsafe_allow_html=True
                    )

        cooccurrence = concepts.get("cooccurrence", [])
        if cooccurrence:
            st.write("**Strongest concept relationships:**")
            for pair in cooccurrence[:5]:
                strength = pair["strength"]
                bar = "█" * min(strength * 2, 10)
                col1, col2 = st.columns([3, 1])
                with col1:
                    st.write(
                        f"**{pair['term1']}** ↔ **{pair['term2']}** {bar}"
                    )
                with col2:
                    st.caption(f"co-occurs {strength}x")

    # ── Topic Segments ──
    with st.expander("📑 Automatic Topic Segmentation"):
        st.caption(
            "Document automatically divided into topic sections "
            "by detecting drops in cosine similarity between "
            "consecutive sentence groups."
        )
        for segment in segments:
            keywords = segment.get("keywords", [])
            count = segment.get("sentence_count", 0)
            col1, col2 = st.columns([3, 1])
            with col1:
                st.write(
                    f"**Topic {segment['topic_id']}:** "
                    f"{', '.join(keywords[:4]) if keywords else 'General'}"
                )
            with col2:
                st.caption(f"{count} sentences")

    st.divider()

    # ── Stage 2: AI Enhancement ──
    st.subheader("🤖 Stage 2 — Gemini AI Enhancement")
    st.caption(
        "Gemini receives the locally identified content and "
        "restructures it into a comprehensive, readable summary "
        "with titles, key points, definitions and conclusions. "
        "This stage adds semantic understanding and fluency "
        "that pure statistical methods cannot provide."
    )

    if "preprocessed" in st.session_state:
        prep = st.session_state.preprocessed
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Words Processed", prep["statistics"]["word_count"])
        with col2:
            st.metric("Readability", prep["readability"]["level"])
        with col3:
            st.metric(
                "Sections",
                f"{prep['chunk_count']} chunk(s)"
            )

        if prep["is_long_document"]:
            st.info(
                f"📄 Long document detected. TF-IDF cosine similarity "
                f"will select the most relevant section before "
                f"sending to Gemini — reducing token usage and "
                f"improving relevance."
            )

    if st.button(
        "✨ Generate AI Enhanced Summary",
        use_container_width=True
    ):
        with st.spinner(
            "🤖 Gemini is enhancing the local analysis..."
        ):
            summary, error = generate_summary(
                st.session_state.study_text
            )

            if error:
                st.error(f"❌ {error}")
                st.info(
                    "💡 The local extractive summary above "
                    "is still fully available without any API."
                )
            else:
                st.session_state.summary = summary
                st.success("✅ AI summary generated successfully!")

                # Save to database
                if user and "preprocessed" in st.session_state:
                    prep = st.session_state.preprocessed
                    doc_name = st.session_state.get(
                        "document_name", "Pasted Text"
                    )
                    if not st.session_state.get("session_id"):
                        session_id, err = save_study_session(
                            user_id=user.id,
                            document_name=doc_name,
                            word_count=prep["statistics"]["word_count"],
                            readability_level=prep["readability"]["level"],
                            keywords=prep["keywords"][:5]
                        )
                        if session_id:
                            st.session_state.session_id = session_id

                    if st.session_state.get("session_id"):
                        save_summary(
                            user.id,
                            st.session_state.session_id,
                            summary
                        )

    # Display AI summary
    if "summary" in st.session_state and st.session_state.summary:
        st.divider()
        st.subheader("📋 AI Enhanced Summary Output")
        display_summary(st.session_state.summary)

        # ── Stage 3: Resources ──
        st.divider()
        st.subheader("🔗 Stage 3 — Resource Recommendations")
        st.caption(
            "Generated from TF-IDF keywords — no additional API call. "
            "URLs constructed programmatically from extracted concepts."
        )

        if "preprocessed" in st.session_state:
            keywords = st.session_state.preprocessed["keywords"]
            title = st.session_state.summary.get(
                "title", "study topic"
            )
            resources, err = generate_resource_recommendations(
                keywords, title
            )

            if resources:
                cols = st.columns(len(resources))
                for col, (key, resource) in zip(
                    cols, resources.items()
                ):
                    with col:
                        st.markdown(
                            f"**{resource['icon']} "
                            f"[{resource['name']}]"
                            f"({resource['url']})**"
                        )
                        st.caption(resource["description"])


def show_pipeline_diagram():
    """Show a visual pipeline diagram."""
    st.subheader("🔄 Processing Pipeline")
    st.markdown("""
    <div style='display:flex;align-items:center;
    justify-content:center;flex-wrap:wrap;gap:8px;
    padding:16px;background:#0F172A;border-radius:12px'>
        <div style='background:#1E3A5F;padding:10px 16px;
        border-radius:8px;text-align:center;min-width:120px'>
            <div style='font-size:24px'>📄</div>
            <div style='color:#93C5FD;font-weight:bold'>Document</div>
            <div style='color:#64748B;font-size:11px'>PDF or Text</div>
        </div>
        <div style='color:#2563EB;font-size:24px'>→</div>
        <div style='background:#1E3A5F;padding:10px 16px;
        border-radius:8px;text-align:center;min-width:120px;
        border:2px solid #2563EB'>
            <div style='font-size:24px'>🔬</div>
            <div style='color:#93C5FD;font-weight:bold'>TF-IDF Engine</div>
            <div style='color:#64748B;font-size:11px'>Local • No API</div>
        </div>
        <div style='color:#2563EB;font-size:24px'>→</div>
        <div style='background:#1E3A5F;padding:10px 16px;
        border-radius:8px;text-align:center;min-width:120px;
        border:2px solid #2563EB'>
            <div style='font-size:24px'>📊</div>
            <div style='color:#93C5FD;font-weight:bold'>Sentence Ranking</div>
            <div style='color:#64748B;font-size:11px'>Cosine Similarity</div>
        </div>
        <div style='color:#2563EB;font-size:24px'>→</div>
        <div style='background:#1E293B;padding:10px 16px;
        border-radius:8px;text-align:center;min-width:120px;
        border:2px solid #F59E0B'>
            <div style='font-size:24px'>🤖</div>
            <div style='color:#FCD34D;font-weight:bold'>Gemini AI</div>
            <div style='color:#64748B;font-size:11px'>Restructure • Enrich</div>
        </div>
        <div style='color:#10B981;font-size:24px'>→</div>
        <div style='background:#064E3B;padding:10px 16px;
        border-radius:8px;text-align:center;min-width:120px;
        border:2px solid #10B981'>
            <div style='font-size:24px'>✅</div>
            <div style='color:#6EE7B7;font-weight:bold'>Final Summary</div>
            <div style='color:#64748B;font-size:11px'>Hybrid Output</div>
        </div>
    </div>
    """, unsafe_allow_html=True)


def display_summary(summary):
    """Display a formatted AI summary."""
    st.subheader(
        f"📚 {summary.get('title', 'Study Summary')}"
    )
    st.subheader("🔍 Overview")
    st.write(summary.get("overview", ""))
    st.divider()

    st.subheader("🎯 Key Points")
    for i, point in enumerate(summary.get("key_points", []), 1):
        st.write(f"**{i}.** {point}")
    st.divider()

    terms = summary.get("important_terms", [])
    if terms:
        st.subheader("📖 Important Terms")
        for item in terms:
            with st.expander(f"📌 {item.get('term', '')}"):
                st.write(item.get("definition", ""))
        st.divider()

    st.subheader("💡 Conclusion")
    st.info(summary.get("conclusion", ""))
