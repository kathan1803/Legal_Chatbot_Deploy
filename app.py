from flask import Flask, request, jsonify
from flask_cors import CORS
import os
from dotenv import load_dotenv
from groq import Groq
import certifi
import httpx
import io
import PyPDF2
import docx
import requests
import chromadb
from werkzeug.utils import secure_filename
import tempfile
import os.path

# Import your prompt utility
from prompt_utils import usecase_prompt

# Load environment variables
load_dotenv()

app = Flask(__name__)
CORS(app, origins=["https://legal-chatbot-deploy-frontend.onrender.com"])  # Enable CORS for all routes

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

# Function to initialize the Groq client
def setup_groq_client(api_key):
    # Configure SSL certificate
    os.environ['SSL_CERT_FILE'] = certifi.where()
    
    # Create httpx client with SSL verification
    http_client = httpx.Client(verify=certifi.where())
    
    # Initialize Groq client with custom HTTP client
    return Groq(api_key=api_key, http_client=http_client)

def fetch_ai_response(client, conversation_history):
    try:
        # Get the last user message
        last_user_message = next((m["content"] for m in reversed(conversation_history) if m["role"] == "user"), "")
        
        # Retrieve context from ChromaDB
        context = get_context_from_chroma(last_user_message)

        # Enrich the user message with ChromaDB context
        context_prefixed_message = f"""Use the following legal context to answer the user's question:

Context:
{context}

Question:
{last_user_message}
"""

        # Replace the last user message with the enriched one
        modified_history = [
            m if m["role"] != "user" or m["content"] != last_user_message
            else {"role": "user", "content": context_prefixed_message}
            for m in conversation_history
        ]

        # Prepend system prompt from usecase_prompt
        system_prompt = {"role": "system", "content": usecase_prompt()}
        final_history = [system_prompt] + modified_history

        # Send to Groq
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=final_history
        )

        return response.choices[0].message.content

    except Exception as e:
        print(f"Error communicating with Groq API: {str(e)}")
        return None

def extract_text_from_pdf(file_path):
    with open(file_path, 'rb') as file:
        pdf_reader = PyPDF2.PdfReader(file)
        text = ""
        for page in pdf_reader.pages:
            text += page.extract_text()
    return text

def extract_text_from_docx(file_path):
    doc = docx.Document(file_path)
    text = ""
    for para in doc.paragraphs:
        text += para.text + "\n"
    return text

def process_uploaded_file(file_path, file_type):
    if file_type == "text/plain":
        with open(file_path, 'r') as file:
            return file.read()
    
    elif file_type == "application/pdf":
        return extract_text_from_pdf(file_path)
    
    elif file_type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
        return extract_text_from_docx(file_path)

    return "Unsupported file type."

# Initialize Groq client
groq_client = setup_groq_client(os.getenv("GROQ_API_KEY"))

@app.route('/api/chat', methods=['POST'])
def chat():
    data = request.json
    conversation_history = data.get('conversation_history', [])
    
    if not conversation_history or conversation_history[-1]['role'] != 'user':
        return jsonify({"error": "Invalid conversation history"}), 400
    
    # Add instruction to preserve formatting in the system prompt
    last_system_prompt_index = -1
    for i, msg in enumerate(conversation_history):
        if msg['role'] == 'system':
            last_system_prompt_index = i
    
    if last_system_prompt_index >= 0:
        # Update existing system prompt
        conversation_history[last_system_prompt_index]['content'] += "\n\nPlease ensure your response preserves formatting like spacing, indentation, and structure, especially for content like emails, code, or formal documents. Use proper paragraph breaks and maintain the intended layout."
    else:
        # Add new system prompt at the beginning
        formatting_prompt = {"role": "system", "content": usecase_prompt() + "\n\nPlease ensure your response preserves formatting like spacing, indentation, and structure, especially for content like emails, code, or formal documents. Use proper paragraph breaks and maintain the intended layout."}
        conversation_history.insert(0, formatting_prompt)

    ai_response = fetch_ai_response(groq_client, conversation_history)
    
    if not ai_response:
        return jsonify({"error": "Failed to get AI response"}), 500
    
    return jsonify({
        "response": ai_response
    })

@app.route('/api/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({"error": "No file part"}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400
    
    conversation_history = request.form.get('conversation_history', '[]')
    import json
    try:
        conversation_history = json.loads(conversation_history)
    except json.JSONDecodeError:
        conversation_history = []
    
    # Create temp file
    temp_dir = tempfile.gettempdir()
    filename = secure_filename(file.filename)
    file_path = os.path.join(temp_dir, filename)
    file.save(file_path)
    
    # Process the file
    file_type = file.content_type
    extracted_text = process_uploaded_file(file_path, file_type)

    system_prompt_added = False
    for i, msg in enumerate(conversation_history):
        if msg['role'] == 'system':
            conversation_history[i]['content'] += "\n\nPlease ensure your response preserves formatting like spacing, indentation, and structure, especially for content like emails, code, or formal documents."
            system_prompt_added = True
            break
    
    if not system_prompt_added:
        formatting_prompt = {"role": "system", "content": usecase_prompt() + "\n\nPlease ensure your response preserves formatting like spacing, indentation, and structure, especially for content like emails, code, or formal documents."}
        conversation_history.insert(0, formatting_prompt)
    
    # Remove temp file
    os.remove(file_path)
    
    # Add the extracted text as a user message
    conversation_history.append({"role": "user", "content": extracted_text})
    
    # Get AI response
    ai_response = fetch_ai_response(groq_client, conversation_history)
    
    if not ai_response:
        return jsonify({"error": "Failed to get AI response"}), 500
    
    return jsonify({
        "extracted_text": extracted_text,
        "ai_response": ai_response
    })

@app.route('/api/health', methods=['GET'])
def health_check():
    return jsonify({"status": "ok"})

@app.route('/')
def index():
    return jsonify({
        "status": "online",
        "message": "Legal Chatbot API is running. Available endpoints: /api/chat, /api/upload, /api/health"
    })

if __name__ == '__main__':
    app.run(debug=True, port=5000)