"""
Tool implementations for agentic QIA

Each tool has a consistent interface:
- Input: Clear, typed arguments
- Output: Standardized dict/list format
- Cost: Defined budget impact
"""
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
import logging


logger = logging.getLogger(__name__)

class FinalizeArgs(BaseModel):
    reasoning: str = Field(..., description="Brief summary of the findings and why you’re stopping now.")


async def pdf_tool(
    url: str,
    query: str
) -> str:
    """
    Process a PDF document from a URL and extract information based on a query.

    Args:
        url: URL of the PDF document to process
        query: Specific information to extract from the PDF
    Returns:
        Extracted information as a string
    Budget Impact:
        - Seconds: 30 (upload and processing time)
    Implementation:
        - Uses PDFAdapter from agentic_adapters
        - Downloads PDF, uploads to Google GenAI File Search Store
        - Executes query using Gemini model with File Search tool
    """
    from agentic_adapters.pdf_adapter import PDFAdapter

    pdf_adapter = PDFAdapter()
    try:
        logger.info(f"PDF tool: Processing PDF from {url} with query '{query[:50]}...'")
        result = await pdf_adapter.process_pdf(url=url, query=query)
        logger.info(f"PDF tool: Successfully processed PDF, result length {len(result)} chars")
        return result

    except Exception as e:
        logger.error(f"PDF tool failed: {e}")
        return f"Error processing PDF: {str(e)}"
    
async def google_ads_tool(
    domain: str,
    region: str = "RO",
    results_limit: int = 100, 
    period_days: int = 4
) -> List[Dict[str, Any]]:
    """
    Search and scrape Google Ads Transparency data for a given domain.

    Args:
        domain: Domain to search for (e.g., "hubspot.com")
        region: Region code for ads (default: "RO")
        results_limit: Maximum number of ads to retrieve (default: 10)
        period_days: Time period in days to look back for ads (default: 30)
    Returns:
        List of ad variations with details
    Budget Impact:
        - Queries: 1 (for advertiser search)
    Implementation:
        - Uses GoogleAdsScraperPipeline from agentic_adapters
        - Searches for advertiser ID via SerpAPI
        - Scrapes ads using Apify actor
    """
    from agentic_adapters.google_adds_adapter import GoogleAdsScraperPipeline

    scraper = GoogleAdsScraperPipeline()
    try:
        logger.info(f"Google Ads tool: Searching advertiser for domain {domain} in region {region}")
        advertiser_info = await scraper.search_advertiser(domain=domain, region=region)

        logger.info(f"Google Ads tool: Scraping ads for advertiser ID {advertiser_info['advertiser_id']}")
        ads = await scraper.scrape_ads(
            advertiser_id=advertiser_info["advertiser_id"],
            region=region,
            results_limit=results_limit,
            preset_date=f"Last+{period_days}+days"
        )

        logger.info(f"Google Ads tool: Retrieved {len(ads)} ads for domain {domain}")
        return ads

    except Exception as e:
        logger.error(f"Google Ads tool failed: {e}")
        return [{"error": str(e)}]
    
    
async def serp_tool(
    queries: List[str]
) -> str:
    """
    Execute multiple SERP search queries in parallel

    Args:
        queries: List of search query strings (1-5 queries recommended)

    Returns:
        Formatted text with query groups and markdown-linked results in Google SERP style.
        Format:
            ### Query: query string

            - [Page Title](https://example.com/page)
              Snippet text describing the page content...

            - [Another Page](https://example.com/another)
              Another snippet with context...

    Budget Impact:
        - Queries: -len(queries)

    Implementation:
        - Use SerpAdapter batch_search for parallel execution
        - Returns up to 10 results per query
        - Automatically deduplicates URLs across queries
        - Formats results as Google-style markdown text
    """
    from agentic_adapters.serp_adapter import SerpAdapter

    if not queries:
        logger.warning("SERP tool called with empty query list")
        return ""

    serp_adapter = SerpAdapter()
    try:
        # Create query objects
        query_objs = [
            {
                "query": q,
                "ai_overview_needed": False,
                "reasoning": "Agent-generated query"
            }
            for q in queries
        ]

        # Execute batch search (runs in parallel)
        results_by_query, _ = await serp_adapter.batch_search(
            queries=query_objs,
            max_per_query=10,
            max_total=50  # Allow more total results for multiple queries
        )

        # Log results
        total_results = sum(len(results) for results in results_by_query.values())
        logger.info(f"SERP tool: Executed {len(queries)} queries, got {total_results} total results")

        # Format results as text
        formatted_text = serp_adapter.format_serp_results_as_text(results_by_query)
        return formatted_text

    except Exception as e:
        logger.error(f"SERP tool failed: {e}")
        return ""  # Return empty string on error
    finally:
        serp_adapter.cleanup()

