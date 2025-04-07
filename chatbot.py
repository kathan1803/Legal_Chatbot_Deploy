import streamlit as st
from prompt_utils import usecase_prompt
import os
from dotenv import load_dotenv
from groq import Groq # type: ignore
import certifi
import httpx
import io
import PyPDF2
import docx
import requests
import chromadb

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
        st.error(f"Error communicating with Groq API: {str(e)}")
        return None

def load_css():
    return """
                <style>
        /* Ensure full screen with no scroll */
        body {
            margin: 0;  /* Remove any default margin */
            padding: 0;  /* Remove any default padding */
            height: 100vh;  /* Full viewport height */
            background-color: #f4f6f9;  /* Light, soft background for a clean look */
            font-family: 'Arial', sans-serif;  /* Clean, modern font */
            display: flex;
            flex-direction: column;
        }

        /* Chat container that fills the screen with auto-scrolling and increased width */
        .chat-container {
            flex-grow: 1;  /* Takes up remaining space */
            overflow-y: auto;
            padding: 10px;
            border: 1px solid #e0e0e0;  /* Soft gray border for subtlety */
            border-radius: 10px;
            margin-bottom: 20px;
            box-sizing: border-box;  /* Ensures padding does not affect the scroll */
            display: flex;
            flex-direction: column;
            justify-content: flex-end;  /* Align messages to the bottom */
            max-width: 90vw; 
            margin-left: auto;  /* Center the chat container horizontally */
            margin-right: auto;
        }

        /* User message bubble styling */
        .chat-bubble-user {
            margin: 10px 0 10px auto;
            padding: 12px;
            border-radius: 15px;
            background-color: #757a7a;  /* Light gray for user messages */
            color: #eeeeee;  /* Light text for contrast */
            max-width: 70%;
            text-align: left;
            box-shadow: 0 2px 5px rgba(0, 0, 0, 0.1);  /* Subtle shadow for depth */
        }

        /* AI message bubble styling */
        .chat-bubble-ai {
            margin: 10px 0;
            padding: 12px;
            border-radius: 15px;
            background-color: #4e6e5b;  /* Slightly darker green for AI messages */
            color: #eeeeee;  /* Light text for contrast */
            max-width: 70%;
            text-align: left;
            box-shadow: 0 2px 5px rgba(0, 0, 0, 0.1);  /* Subtle shadow for depth */
        }

        /* Input field inside chat container */
        .chat-input-container {
            display: flex;
            justify-content: center;
            padding-top: 10px; /* To ensure some space between chat and input */
        }

        .stTextInput>div>div>input {
            border-radius: 20px;
            width: 90%;  /* Adjust width to fit inside the chat window */
        }

        /* Focus effect on input field */
        .stTextInput>div>div>input:focus {
            outline: none;  /* Remove default focus outline */
        }
        </style>
    """

def initialize_session_state():
    if "conversation_history" not in st.session_state:
        # Add initial greeting from the chatbot
        st.session_state.conversation_history = [
            {"role": "system", "content": usecase_prompt()},
            {"role": "assistant", "content": "Hello! I am your AI Assistant. How can I help you today?"}
        ]
    if "user_input" not in st.session_state:
        st.session_state.user_input = ""

def display_chat_history():
    chat_history = '<div class="chat-container">'
    for message in st.session_state.conversation_history:
        if message["role"] == "user":
            chat_history += f'<div class="chat-bubble-user">You :  {message["content"]}</div>'
        elif message["role"] == "assistant":
            chat_history += f'<div class="chat-bubble-ai">AI Assistant :  {message["content"]}</div>'
    chat_history += "</div>"
    st.markdown(chat_history, unsafe_allow_html=True)

def handle_user_input(client):
    if st.session_state.user_input:
        user_message = st.session_state.user_input
        st.session_state.conversation_history.append(
            {"role": "user", "content": user_message}
        )
        
        with st.spinner("AI is thinking..."):
            ai_response = fetch_ai_response(client, st.session_state.conversation_history)
            
        if ai_response:
            st.session_state.conversation_history.append(
                {"role": "assistant", "content": ai_response}
            )
        
        # Clear the input after submitting
        st.session_state.user_input = ""

def process_uploaded_file(uploaded_file):
    file_extension = uploaded_file.type
    
    # Handle text file (.txt)
    if file_extension == "text/plain":
        return uploaded_file.read().decode("utf-8")
    
    # Handle PDF file (.pdf)
    elif file_extension == "application/pdf":
        return extract_text_from_pdf(uploaded_file)
    
    # Handle DOCX file (.docx)
    elif file_extension == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
        return extract_text_from_docx(uploaded_file)

    return "Unsupported file type."

def extract_text_from_image(uploaded_file):
    image = Image.open(image_path)
    text = pytesseract.image_to_string(image)
    return text

def extract_text_from_pdf(uploaded_file):
    pdf_reader = PyPDF2.PdfReader(io.BytesIO(uploaded_file.read()))
    text = ""
    for page in pdf_reader.pages:
        text += page.extract_text()
    return text

def extract_text_from_docx(uploaded_file):
    doc = docx.Document(io.BytesIO(uploaded_file.read()))
    text = ""
    for para in doc.paragraphs:
        text += para.text + "\n"
    return text

def main():
    st.set_page_config(page_title="AI Chatbot", page_icon="💬")
    
    # Load API key
    api_key = os.getenv("GROQ_API_KEY")
    
    if not api_key:
        st.error("API key is missing. Please set the 'GROQ_API_KEY' in your .env file.")
        return
    
    # Initialize Groq client
    client = setup_groq_client(api_key)
    
    # Load custom CSS
    st.markdown(load_css(), unsafe_allow_html=True)
    
    # Initialize session state
    initialize_session_state()
    
    # App title
    st.title("Legal Chatbot")
    
    # Display chat history
    display_chat_history()
    
    # Chat input
    st.text_input(
        "",  # Empty string removes the default text
        key="user_input",
        on_change=handle_user_input,
        args=(client,),
        placeholder="Type your message and press Enter..."
    )
    
    uploaded_file = st.file_uploader("Please upload your legal document (TXT, PDF, or DOCX):", type=["txt", "pdf", "docx"])
    if uploaded_file:
        extracted_text = process_uploaded_file(uploaded_file)
        if st.button("Send to Chatbot"):
            st.session_state.conversation_history.append(
                {"role": "user", "content": extracted_text}
            )
            
            with st.spinner("AI is analyzing the document..."):
                ai_response = fetch_ai_response(client, st.session_state.conversation_history)
        
            if ai_response:
                st.session_state.conversation_history.append(
                    {"role": "assistant", "content": ai_response}
                )


if __name__ == "__main__":
    main()
