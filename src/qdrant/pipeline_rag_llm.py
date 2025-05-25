import os
import json
import requests
import streamlit as st
from sentence_transformers import SentenceTransformer
from qdrant_client import QdrantClient
import openai
import matplotlib.pyplot as plt
import re

COLLECTION_NAME = "arxiv"
QDRANT_HOST = "192.168.100.10"
QDRANT_PORT = 6333
TOP_K = 7
MAX_CONTEXT_CHARS = 4000

openai.api_key = "your-api-key"
openai.api_base = "https://openrouter.ai/api/v1"

st.set_page_config(page_title="RAG with Qdrant & OpenRouter", layout="wide")

@st.cache_resource
def load_model():
    return SentenceTransformer("all-MiniLM-L6-v2")

@st.cache_resource
def get_qdrant_client():
    return QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT)

model = load_model()
client = get_qdrant_client()

def get_query_embedding(text: str) -> list:
    return model.encode(text).tolist()

def get_ollama_response(prompt: str, max_tokens: int = 512) -> str:
    try:
        response = openai.ChatCompletion.create(
            model="google/gemma-3n-e4b-it:free",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=max_tokens,
            temperature=0.7,
            stream=True
        )

        collected = ""
        response_placeholder = st.empty()
        partial_text = ""

        for chunk in response:
            if 'choices' in chunk:
                delta = chunk.choices[0].delta
                content = delta.get("content", "")
                partial_text += content
                response_placeholder.markdown(partial_text)
                collected += content

        return collected.strip()

    except Exception as e:
        return f"Error calling OpenRouter: {e}"

def evaluate_answer(question, answer, context=""):
    prompt = f"""
You are evaluating the quality of an answer in relation to a specific context of retrieved documents.

The documents provided define the intended domain of the question. Your evaluation must consider not only whether the answer is accurate and well-written, but especially whether it is grounded in the given context.

Pay extra attention to the Relevance score: it must reflect how much the answer aligns with the topic and content of the retrieved documents. If the answer talks about something unrelated or not found in the context, give a low Relevance score.

Evaluate using the following 4 criteria, assigning a rating from 1 to 5 for each:

1. Relevance to the context  
2. Accuracy  
3. Completeness  
4. Clarity  

Then give an Overall score from 1 to 5, where Relevance has more weight than the other criteria.

---
Question: {question}

Context (retrieved documents):
{context}

Answer:
{answer}

---
Respond in this format:

- Relevance: 2/5  
- Accuracy: 1/5  
- Completeness: 0/5  
- Clarity: 5/5  
- Overall: 3/5  

Explanation: ...
"""
    try:
        response = openai.ChatCompletion.create(
            model="meta-llama/llama-3.3-8b-instruct:free",
            messages=[{"role": "user", "content": prompt}],
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"Evaluation error:\n{e}"

st.title("RAG with Qdrant + Gemma (OpenRouter)")
query = st.text_input("Enter your question", placeholder="e.g., What is a transformer?")

if st.button("Search"):
    if not query.strip():
        st.warning("Please enter a valid question.")
        st.stop()

    with st.spinner("Retrieving documents and computing embeddings..."):
        embedding = get_query_embedding(query)
        results = client.search(
            collection_name=COLLECTION_NAME,
            query_vector=embedding,
            limit=TOP_K
        )

        context_chunks = []
        references = []

        for r in results:
            chunk = r.payload.get("chunk", "")
            if chunk:
                context_chunks.append(chunk)
                references.append({
                    "id": r.payload.get("id", "N/A"),
                    "title": r.payload.get("title", "N/A"),
                    "authors": r.payload.get("authors", "N/A"),
                    "year": r.payload.get("year", "N/A")
                })

        full_context = "\n\n".join(context_chunks)
        if len(full_context) > MAX_CONTEXT_CHARS:
            full_context = full_context[:MAX_CONTEXT_CHARS] + "..."

    st.subheader("Answer (without context)")
    with st.spinner("Generating..."):
        response_no_context = get_ollama_response(query)

    st.subheader("Answer (with context)")
    rag_prompt = f"""
You are an AI assistant specialized in reading and summarizing scientific papers.

Use the information provided in the context to answer the question as thoroughly and precisely as possible. 
Explain all relevant aspects you can infer from the context.

If the answer is not found in the context, clearly state that the information is missing. 
Do not invent information.

Context:
{full_context}

Question:
{query}

Answer:
"""
    with st.spinner("Generating..."):
        response_rag = get_ollama_response(rag_prompt)

    st.subheader("Evaluation (via LLaMA 3 on OpenRouter)")

    with st.spinner("Evaluating response without context..."):
        rating_no_context = evaluate_answer(query, response_no_context, full_context)
    st.markdown("No-context answer evaluation:")
    st.success(rating_no_context)

    with st.spinner("Evaluating response with context (RAG)..."):
        rating_with_context = evaluate_answer(query, response_rag, full_context)
    st.markdown("RAG answer evaluation:")
    st.success(rating_with_context)

    # Parse evaluation text to extract scores
    def extract_scores(text):
        scores = {}
        for line in text.splitlines():
            match = re.match(r"- (\w+): (\d)/5", line.strip())
            if match:
                scores[match[1]] = int(match[2])
        return scores

    scores_no = extract_scores(rating_no_context)
    scores_with = extract_scores(rating_with_context)

    metrics = list(scores_no.keys())
    vals_no = [scores_no.get(m, 0) for m in metrics]
    vals_with = [scores_with.get(m, 0) for m in metrics]

    fig, ax = plt.subplots(figsize=(8, 4))
    x = range(len(metrics))
    bar_width = 0.35

    ax.bar([i - bar_width/2 for i in x], vals_no, bar_width, label="No Context")
    ax.bar([i + bar_width/2 for i in x], vals_with, bar_width, label="With Context")

    ax.set_xticks(x)
    ax.set_xticklabels(metrics)
    ax.set_ylim(0, 5)
    ax.set_ylabel("Score")
    ax.set_title("Evaluation Comparison")
    ax.legend()

    st.subheader("Evaluation Comparison Chart")
    st.pyplot(fig)

    st.subheader("Retrieved documents")
    for ref in references:
        st.markdown(f"- **{ref['title']}** ({ref['year']}) — *{ref['authors']}* — `ID: {ref['id']}`")