async def crawl_tool(urls: List[str]) -> List[Dict[str, Any]]:
    """
    Crawl list of URLs and extract markdown content

    Args:
        urls: List of URLs to crawl (max 5 recommended)

    Returns:
        List of {"url": str, "markdown": str, "success": bool, "meta": dict}

    Budget Impact:
        - Pages: -len(urls)

    Implementation:
        - Use CrawlAdapter from agentic_adapters
        - Multi-level fallback (crawl4ai → scraping_dog → bright_data)
        - Apply content deduplication
    """
    from agentic_adapters.crawl_adapter import CrawlAdapter

    if not urls:
        logger.warning("Crawl tool called with empty URL list")
        return []

    crawl_adapter = CrawlAdapter()
    try:
        logger.info(f"Crawl tool: Starting crawl of {len(urls)} URLs")

        pages = await crawl_adapter.crawl_pages(urls=urls)

        # Count successes
        successful = [{"markdown": p.get("deduplicated_markdown", ""), "url": p.get("url", "")} for p in pages if p.get("success")]

        return successful

    except Exception as e:
        logger.error(f"Crawl tool failed: {e}")
        return [{"url": url, "success": False, "error": str(e)} for url in urls]
    finally:
        await crawl_adapter.cleanup()

async def extract_links_tool(url: str) -> List[Dict[str, Any]]:
    """
    Extract all links from a webpage

    Args:
        url: URL to extract links from

    Returns:
        List of {"url": str, "text": str, "type": str} for each link found

    Budget Impact:
        - Pages: -1 (crawls the page to get HTML)

    Implementation:
        1. Crawl the URL to get HTML content
        2. Parse HTML with BeautifulSoup
        3. Extract all <a> tags with href attributes
        4. Normalize URLs to absolute format
        5. Deduplicate and filter out common junk links
    """
    from bs4 import BeautifulSoup
    from urllib.parse import urljoin, urlparse

    logger.info(f"Extract links tool: Getting links from {url}")

    try:
        # Crawl the page to get HTML
        from agentic_adapters.crawl_adapter import CrawlAdapter
        crawl_adapter = CrawlAdapter()
        pages = await crawl_adapter.crawl_pages(urls=[url])
        if not pages or not pages[0].get("success"):
            error_msg = pages[0].get("error", "Unknown error") if pages else "No results"
            logging.warning(f"Extract links tool: Failed to crawl {url}: {error_msg}")
            return [{"error": f"Failed to crawl page: {error_msg}", "success": False}]

        page = pages[0]
        html_content = page.get("html", "")
        with open("debug_extracted_page.html", "w", encoding="utf-8") as f:
            f.write(html_content)
        if not html_content:
            logging.warning(f"Extract links tool: No HTML content from {url}")
            return [{"error": "No HTML content returned from crawl", "success": False}]

        # Parse HTML
        soup = BeautifulSoup(html_content, 'html.parser')

        # Extract all links
        links = []
        seen_urls = set()

        # Filters for junk links
        skip_patterns = [
            '/privacy', '/terms', '/cookie', '/legal',
            '/login', '/signup', '/signin', '/register',
            'javascript:', 'mailto:', 'tel:', '#'
        ]

        for a_tag in soup.find_all('a', href=True):
            href = a_tag['href'].strip()
            print(href)

            # Skip empty hrefs
            if not href or href == '#':
                continue

            # Convert to absolute URL
            absolute_url = urljoin(url, href)

            # Remove fragment
            parsed = urlparse(absolute_url)
            clean_url = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
            if parsed.query:
                clean_url += f"?{parsed.query}"

            # Skip if already seen
            if clean_url in seen_urls:
                continue

            # Skip junk links
            if any(pattern in clean_url.lower() for pattern in skip_patterns):
                continue

            # Get link text
            link_text = a_tag.get_text(strip=True)

            # Categorize link type
            link_type = "internal" if urlparse(clean_url).netloc == urlparse(url).netloc else "external"

            links.append({
                "url": clean_url,
                "text": link_text,
                "type": link_type
            })

            seen_urls.add(clean_url)

        logger.info(f"Extracted {len(links)} unique links from {url}: {links}...")
        return links

    except Exception as e:
        logger.error(f"Extract links tool failed: {e}")
        return [{"error": str(e), "success": False}]

