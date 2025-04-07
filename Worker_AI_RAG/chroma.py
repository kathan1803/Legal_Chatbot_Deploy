import json
import os
import chromadb
from chromadb.config import Settings


script_dir = os.path.dirname(os.path.abspath(__file__))
file_path = os.path.join(script_dir, "embedding_results.json")

# Load the embedding results
with open(file_path, "r") as f:
    embedding_results = json.load(f)

# Initialize ChromaDB client - Updated to use the new client initialization
chroma_client = chromadb.PersistentClient(path="./chroma_db")

# Create a collection
collection_name = "constitution_embeddings"
collection = chroma_client.get_or_create_collection(name=collection_name)

print(f"Created collection: {collection_name}")

# Process and add each document embedding
for item in embedding_results:
    filename = item["filename"]
    
    # Extract embedding data - adjusting for the actual structure in your file
    try:
        embedding_data = item["response"]["result"]["data"][0]
        
        # For document content, you would ideally have the original text
        # but since we just have the embedding, we'll use the filename for now
        document_content = f"Embedding for {filename}"
        
        # Store in ChromaDB
        try:
            collection.add(
                embeddings=[embedding_data],
                documents=[document_content],
                metadatas=[{"source": filename}],
                ids=[filename.replace(".pdf", "")]
            )
            print(f"Successfully stored embedding for {filename}")
        except Exception as e:
            print(f"Error storing embedding for {filename}: {e}")
    except KeyError as e:
        print(f"Skipping {filename} because could not extract embedding data: {e}")
        print(f"Response structure: {item['response']}")

print("\nEmbeddings stored successfully in ChromaDB!")
print(f"Collection Info: {collection.count()} documents stored")