"""
Pages Synthesis Adapter for parallel Dense Evidence Notes generation.

This adapter handles the parallel processing of web pages to generate
Dense Evidence Notes using LLM calls.
"""

import asyncio
import os
import logging
from typing import List, Dict, Any

from .llm_adapter import LLMAdapter

logger = logging.getLogger(__name__)

# Prompt path
PROMPTS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "agentic_prompts")
PAGE_NOTES_PROMPT = os.path.join(PROMPTS_DIR, "page_notes.md")


class PagesSynthesisAdapter:
    """Adapter for parallel page processing and Dense Evidence Notes generation"""
    
    def __init__(self):
        self.llm_adapter = LLMAdapter()
    
    def generate_page_notes(
        self,
        page: Dict[str, Any],
        company_context: Dict[str, Any],
        datapoint_context: Dict[str, Any]
    ) -> str:
        """
        Generate Dense Evidence Notes for a single page
        
        Args:
            page: Page dictionary with fit_markdown content
            company_context: Company information and context
            datapoint_context: Datapoint requirements and context
            
        Returns:
            Dense Evidence Notes as markdown string
        """
        # Extract and prepare content
        content = page.get("fit_markdown", "")
        if not content or not content.strip():
            url = page.get("url", "Unknown")
            return f"# Dense Evidence Notes — No Content ({url})\n\n[NO_CONTENT] Page contains no extractable content"
        
        # Add paragraph indices
        content_with_indices = self._add_paragraph_indices(content)
        
        # Generate prompt
        prompt = self.llm_adapter.format_prompt_with_template(
            PAGE_NOTES_PROMPT,
            company_context=company_context,
            datapoint_context=datapoint_context,
            page_url=page.get("url", ""),
            fit_markdown_clean_with_indices=content_with_indices
        )
        
        # Get LLM completion
        notes_md = self.llm_adapter.get_completion(
            prompt,
            temperature=0.1,
            model="gemini-2.0-flash",
            # max_tokens=3000
        )
        logger.info(f"Generated notes for page {page.get('url', 'unknown')}: {self.llm_adapter._count_tokens(notes_md)} tokens")
        # create a directory for 
        return notes_md
    
    async def generate_multiple_pages(
        self,
        pages: List[Dict[str, Any]],
        company_context: Dict[str, Any],
        datapoint_context: Dict[str, Any],
        max_concurrent: int = 3
    ) -> List[str]:
        """
        Generate Dense Evidence Notes for multiple pages in parallel
        
        Args:
            pages: List of page dictionaries with content (already deduplicated)
            company_context: Company information and context
            datapoint_context: Datapoint requirements and context
            max_concurrent: Maximum concurrent LLM calls
            
        Returns:
            List of markdown notes strings (same order as input pages)
        """
        if not pages:
            return []
        
        # Create semaphore to limit concurrent requests
        semaphore = asyncio.Semaphore(max_concurrent)
        
        # Create async task for each page
        async def process_page_async(page: Dict[str, Any]) -> str:
            async with semaphore:
                try:
                    # Run the sync function in thread pool to avoid blocking
                    loop = asyncio.get_event_loop()
                    notes_md = await loop.run_in_executor(
                        None,
                        self.generate_page_notes,
                        page,
                        company_context,
                        datapoint_context
                    )
                    return notes_md
                except Exception as e:
                    logger.error(f"Error processing page {page.get('url', 'unknown')}: {e}")
                    url = page.get("url", "Unknown")
                    return f"# Dense Evidence Notes — Error ({url})\n\n[ERROR] Failed to process page: {str(e)}"
        
        # Execute all tasks in parallel
        tasks = [process_page_async(page) for page in pages]
        notes_list = await asyncio.gather(*tasks)
        
        logger.info(f"Parallel page processing complete: {len(notes_list)} pages processed")
        
        return notes_list
    
    def aggregate_notes(self, notes_list: List[str], page_urls: List[str]) -> str:
        """
        Aggregate page notes into concatenated markdown
        
        Args:
            notes_list: List of markdown notes strings
            page_urls: List of corresponding page URLs
            
        Returns:
            Concatenated markdown string with URL separators
        """
        if not notes_list:
            return ""
        
        # Filter out empty notes
        valid_sections = []
        for i, notes in enumerate(notes_list):
            if notes and notes.strip():
                valid_sections.append(notes.strip())
        
        if not valid_sections:
            return ""
        
        # Simple concatenation with separators
        concatenated = "\n\n---\n\n".join(valid_sections)
        
        logger.info(f"Notes aggregation complete: {len(valid_sections)} sections, "
                   f"{self.llm_adapter._count_tokens(concatenated)} tokens")
        
        return concatenated
    
    def _add_paragraph_indices(self, content: str) -> str:
        """Add paragraph indices (§p1, §p2, etc.) to content"""
        paragraphs = content.split('\n\n')
        indexed = []
        for i, para in enumerate(paragraphs, 1):
            if para.strip():
                indexed.append(f"§p{i} {para}")
        return '\n\n'.join(indexed)