async def ai_overview_tool(query: str, country: str = "us") -> Dict[str, Any]:
    """
    Get Google AI Overview for query

    Args:
        query: Search query string
        country: Country code for localized results (default: "us")

    Returns:
        {"query": str, "ai_overview": str, "success": bool, "error": str or None}

    Budget Impact:
        - Minimal (piggybacks on SERP infrastructure)

    Use Cases:
        - Protected sites (Glassdoor, G2, Capterra)
        - Sites with heavy anti-bot measures
        - When direct crawl fails

    Implementation:
        - Use ScrapingDogClient from agentic_adapters
        - Extract AI Overview paragraph from Google SERP
        - Use return_html=True parameter for better parsing
    """
    from agentic_adapters.api_crawlers import ScrapingDogClient

    scraping_dog = ScrapingDogClient()
    try:
        logger.info(f"AI Overview tool: Fetching for query '{query}...'")

        # Call async wrapper which handles rate limiting
        result = await scraping_dog.get_ai_overview_async(
            query=query,
            country=country,
            return_html=True  # Use HTML mode for better parsing
        )

        # Add query to result for consistency
        result["query"] = query

        if result.get("success"):
            overview_text = result.get("ai_overview", "")
            logger.info(f"AI Overview tool: Success ({len(overview_text)} chars)")
        else:
            error = result.get("error", "Unknown error")
            logger.warning(f"AI Overview tool: Failed - {error}")

        return result

    except Exception as e:
        logger.error(f"AI Overview tool failed: {e}")
        return {
            "query": query,
            "ai_overview": "",
            "success": False,
            "error": str(e)
        }
    finally:
        await scraping_dog.cleanup()

async def finalize_tool(reasoning: str) -> Dict[str, str]:
    """
    Signal completion of research task

    Args:
        reasoning: Brief summary of findings and why research is complete

    Returns:
        {"action": "finalize", "reasoning": str}

    Use Cases:
        - When sufficient evidence has been gathered
        - When budget is nearly exhausted but key findings obtained
        - When confidence threshold reached for the datapoint
    """
    logger.info(f"Finalize tool called: {reasoning}...")
    return {
        "action": "finalize",
        "reasoning": reasoning
    }

