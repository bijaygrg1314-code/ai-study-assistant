"""
chat.py — Document Q&A Chat Interface.
Uses local TF-IDF retrieval (no API) to find relevant passages,
then optionally uses Gemini to refine the answer.
This demonstrates RAG (Retrieval Augmented Generation).
"""

import streamlit as st
from utils.local_nlp import (
    build_knowledge_base,
    answer_question_locally,
    extract_concepts
)
from utils.gemini_client import call_gemini_with_retry


def show_chat_page(user=None):
    st.title("💬 Document Q&A")
    st.write(
        "Ask any question about your uploaded study material. "
        "The app finds the answer using local TF-IDF retrieval — "
        "no internet required for the search."
    )

    if "study_text" not in st.session_state or not st.session_state.study_text:
        st.warning("⚠️ No study material loaded. Please go to the Home page first!")
        return

    # Build knowledge base if not already built
    if "knowledge_base" not in st.session_state or st.session_state.knowledge_base is None:
        with st.spinner("🔧 Building local knowledge base from your document..."):
            st.session_state.knowledge_base = build_knowledge_base(
                st.session_state.study_text
            )
        st.success("✅ Knowledge base built! You can now ask questions.")

    kb = st.session_state.knowledge_base

    if not kb:
        st.error("Could not build knowledge base. Please try a different document.")
        return

    # Show knowledge base stats
    with st.expander("🔬 Knowledge Base Details", expanded=False):
        st.write(f"**Total passages indexed:** {len(kb['passages'])}")
        st.write(f"**Total sentences:** {len(kb['sentences'])}")
        st.write(
            "**Method:** TF-IDF vectorisation with cosine similarity retrieval"
        )
        st.write(
            "**How it works:** Your document is split into overlapping "
            "passages and vectorised using Term Frequency-Inverse Document "
            "Frequency (TF-IDF). When you ask a question, it is vectorised "
            "using the same vocabulary and the most similar passages are "
            "retrieved using cosine similarity — entirely locally."
        )

    st.divider()

    # Initialise chat history
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []

    # Answer mode selection
    col1, col2 = st.columns(2)
    with col1:
        answer_mode = st.radio(
            "Answer mode",
            ["🔍 Local Only (TF-IDF)", "🤖 Local + AI Refinement"],
            help="Local Only uses pure TF-IDF retrieval. "
                 "AI Refinement passes the retrieved passage to "
                 "Gemini for a more natural answer."
        )
    with col2:
        if st.button("🗑️ Clear Chat History", use_container_width=True):
            st.session_state.chat_history = []
            st.rerun()

    st.divider()

    # Display chat history
    for message in st.session_state.chat_history:
        if message["role"] == "user":
            with st.chat_message("user"):
                st.write(message["content"])
        else:
            with st.chat_message("assistant"):
                st.write(message["content"])
                if message.get("confidence"):
                    st.caption(
                        f"🎯 Retrieval confidence: {message['confidence_label']} "
                        f"({round(message['confidence'] * 100, 1)}%) | "
                        f"Source: {message.get('source', 'Local TF-IDF')}"
                    )
                if message.get("passages"):
                    with st.expander("📄 Source passages from document"):
                        for i, p in enumerate(
                            message["passages"][:2], 1
                        ):
                            st.markdown(
                                f"**Passage {i} "
                                f"(similarity: {round(p['confidence'] * 100, 1)}%):**"
                            )
                            st.write(p["passage"])
                            st.divider()

    # Question input
    question = st.chat_input(
        "Ask a question about your document..."
    )

    if question:
        # Add user message to history
        st.session_state.chat_history.append({
            "role": "user",
            "content": question
        })

        with st.chat_message("user"):
            st.write(question)

        with st.chat_message("assistant"):
            with st.spinner("🔍 Searching document..."):

                # Step 1: Local TF-IDF retrieval
                local_result = answer_question_locally(
                    question, kb, top_k=3
                )

                if not local_result or not local_result.get("found"):
                    response = (
                        "I could not find relevant information about "
                        "that in your document. Try rephrasing your question "
                        "or ask about a topic covered in the material."
                    )
                    st.write(response)
                    st.session_state.chat_history.append({
                        "role": "assistant",
                        "content": response,
                        "confidence": 0,
                        "confidence_label": "Not found",
                        "source": "Local TF-IDF"
                    })

                else:
                    top_passage = local_result["top_passage"]
                    confidence = local_result["confidence"]
                    confidence_label = local_result["confidence_label"]

                    if "Local Only" in answer_mode:
                        # Return the raw retrieved passage
                        response = (
                            f"**Based on your document:**\n\n{top_passage}"
                        )
                        source = "Local TF-IDF"
                        st.write(response)

                    else:
                        # Refine with Gemini
                        with st.spinner("🤖 Refining answer with AI..."):
                            prompt = f"""
                            A student asked: "{question}"

                            The most relevant passage from their study document is:
                            "{top_passage}"

                            Using ONLY the information in the passage above,
                            provide a clear, concise answer to the student's question.
                            If the passage does not contain enough information to
                            answer the question fully, say so honestly.
                            Do not add information not present in the passage.
                            """

                            refined, error = call_gemini_with_retry(prompt)

                            if error or not refined:
                                response = (
                                    f"**Based on your document:**\n\n{top_passage}"
                                )
                                source = "Local TF-IDF (AI unavailable)"
                            else:
                                response = refined
                                source = "Local TF-IDF + Gemini refinement"

                        st.write(response)

                    # Show confidence and sources
                    st.caption(
                        f"🎯 Retrieval confidence: {confidence_label} "
                        f"({round(confidence * 100, 1)}%) | "
                        f"Source: {source}"
                    )

                    with st.expander("📄 Source passages from document"):
                        for i, p in enumerate(
                            local_result["passages"][:2], 1
                        ):
                            st.markdown(
                                f"**Passage {i} "
                                f"(similarity: "
                                f"{round(p['confidence'] * 100, 1)}%):**"
                            )
                            st.write(p["passage"])
                            st.divider()

                    # Add to chat history
                    st.session_state.chat_history.append({
                        "role": "assistant",
                        "content": response,
                        "confidence": confidence,
                        "confidence_label": confidence_label,
                        "passages": local_result["passages"],
                        "source": source
                    })

    # Suggested questions based on document keywords
    if not st.session_state.chat_history:
        st.divider()
        st.subheader("💡 Suggested Questions")
        st.write("Based on your document, try asking:")

        if "preprocessed" in st.session_state:
            keywords = st.session_state.preprocessed.get("keywords", [])
            suggestions = [
                f"What is {keywords[0]}?" if len(keywords) > 0 else "What is the main topic?",
                f"How does {keywords[1]} work?" if len(keywords) > 1 else "How does this work?",
                f"What is the relationship between {keywords[0]} and {keywords[2]}?" if len(keywords) > 2 else "What are the key concepts?",
                "What are the most important points in this document?",
                "Summarise the main conclusions."
            ]
        else:
            suggestions = [
                "What is the main topic of this document?",
                "What are the key concepts covered?",
                "What are the most important conclusions?",
                "How does the main concept work?",
                "What are the limitations discussed?"
            ]

        cols = st.columns(2)
        for i, suggestion in enumerate(suggestions[:4]):
            with cols[i % 2]:
                if st.button(
                    suggestion,
                    key=f"suggestion_{i}",
                    use_container_width=True
                ):
                    st.session_state.chat_history.append({
                        "role": "user",
                        "content": suggestion
                    })
                    st.rerun()
