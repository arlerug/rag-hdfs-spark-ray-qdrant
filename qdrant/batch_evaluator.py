

import json
import time
from sentence_transformers import SentenceTransformer
from qdrant_client import QdrantClient
import openai

# Configurazione
COLLECTION_NAME = "arxiv"
QDRANT_HOST = "192.168.100.10"
QDRANT_PORT = 6333
TOP_K = 7
MAX_CONTEXT_CHARS = 4000

openai.api_key = "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"
openai.api_base = "https://openrouter.ai/api/v1"

# Domande da porre
questions = [
    "What is a transformer?",
    "What is an agent?",
    "what is grounding?",
    "How does a RAG work?",
    "What is overfitting?",
    "What is a large language model?",
    "What are hallucinations?",
    "How does one do fine-tuning?",
    "What is overfitting?",
    "What is the future of ai?"
]

# Inizializzazione modelli e client
model = SentenceTransformer("all-MiniLM-L6-v2")
client = QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT)

# Funzioni
def get_query_embedding(text: str) -> list:
    return model.encode(text).tolist()

def ask_model(prompt: str, model_name: str = "google/gemma-3n-e4b-it:free", max_tokens: int = 512) -> str:
    try:
        response = openai.ChatCompletion.create(
            model=model_name,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=max_tokens,
            temperature=0.7
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"Error: {e}"

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

# Esecuzione batch
results = []

for idx, q in enumerate(questions, 1):
    print(f"[{idx}/{len(questions)}] Processing: {q}")
    embedding = get_query_embedding(q)
    search_results = client.search(
        collection_name=COLLECTION_NAME,
        query_vector=embedding,
        limit=TOP_K
    )

    context_chunks = [r.payload.get("chunk", "") for r in search_results if r.payload.get("chunk", "")]
    context = "\n\n".join(context_chunks)
    if len(context) > MAX_CONTEXT_CHARS:
        context = context[:MAX_CONTEXT_CHARS] + "..."

    # Risposte
    response_no_context = ask_model(q)
    rag_prompt = f"""
You are an AI assistant specialized in reading and summarizing scientific papers.

Use the information provided in the context to answer the question as thoroughly and precisely as possible. 
Explain all relevant aspects you can infer from the context.

If the answer is not found in the context, clearly state that the information is missing. 
Do not invent information.

Context:
{context}

Question:
{q}

Answer:
"""
    response_rag = ask_model(rag_prompt)

    # Valutazione
    eval_no_context = evaluate_answer(q, response_no_context, context)
    eval_with_context = evaluate_answer(q, response_rag, context)

    results.append({
        "question": q,
        "no_context": {
            "answer": response_no_context,
            "evaluation": eval_no_context
        },
        "with_context": {
            "answer": response_rag,
            "evaluation": eval_with_context
        }
    })

    time.sleep(2)  # throttling

# Salva su file
with open("llm_as_a_judge.json", "w") as f:
    json.dump(results, f, indent=2)

print("✅ Risultati salvati su llm_as_a_judge.json")