# this function uses prospect model from core/models/prospect.py
def create_search_linkedin_posts_tool(prospect):
    """
    Factory function that creates a LinkedIn posts search tool with prospect bound via closure.

    This pattern allows the prospect object to be accessible to the tool without being
    serialized into the conversation state (avoiding token bloat).

    Args:
        prospect: Prospect object with linkedin_posts_data attribute

    Returns:
        Async function that searches LinkedIn posts
    """
    async def search_linkedin_posts_tool(keywords: List[str], max_posts: int = 10) -> str:
        """
        Search the company's LinkedIn posts for specific keywords.

        Args:
            keywords: List of keywords to search for (case-insensitive)
            max_posts: Maximum number of matching posts to return (default: 10)

        Returns:
            Formatted string with matching posts and engagement metrics
        """
        # Validate prospect has LinkedIn posts data
        logging.info(f"Search LinkedIn posts tool: Searching for keywords {keywords} with max_posts={max_posts}")
        if not prospect or not hasattr(prospect, 'linkedin_posts_data'):
            logging.warning("Search LinkedIn posts tool: No prospect or linkedin_posts_data available")
            return "No LinkedIn posts data available for this company."

        posts_data = prospect.linkedin_posts_data

        if not posts_data or not posts_data.success or not posts_data.posts:
            logging.info("Search LinkedIn posts tool: No posts data or unsuccessful fetch")
            return "No LinkedIn posts available for this company."

        # Search for matching posts
        logging.info(f"Found multiple posts: Searching {len(posts_data.posts)} posts for keywords")
        matching_posts = posts_data.search_posts(keywords=keywords, max_results=max_posts)

        if not matching_posts:
            return f"No posts found matching keywords: {', '.join(keywords)}"

        # Format results
        logging.info(f"Found {len(matching_posts)} matching posts for keywords: {keywords}")
        result = f"Found {len(matching_posts)} posts matching keywords: {', '.join(keywords)}\n\n"

        for i, post in enumerate(matching_posts, 1):
            result += f"--- Post {i} ---\n"

            if post.posted_at:
                result += f"Posted: {post.posted_at}\n"

            if post.text:
                # Truncate to 300 chars for readability
                text = post.text[:300] + "..." if len(post.text) > 300 else post.text
                result += f"Content: {text}\n"

            # Add engagement metrics
            metrics = []
            if post.total_reaction_count is not None:
                metrics.append(f"{post.total_reaction_count} reactions")
            if post.like_count is not None:
                metrics.append(f"{post.like_count} likes")
            if post.comments_count is not None:
                metrics.append(f"{post.comments_count} comments")
            if post.reposts_count is not None:
                metrics.append(f"{post.reposts_count} reposts")

            if metrics:
                result += f"Engagement: {', '.join(metrics)}\n"

            if post.post_url:
                result += f"URL: {post.post_url}\n"

            result += "\n"

        return result.strip()

    return search_linkedin_posts_tool

