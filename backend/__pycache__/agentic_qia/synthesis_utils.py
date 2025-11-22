"""
Synthesis utilities for agentic QIA
"""
import logging
import os
from typing import List, Dict, Any, Optional, Tuple

logger = logging.getLogger(__name__)

PROMPTS_DIR = os.path.join(os.path.dirname(__file__), "prompts")
FINAL_SYNTHESIS_PROMPT = os.path.join(PROMPTS_DIR, "final_synthesis.md")


def format_pages_for_synthesis(pages: List[Dict[str, Any]]) -> str:
    """
    Convert raw pages to markdown format suitable for synthesis

    Input: [{"url": "...", "deduplicated_markdown": "...", "meta": {...}}, ...]
    Output: Concatenated markdown with clear source delineation
    """
    formatted_sections = []
    for page in pages:
        url = page.get("url", "Unknown URL")
        markdown = page.get("deduplicated_markdown", "") or page.get("markdown", "")
        title = page.get("meta", {}).get("title", "Untitled")

        if markdown and markdown.strip():
            section = f"""
# {title} ({url})

{markdown}

----
"""
            formatted_sections.append(section)

    return "\n".join(formatted_sections)



