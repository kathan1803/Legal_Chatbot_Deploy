import os
import json
import requests
import fitz  # PyMuPDF
from dotenv import load_dotenv

load_dotenv()

CLOUDFLARE_API_TOKEN = os.getenv("CLOUDFLARE_API_TOKEN")
CLOUDFLARE_ACCOUNT_ID = os.getenv("CLOUDFLARE_ACCOUNT_ID")

path = "./Constitution"

contents = []
filenames = []

for filename in os.listdir(path):
    if filename.endswith(".pdf"):
        pdf_path = os.path.join(path, filename)
        doc = fitz.open(pdf_path)  # Open PDF
        text = "\n".join([page.get_text() for page in doc])  # Extract text from all pages
        contents.append({"filename": filename, "text": text})  # Store filename with text

# Cloudflare AI API Endpoint
model = "@cf/baai/bge-large-en-v1.5"
url = f"https://api.cloudflare.com/client/v4/accounts/{CLOUDFLARE_ACCOUNT_ID}/ai/run/{model}"

# Sending each document separately (if required)
results = []
for doc in contents:
    payload = json.dumps({"text": doc["text"]})
    headers = {
        "Authorization": f"Bearer {CLOUDFLARE_API_TOKEN}",
        "Content-Type": "application/json"
    }

    response = requests.request(method="POST",url=url, headers=headers, data=payload)

    try:
        result = response.json()
        results.append({"filename": doc["filename"], "response": result})
    except json.JSONDecodeError:
        results.append({"filename": doc["filename"], "response": "Invalid JSON response from API"})

# Print results
print(json.dumps(results, indent=4))