# Tool registry with metadata for LLM consumption
TOOL_REGISTRY = {
    "pdf": {
        "function": pdf_tool,
        "description": "Process a PDF document from a URL and extract information based on a query. Downloads the PDF, uploads it to Google GenAI File Search Store, and executes the query using Gemini model with File Search tool.",
        "parameters": {
            "url": {
                "type": "string",
                "required": True,
                "description": "URL of the PDF document to process"
            },
            "query": {
                "type": "string",
                "required": True,
                "description": "Specific information to extract from the PDF"
            }
        },
        "returns": {
            "type": "string",
            "description": "Extracted information as a string"
        },
        "budget_cost": {
            "pdf": 1,
        },
        "use_cases": [
            "Extracting financial data from PDF reports",
            "Summarizing PDF documents",
            "Retrieving specific information from PDFs"
        ],
        "example": {
            "url": "https://example.com/report.pdf",
            "query": "Extract financial summary"
        }
    },
    "google_ads": {
        "function": google_ads_tool,
        "description": "Search and scrape Google Ads Transparency data for a given domain. Searches for the advertiser ID via SerpAPI and scrapes ads using an Apify actor.",
        "parameters": {
            "domain": {
                "type": "string",
                "required": True,
                "description": "Domain to search for (e.g., 'hubspot.com')"
            },
            "region": {
                "type": "string",
                "required": False,
                "description": "Region code for ads (default: 'RO')"
            },
            "results_limit": {
                "type": "integer",
                "required": False,
                "description": "Maximum number of ads to retrieve (default: 10)"
            },
            "period_days": {
                "type": "integer",
                "required": False,
                "description": "Time period in days to look back for ads (default: 30)"
            }
        },
        "returns": {
            "type": "array",
            "description": "List of ad variations with details"
        },
        "budget_cost": {
            "google_ads": 1,
        },
        "use_cases": [
            "Gathering competitive advertising data",
            "Analyzing ad creatives and messaging",
            "Tracking competitor ad spend and strategies"
        ],
        "example": {
            "domain": "hubspot.com",
            "region": "RO",
            "results_limit": 100,
            "period_days": 4
        },
    },
    "serp": {
        "function": serp_tool,
        "description": "Search the web using multiple Google Search queries in parallel. IMPORTANT: This tool accepts a LIST of queries (not a single query) and executes them simultaneously. Use this to efficiently gather information from multiple search angles at once. Returns formatted text with query groups and markdown-linked results in Google SERP style, making it easy to read and select URLs for crawling. Company context and datapoint context are automatically provided from the current research task.",
        "parameters": {
            "queries": {
                "type": "array",
                "items": {"type": "string"},
                "required": True,
                "description": "List of 1-5 search query strings to execute in parallel. Use simple, natural language with company domain + keywords (e.g., ['techcorp.com employee count', 'techcorp.com careers', 'techcorp.com about'])"
            }
        },
        "returns": {
            "type": "string",
            "description": "Formatted text with query groups and markdown-linked results. Format: '### Query: query\\n\\n- [Title](URL)\\n  Snippet text...\\n\\n- [Title](URL)\\n  Snippet...'"
        },
        "budget_cost": {
            "queries": "len(queries)",
        },
        "use_cases": [
            "Finding external verification sources",
            "Discovering news articles or press releases",
            "Locating LinkedIn, Glassdoor, or review sites",
            "Researching competitive landscape"
        ],
        "example": {
            "query": "acme-corp.com funding round series B",
            "company_context": {"domain": "acme-corp.com", "name": "Acme Corp"}
        }
    },
    "crawl": {
        "function": crawl_tool,
        "description": "Extract content from webpages as markdown. Accepts a single URL string or JSON array of URLs. Uses multi-level fallback crawling (crawl4ai → scraping_dog → bright_data) to handle protected sites. Returns structured markdown with metadata. Use this when you have specific URLs to extract information from.",
        "parameters": {
            "urls": {
                "type": "string or array",
                "required": True,
                "description": "URL string (e.g. 'https://example.com') or JSON array of URLs (e.g. '[\"https://example.com\", \"https://example.com/about\"]'). Recommend max 5 URLs per call for efficiency."
            }
        },
        "returns": {
            "type": "array",
            "description": "List of crawled pages, each containing: url (str), markdown (str), deduplicated_markdown (str), success (bool), meta (dict with title, source_type, api_used)"
        },
        "budget_cost": {
            "urls": "len(urls)",
        },
        "use_cases": [
            "Extracting content from company website pages",
            "Reading news articles or blog posts",
            "Accessing LinkedIn company pages",
            "Retrieving information from discovered URLs"
        ],
        "example": {
            "urls": ["https://acme-corp.com/about", "https://acme-corp.com/team"]
        }
    },
    "extract_links": {
        "function": extract_links_tool,
        "description": "Extract all links from a webpage. Returns a list of URLs found on the page with their anchor text and type (internal/external). Useful for discovering related pages, finding job listings, locating specific sections of a website, or exploring site structure.",
        "parameters": {
            "url": {
                "type": "string",
                "required": True,
                "description": "URL of the page to extract links from"
            }
        },
        "returns": {
            "type": "array",
            "description": "List of links, each containing: url (str), text (str - anchor text), type (str - 'internal' or 'external')"
        },
        "budget_cost": {
            "urls": 1,
        },
        "use_cases": [
            "Finding all job postings on a careers page",
            "Discovering department/team pages from main site",
            "Locating blog posts or press releases",
            "Finding product pages or documentation"
        ],
        "example": {
            "url": "https://acme-corp.com/careers"
        }
    },
    "ai_overview": {
        "function": ai_overview_tool,
        "description": "Get Google's AI-generated overview for a query. This is pre-processed by Google and can access information from protected sites (Glassdoor, G2, Capterra) that are hard to crawl directly. Use this when dealing with anti-bot protected sites or when you need a quick synthesized answer from Google.",
        "parameters": {
            "query": {
                "type": "string",
                "required": True,
                "description": "Search query string. Use natural language questions (e.g., 'What is Acme Corp's Glassdoor rating?')"
            },
        },
        "returns": {
            "type": "object",
            "description": "Dict containing: query (str), ai_overview (str - the AI-generated text), success (bool), error (str or None)"
        },
        "budget_cost": {
            "ai_overviews": 1,
        },
        "use_cases": [
            "Accessing heavily guarded sites like Glassdoor, Indeed, G2",
            "Good for quick factual insights and answers, but might lack depth.",
            "Initial context gathering before deeper research",
        ],
        "example": {
            "query": "Acme Corp Glassdoor rating and reviews",
            "country": "us"
        }
    },
    "search_linkedin_posts": {
        "function": None,  # Created dynamically via factory
        "description": "Search the company's LinkedIn posts for specific keywords and topics. Returns matching posts with content, engagement metrics, and URLs. Use this when you need evidence from the company's social media about culture, hiring, products, announcements, or brand messaging. Try to use keywords both in english and in the local language of the companys for better results.",
        "parameters": {
            "keywords": {
                "type": "array",
                "items": {"type": "string"},
                "required": True,
                "description": "List of keywords to search for in post text (e.g., ['culture', 'hiring', 'remote work']). Search is case-insensitive and matches any keyword."
            },
            "max_posts": {
                "type": "integer",
                "required": False,
                "description": "Maximum number of matching posts to return (default: 10)"
            }
        },
        "returns": {
            "type": "string",
            "description": "Formatted text with matching posts. Each post includes: posted date, content (truncated to 300 chars), engagement metrics (reactions, comments, reposts), and post URL. The posts returned are cronologically sorted  from newest to oldest. It doesnt support filtering by date range."
        },
        "budget_cost": {},  # No budget cost - uses pre-fetched data
        "use_cases": [
            "Finding posts about employee culture, values, or workplace environment",
            "Detecting hiring signals and recruitment content",
            "Identifying product launches or new feature announcements",
            "Discovering partnership mentions or customer success stories",
            "Analyzing company messaging and brand voice",
            "Verifying company claims about remote work, diversity, or initiatives"
        ],
        "example": {
            "keywords": ["culture", "team", "employees"],
            "max_posts": 5
        }
    }
}

