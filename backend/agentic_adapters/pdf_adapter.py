import time
from google import genai
from google.genai import types
import os
import asyncio
import requests
import tempfile
from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)

class PDFAdapter:
    """
    Adapter for processing PDF documents using Google GenAI File Search

    Downloads PDFs, uploads to File Search Store, and queries using Gemini
    """

    async def process_pdf(self, url: str, query: str) -> str:
        """
        Process a PDF from URL and extract information based on query

        Args:
            url: URL of the PDF document
            query: Question or extraction task to perform on the PDF

        Returns:
            Extracted information as text
        """
        temp_pdf_path = None
        store = None
        client = None

        try:
            logger.info(f"PDFAdapter: Downloading PDF from {url}")

            # Download PDF with streaming
            response = requests.get(url, timeout=30, stream=True)
            response.raise_for_status()

            # Validate content type
            content_type = response.headers.get('Content-Type', '')
            if 'pdf' not in content_type.lower() and not url.lower().endswith('.pdf'):
                logger.warning(f"URL may not be a PDF. Content-Type: {content_type}")

            # Save to temporary file
            with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as temp_file:
                temp_pdf_path = temp_file.name
                for chunk in response.iter_content(chunk_size=8192):
                    temp_file.write(chunk)

            logger.info(f"PDFAdapter: Downloaded PDF to {temp_pdf_path}")

            # Initialize Gemini client
            api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GENAI_API_KEY")
            if not api_key:
                raise ValueError("GEMINI_API_KEY not found in environment")

            client = genai.Client(api_key=api_key)

            # Create File Search Store
            logger.info("PDFAdapter: Creating File Search Store")
            store = client.file_search_stores.create()

            # Upload PDF to store
            logger.info("PDFAdapter: Uploading PDF to File Search Store")
            upload_op = client.file_search_stores.upload_to_file_search_store(
                file_search_store_name=store.name,
                file=temp_pdf_path
            )

            # Wait for upload to complete
            while not upload_op.done:
                await asyncio.sleep(5)
                upload_op = client.operations.get(upload_op)
                logger.debug("PDFAdapter: Waiting for upload to complete...")

            logger.info(f"PDFAdapter: Upload complete, executing query: '{query[:100]}...'")

            # Query the PDF using the provided query parameter
            response = client.models.generate_content(
                model='gemini-2.5-flash',
                contents=query,  # Use the query parameter, not hardcoded text
                config=types.GenerateContentConfig(
                    tools=[types.Tool(
                        file_search=types.FileSearch(
                            file_search_store_names=[store.name]
                        )
                    )]
                )
            )

            result_text = response.text
            logger.info(f"PDFAdapter: Query successful, result length: {len(result_text)} chars")
            logger.info(f"PDFAdapter: Gemini response: {result_text}")
            return result_text

        except Exception as e:
            logger.error(f"PDFAdapter: Error processing PDF: {e}", exc_info=True)
            raise

        finally:
            # Cleanup temp file
            if temp_pdf_path and os.path.exists(temp_pdf_path):
                try:
                    os.unlink(temp_pdf_path)
                    logger.info(f"PDFAdapter: Cleaned up temp file {temp_pdf_path}")
                except Exception as e:
                    logger.warning(f"PDFAdapter: Failed to delete temp file: {e}")

            # Cleanup File Search Store
            if client and store:
                try:
                    # First, list and delete all files in the store
                    try:
                        # List files using the correct API
                        files = client.files.list(filter=f"file_search_stores/{store.name.split('/')[-1]}")

                        # Delete each file
                        for file in files:
                            try:
                                client.files.delete(name=file.name)
                                logger.debug(f"PDFAdapter: Deleted file {file.name}")
                            except Exception as file_err:
                                logger.warning(f"PDFAdapter: Failed to delete file {file.name}: {file_err}")
                    except Exception as list_err:
                        logger.debug(f"PDFAdapter: Could not list/delete files: {list_err}")

                    # Now delete the store (may still fail if files weren't deleted)
                    client.file_search_stores.delete(name=store.name)
                    logger.info("PDFAdapter: Deleted File Search Store successfully")
                except Exception as e:
                    # This is non-critical - Google will eventually clean up old stores
                    logger.debug(f"PDFAdapter: Could not delete File Search Store (non-critical): {e}")