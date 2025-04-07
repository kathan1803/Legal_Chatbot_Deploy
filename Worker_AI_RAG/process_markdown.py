import os
import json
import requests
import chromadb
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


# ChromaDB & Cloudflare setup
chroma_client = chromadb.PersistentClient(path="./chroma_db")
collection = chroma_client.get_collection(name="constitution_embeddings")

def get_embedding(text):
    model = "@cf/baai/bge-large-en-v1.5"
    url = f"https://api.cloudflare.com/client/v4/accounts/{os.getenv('CLOUDFLARE_ACCOUNT_ID')}/ai/run/{model}"
    headers = {
        "Authorization": f"Bearer {os.getenv('CLOUDFLARE_API_TOKEN')}",
        "Content-Type": "application/json"
    }
    response = requests.post(url, headers=headers, json={"text": text})
    result = response.json()
    if result.get("success") and result.get("result") and result["result"].get("data"):
        return result["result"]["data"][0]
    return None

def get_context_from_chroma(question):
    embedding = get_embedding(question)
    if not embedding:
        return "No relevant context found."
    result = collection.query(query_embeddings=[embedding], n_results=3)
    if result["documents"]:
        return "\n\n".join(result["documents"][0])
    return "No relevant documents found."

CLOUDFLARE_API_TOKEN = os.getenv("CLOUDFLARE_API_TOKEN")
CLOUDFLARE_ACCOUNT_ID = os.getenv("CLOUDFLARE_ACCOUNT_ID")

# Initialize ChromaDB client
chroma_client = chromadb.PersistentClient(path="./chroma_db")
collection = chroma_client.get_collection(name="constitution_embeddings")

def get_embedding(text):
    """Generate embedding for text using Cloudflare AI API"""
    model = "@cf/baai/bge-large-en-v1.5"
    url = f"https://api.cloudflare.com/client/v4/accounts/{CLOUDFLARE_ACCOUNT_ID}/ai/run/{model}"
    
    payload = json.dumps({"text": text})
    headers = {
        "Authorization": f"Bearer {CLOUDFLARE_API_TOKEN}",
        "Content-Type": "application/json"
    }
    
    response = requests.request(method="POST", url=url, headers=headers, data=payload)
    result = response.json()
    
    if result.get("success") and result.get("result") and result["result"].get("data"):
        return result["result"]["data"][0]
    else:
        print(f"Error getting embedding: {result.get('errors', 'Unknown error')}")
        return None

def generate_answer(question, context):
    """Generate an answer using Cloudflare AI API based on context"""
    model = "@cf/meta/llama-3.1-8b-instruct"  # You might need to adjust this based on available models
    url = f"https://api.cloudflare.com/client/v4/accounts/{CLOUDFLARE_ACCOUNT_ID}/ai/run/{model}"
    
    prompt = f"""
    You are a legal assistant answering questions based only on the Indian Constitution.
    Use the following context to answer the question. Do not use any external knowledge.

    If the answer is not found in the context, respond with:
    "The answer is not available in the provided context."

    Context:
    {context}

    Question: {question}

    Answer:
    """
    
    payload = json.dumps({"prompt": prompt})
    headers = {
        "Authorization": f"Bearer {CLOUDFLARE_API_TOKEN}",
        "Content-Type": "application/json"
    }
    
    response = requests.request(method="POST", url=url, headers=headers, data=payload)
    result = response.json()
    
    if result.get("success") and result.get("result"):
        return result["result"]
    else:
        print(f"Error generating answer: {result.get('errors', 'Unknown error')}")
        return "I couldn't generate an answer based on the provided context."

def query_legal_assistant(question):
    """Main function to query the legal assistant"""
    # Step 1: Convert question to embedding
    question_embedding = get_embedding(question)
    if not question_embedding:
        return "Sorry, I couldn't process your question."
    
    # Step 2: Query ChromaDB for similar documents
    query_results = collection.query(
        query_embeddings=[question_embedding],
        n_results=3  # Retrieve top 3 most relevant documents
    )
    
    # Step 3: Extract relevant documents and construct context
    if not query_results["documents"]:
        return "No relevant information found in the database."
    
    context = "\n\n".join(query_results["documents"][0])
    
    # Step 4: Generate response using LLM
    answer = generate_answer(question, context)
    
    return answer

# Interactive query loop
if __name__ == "__main__":
    print("Legal Assistant Bot (type 'exit' to quit)")
    print("----------------------------------------")
    
    while True:
        user_question = input("\nYour question: ")
        if user_question.lower() in ["exit", "quit"]:
            break
            
        print("\nSearching for relevant information...")
        response = query_legal_assistant(user_question)
        print("\nAnswer:")
        print(response)