# Legacy tool mapping for backward compatibility
TOOLS = {name: meta["function"] for name, meta in TOOL_REGISTRY.items() if meta["function"]}

def get_tool_cost(tool_name: str, tool_args: Dict[str, Any]) -> Dict[str, int]:
    """
    Calculate budget cost for tool execution using registry metadata

    Returns:
        {"queries": X, "pages": Y, "seconds": Z} cost dict
    """
    if tool_name not in TOOL_REGISTRY:
        return {"queries": 0, "pages": 0, "seconds": 0}

    cost = TOOL_REGISTRY[tool_name]["budget_cost"].copy()

    # Handle dynamic costs (e.g., crawl pages based on URL count)
    if tool_name == "crawl":
        url_count = len(tool_args.get("urls", []))
        cost["pages"] = url_count
        cost["seconds"] = 2 * url_count

    return cost

def get_tool_description(tool_name: str) -> str:
    """Get LLM-friendly description of a tool"""
    if tool_name not in TOOL_REGISTRY:
        return ""
    return TOOL_REGISTRY[tool_name]["description"]

def get_tool_parameters(tool_name: str) -> Dict[str, Any]:
    """Get parameter schema for a tool"""
    if tool_name not in TOOL_REGISTRY:
        return {}
    return TOOL_REGISTRY[tool_name]["parameters"]

def format_tools_for_llm() -> str:
    """
    Format tool registry as markdown for LLM consumption in prompts

    Returns formatted string with tool descriptions, parameters, costs, and examples
    """
    lines = []
    for tool_name, meta in TOOL_REGISTRY.items():
        lines.append(f"### {tool_name}")
        lines.append(f"**Description:** {meta['description']}\n")

        # Parameters
        lines.append("**Parameters:**")
        for param_name, param_info in meta["parameters"].items():
            required = "required" if param_info["required"] else "optional"
            lines.append(f"- `{param_name}` ({param_info['type']}, {required}): {param_info['description']}")
        lines.append("")

        # Returns
        lines.append(f"**Returns:** {meta['returns']['description']}\n")

        # Budget cost
        cost = meta["budget_cost"]
        cost_str = ", ".join([f"{k}: {v}" for k, v in cost.items()])
        lines.append(f"**Budget Cost:** {cost_str}\n")

        # Use cases
        lines.append("**When to use:**")
        for use_case in meta["use_cases"]:
            lines.append(f"- {use_case}")
        lines.append("")

        # Example
        lines.append("**Example:**")
        lines.append(f"```json\n{meta['example']}\n```\n")
        lines.append("---\n")

    return "\n".join(lines)

