import time
from google import genai
from google.genai import types
import os

import requests
import tempfile
import os
from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)

def process_pdf(url: str, query: str) -> str:
    response = requests.get(url, timeout=30, stream=True)
    response.raise_for_status()
    
    # Verifică că e PDF
    content_type = response.headers.get('Content-Type', '')
    if 'pdf' not in content_type.lower() and not url.lower().endswith('.pdf'):
        logger.warning(f"URL-ul nu pare să fie un PDF. Content-Type: {content_type}")
    
    # Salvează în fișier temporar
    with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as temp_file:
        temp_pdf_path = temp_file.name
        for chunk in response.iter_content(chunk_size=8192):
            temp_file.write(chunk)
    
    client = genai.Client(api_key=os.getenv("GENAI_API_KEY"))
    store = client.file_search_stores.create()

    upload_op = client.file_search_stores.upload_to_file_search_store(
        file_search_store_name=store.name,
        file=temp_pdf_path
    )

    while not upload_op.done:
        time.sleep(5)
        upload_op = client.operations.get(upload_op)

    # Use the file search store as a tool in your generation call
    response = client.models.generate_content(
        model='gemini-2.5-flash',
        contents='Extrage-mi informații financiare din documentul încărcat si formateaza-le ca un tabel.',
        config=types.GenerateContentConfig(
            tools=[types.Tool(
                file_search=types.FileSearch(
                    file_search_store_names=[store.name]
                )
            )]
        )
    )
    return response.text

test_url = "https://corporate.mcdonalds.com/content/dam/sites/corp/nfl/pdf/2025%20Q2%20Earnings%20Release.pdf"
test_query = "Gasește informații despre veniturile totale și profitul net din acest raport financiar."

# Execută search
result = process_pdf(test_url, test_query)
print(result)