def get_tool_json_schema(tool_name: str) -> Dict[str, Any]:
    """
    Generate JSON schema for tool parameters (for LLM structured output)

    Returns schema that can be used in LLM tool calling or structured output
    """
    if tool_name not in TOOL_REGISTRY:
        return {}

    params = TOOL_REGISTRY[tool_name]["parameters"]
    properties = {}
    required = []

    for param_name, param_info in params.items():
        properties[param_name] = {
            "type": param_info["type"],
            "description": param_info["description"]
        }
        if param_info["required"]:
            required.append(param_name)

    return {
        "type": "object",
        "properties": properties,
        "required": required
    }

def get_all_tools_enum() -> list:
    """Get list of all available tool names for LLM enum constraints"""
    return list(TOOL_REGISTRY.keys()) + ["TERMINATE"]

def can_afford_tool(
    budget_remaining: Dict[str, int],
    tool_name: str,
    tool_args: Dict[str, Any]
) -> bool:
    """
    Check if budget allows tool execution

    Args:
        budget_remaining: Current budget state
        tool_name: Name of tool to check
        tool_args: Arguments for the tool

    Returns:
        True if budget sufficient, False otherwise
    """
    cost = get_tool_cost(tool_name, tool_args)

    queries_needed = cost.get("queries", 0)
    pages_needed = cost.get("pages", 0)

    queries_available = budget_remaining.get("queries", 0)
    pages_available = budget_remaining.get("pages", 0)

    return queries_available >= queries_needed and pages_available >= pages_needed


# =============================================================================
# LangChain Tool Wrappers for create_react_agent with Budget Enforcement
# =============================================================================

def _require_thread_id(kwargs: Dict[str, Any]) -> str:
    """Extract thread_id from kwargs"""
    thread_id = kwargs.pop("thread_id", None)
    if not thread_id:
        raise ValueError("All tools must be called with a `thread_id` argument.")
    return thread_id

def create_simple_tools():
    """
    Create LangChain StructuredTools that properly handle list arguments.
    
    Uses StructuredTool instead of Tool to support typed parameters including lists.
    This ensures that when the LLM passes a list of queries, it's received as a list
    rather than being stringified.
    """
    import asyncio
    import json
    from langchain_core.tools import StructuredTool
    from typing import List

    def pdf_sync(url: str, query: str) -> str:
        """Process a PDF document from a URL and extract information based on a query."""
        result = asyncio.run(pdf_tool(url, query))
        return result
    
    def google_ads_sync(
        domain: str,
        region: str = "RO",
        results_limit: int = 100,
        period_days: int = 4
    ) -> str:
        """Search and scrape Google Ads Transparency data for a given domain."""
        result = asyncio.run(google_ads_tool(
            domain=domain,
            region=region,
            results_limit=results_limit,
            period_days=period_days
        ))
        return json.dumps(result)
    
    
    def serp_sync(queries: List[str]) -> str:
        """
        Search Google using multiple queries in parallel.

        Args:
            queries: List of query strings to execute in parallel

        Returns:
            Formatted text with query groups and markdown-linked results
        """
        try:
            # Ensure we have a list
            if not isinstance(queries, list):
                queries = [queries] if queries else []

            # Clean each query
            cleaned_queries = []
            for q in queries:
                if isinstance(q, str):
                    cleaned = q.strip().replace('\n', ' ').replace('\"', '').replace('\'', '').replace('\\', '').replace('\t', ' ').replace('"', ' ')
                    if cleaned:
                        cleaned_queries.append(cleaned)

            if not cleaned_queries:
                logger.warning("SERP tool received empty queries")
                return ""

            logger.info(f"SERP tool executing {len(cleaned_queries)} queries: {cleaned_queries}")
            result = asyncio.run(serp_tool(cleaned_queries))
            logging.info("Serp results: ")
            logging.info(result)
            return result  # Return formatted text string directly
        except Exception as e:
            logger.error(f"SERP sync wrapper error: {e}")
            return f"Error: {str(e)}"

    def crawl_sync(urls: List[str]) -> str:
        """
        Extract content from one or more URLs.

        Args:
            urls: List of URLs to crawl

        Returns:
            JSON array of crawled page results
        """
        try:
            # Ensure we have a list
            if not isinstance(urls, list):
                urls = [urls] if urls else []
            
            # Clean each URL
            cleaned_urls = []
            for u in urls:
                if isinstance(u, str):
                    cleaned = u.strip()
                    if cleaned:
                        cleaned_urls.append(cleaned)
            
            if not cleaned_urls:
                logger.warning("Crawl tool received empty URLs")
                return json.dumps([{"error": "No URLs provided", "success": False}])
            
            logger.info(f"Crawl tool processing {len(cleaned_urls)} URLs: {cleaned_urls}")
            result = asyncio.run(crawl_tool(cleaned_urls))
            return json.dumps(result)
        except Exception as e:
            logger.error(f"Crawl tool error: {e}")
            return json.dumps([{"error": str(e), "success": False}])

    def extract_links_sync(url: str) -> str:
        """Extract all links from a webpage"""
        result = asyncio.run(extract_links_tool(url))
        return json.dumps(result)

    def ai_overview_sync(query: str) -> str:
        """Get Google AI Overview for a query"""
        result = asyncio.run(ai_overview_tool(query))
        return json.dumps(result)

    def finalize_sync(reasoning: str) -> str:
        """
        Call this when research is complete.
        Provide a brief summary of your findings.
        """
        return {
            "action": "finalize",
            "reasoning": reasoning
        }

    return [
        StructuredTool.from_function(
            func=pdf_sync,
            name="pdf",
            description=TOOL_REGISTRY["pdf"]["description"],
            args_schema=None,  # Will be inferred from type hints
        ),
        StructuredTool.from_function(
            func=google_ads_sync,
            name="google_ads",
            description=TOOL_REGISTRY["google_ads"]["description"],
            args_schema=None,  # Will be inferred from type hints
        ),
        StructuredTool.from_function(
            func=serp_sync,
            name="serp",
            description=TOOL_REGISTRY["serp"]["description"],
            args_schema=None,  # Will be inferred from type hints
        ),
        StructuredTool.from_function(
            func=crawl_sync,
            name="crawl",
            description=TOOL_REGISTRY["crawl"]["description"],
            args_schema=None,
        ),
        StructuredTool.from_function(
            func=extract_links_sync,
            name="extract_links",
            description=TOOL_REGISTRY["extract_links"]["description"],
            args_schema=None,
        ),
        StructuredTool.from_function(
            func=ai_overview_sync,
            name="ai_overview",
            description=TOOL_REGISTRY["ai_overview"]["description"],
            args_schema=None,
        ),
        StructuredTool.from_function(
            func=finalize_sync,
            name="finalize",
            description="Call when you have gathered sufficient evidence and are ready to conclude research. Provide all your findings with reasoning in 4-6 sentences.",
            args_schema=None,
        )
    ]

def create_async_tools() -> List:
    """
    Create LangGraph-native async tools with InjectedState support.

    Returns raw async functions (no Tool wrappers, no bind_tools).
    LangGraph will automatically inject state for parameters annotated with InjectedState.

    Usage:
        agent = create_react_agent(
            model=llm,  # plain model, no bind_tools
            tools=create_async_tools(),
            ...
        )

    Returns:
        List of async tool functions with InjectedState support
    """
    return [
        pdf_tool, 
        google_ads_tool,  # No state injection needed
        serp_tool,       # Has InjectedState for company_context/datapoint_definition
        crawl_tool,      # No state injection needed
        extract_links_tool,  # No state injection needed
        ai_overview_tool,    # No state injection needed
        finalize_tool        # Signals research completion
    ]

# Backward compatibility aliases
def create_budget_aware_tools(prospect=None):
    """
    Create tools with optional prospect data for LinkedIn posts search.

    Args:
        prospect: Optional Prospect object with linkedin_posts_data

    Returns:
        List of tool functions
    """
    base_tools = create_simple_tools()

    # Add LinkedIn posts tool if prospect is provided and has posts data
    if prospect and hasattr(prospect, 'linkedin_posts_data') and prospect.linkedin_posts_data:
        linkedin_posts_tool = create_search_linkedin_posts_tool(prospect)
        base_tools.append(linkedin_posts_tool)
        logger.info("Added search_linkedin_posts tool to available tools")
    else:
        logger.info("No prospect or linkedin_posts_data; skipping search_linkedin_posts tool")

    return base_tools

def create_langchain_tools() -> List:
    """Legacy function"""
    return create_simple_tools()
