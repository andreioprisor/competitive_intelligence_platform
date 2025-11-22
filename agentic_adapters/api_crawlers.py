import os
import requests
import httpx
import logging
import asyncio
import time
import uuid
from typing import Dict, Any, List, Optional
from redis.asyncio import Redis
import html2text
import logging
# BeautifulSoup for HTML parsing

logger = logging.getLogger(__name__)

try:
    from bs4 import BeautifulSoup
    HAS_BS4 = True
except ImportError:
    HAS_BS4 = False
    logger.warning("BeautifulSoup4 not installed. HTML parsing for AI Overview will not be available. Install with: pip install beautifulsoup4")



# Redis Fixed Window Rate Limiter for distributed RPS control
class RedisFixedWindowRPS:
    """
    Caps to `rps` requests per second across all workers.
    Fixed 1s window: simple and robust (minor burst at second boundary).
    """
    def __init__(self, redis: Redis, base_key: str, rps: int):
        self.r = redis
        self.base_key = base_key      # e.g. "rate:scrapingdog"
        self.rps = int(rps)
        self.window_ms = 1500

    async def acquire(self):
        while True:
            now_ms = int(time.time() * 1500)
            bucket = now_ms // self.window_ms
            key = f"{self.base_key}:{bucket}"

            try:
                # increment this second's counter and ensure it expires
                val = await self.r.incr(key)
                if val == 1:
                    # expire slightly after 1s so keys don't accumulate
                    await self.r.pexpire(key, self.window_ms + 100)

                if val <= self.rps:
                    logging.info(f"Rate limiter allowed request {val}/{self.rps} in current window")
                    return  # allowed this second

                # too many this second -> sleep to next second boundary
                wait_ms = self.window_ms - (now_ms % self.window_ms)
                await asyncio.sleep(wait_ms / 1500.0)
            except Exception as e:
                logger.warning(f"Rate limiter error: {e}, proceeding without rate limit")
                return  # Fail open - don't block on Redis errors

class ScrapingDogClient:
    """Simple Scraping Dog API client"""

    def __init__(self):
        self.api_key = os.getenv('SCRAPING_DOG_API_KEY')
        if not self.api_key:
            logger.warning("SCRAPING_DOG_API_KEY not found in environment variables")

        # Initialize rate limiter
        self.rate_limiter = None
        self.redis = None  # Track Redis connection for cleanup
        redis_url = os.getenv('REDIS_URL')
        rps_limit = int(os.getenv('SCRAPING_DOG_RPS_LIMIT', '5'))  # Default 5 RPS

        if redis_url:
            try:
                # Create Redis connection and rate limiter
                self.redis = Redis.from_url(redis_url)
                self.rate_limiter = RedisFixedWindowRPS(
                    self.redis,
                    "rate:scrapingdog",
                    rps_limit
                )
                logger.info(f"ScrapingDog rate limiter initialized with {rps_limit} RPS limit")
            except Exception as e:
                logger.warning(f"Failed to initialize Redis rate limiter: {e}")
                self.rate_limiter = None
                self.redis = None
        else:
            logger.warning("REDIS_URL not set, ScrapingDog rate limiting disabled")
        
    def scrape_page(self, url: str, js_rendering: bool = False) -> Dict[str, Any]:
        """Scrape a page using Scraping Dog API"""
        if not self.api_key:
            return {'html_content': '', 'success': False, 'error': 'API key not configured'}

        # Note: Rate limiting is handled in the async wrapper methods
        try:
            logger.info(f"Scraping URL via Scraping Dog API: {url}")
            response = requests.get("https://api.scrapingdog.com/scrape", params={
                'api_key': self.api_key,
                'url': url,
                'dynamic': 'true' if js_rendering else 'false',
            }, timeout=30)
            
            if response.status_code == 200:
                return {
                    'html_content': response.text,
                    'success': True,
                    'error': None
                }
            else:
                return {
                    'html_content': '',
                    'success': False,
                    'error': f"HTTP {response.status_code}"
                }
        except Exception as e:
            return {
                'html_content': '',
                'success': False,
                'error': str(e)
            }
    
    def get_ai_overview(self, query: str, country: str = "us", return_html: bool = False) -> Dict[str, Any]:
        """
        Get AI Overview from Google Search using Scraping Dog API

        Args:
            query: Search query
            country: Country code for localized results (default: "us")
            return_html: If True, request HTML format and parse with BeautifulSoup (default: False)

        Returns:
            Dict with ai_overview text, success status, and error if any:
            {
                'ai_overview': str,  # Formatted AI overview text
                'full_response': dict,  # Raw response (JSON or HTML)
                'success': bool,
                'error': str or None
            }
        """
        if not self.api_key:
            return {'ai_overview': '', 'success': False, 'error': 'API key not configured'}

        # Note: Rate limiting is handled in the async wrapper methods

        try:
            # Build request parameters
            params = {
                'api_key': self.api_key,
                'query': query,
                'country': country,
            }

            # Add html parameter if HTML format is requested
            if return_html:
                params['html'] = 'true'

            response = requests.get("https://api.scrapingdog.com/google/ai_mode",
                                   params=params, timeout=30)

            if response.status_code == 200:
                if return_html:
                    # Parse HTML response with BeautifulSoup
                    html_content = response.text
                    ai_overview = self._parse_ai_overview_html(html_content)

                    return {
                        'ai_overview': ai_overview,
                        # 'full_response': {'html': html_content},  # Store raw HTML for debugging
                        'success': True,
                        'error': None
                    }
                else:
                    # Parse JSON response (existing logic)
                    data = response.json()
                    ai_overview = self._format_ai_overview(data)

                    return {
                        'ai_overview': ai_overview,
                        'full_response': data,
                        'success': True,
                        'error': None
                    }
            else:
                logging.error(f"Scraping Dog AI overview error: HTTP {response.status_code}")
                return {
                    'ai_overview': '',
                    'full_response': {},
                    'success': False,
                    'error': f"HTTP {response.status_code}"
                }
        except Exception as e:
            logging.error(f"Error getting AI overview: {e}")
            return {
                'ai_overview': '',
                'full_response': {},
                'success': False,
                'error': str(e)
            }

    def google_search(self, query: str, num: int = 10, country: str = "us") -> List[Dict[str, Any]]:
        """
        Search Google using ScrapingDog API (fallback for Serper)

        Args:
            query: Search query string
            num: Number of results to return (1-100, default 10)
            country: ISO country code for localized results (default "us")

        Returns:
            List of search results with url, title, snippet, and position

        API Cost: 5 credits per request
        Endpoint: https://api.scrapingdog.com/google/
        """
        if not self.api_key:
            logger.warning("ScrapingDog API key not configured for google_search")
            return []

        try:
            params = {
                'api_key': self.api_key,
                'query': query,
                'results': 10,  # Cap at API max
                'country': country,
                "domain": "google.com"
            }

            logger.info(f"Executing ScrapingDog Google search for query: '{query}' (country: {country})")
            response = requests.get(
                "https://api.scrapingdog.com/google/",
                params=params,
                timeout=30
            )

            response.raise_for_status()
            data = response.json()

            # Parse organic_data results
            organic_results = data.get('organic_results', [])
            candidates = []

            for item in organic_results:
                candidate = {
                    'url': item.get('link', ''),
                    'title': item.get('title', ''),
                    'snippet': item.get('snippet', ''),
                    'position': item.get('rank', len(candidates) + 1)
                }
                candidates.append(candidate)

            logger.info(f"ScrapingDog Google search returned {len(candidates)} results for '{query}'")
            return candidates[:num]

        except Exception as e:
            logger.error(f"ScrapingDog Google search failed for query '{query}': {e}")
            return []

    async def async_google_search(self, query: str, num: int = 10, country: str = "us") -> List[Dict[str, Any]]:
        """
        Async wrapper for google_search with rate limiting support

        Args:
            query: Search query string
            num: Number of results to return (1-100, default 10)
            country: ISO country code for localized results (default "us")

        Returns:
            List of search results with url, title, snippet, and position
        """
        # Apply rate limiting if available
        if self.rate_limiter:
            try:
                await self.rate_limiter.acquire()
            except Exception as e:
                logger.warning(f"Rate limiter error in async_google_search: {e}, proceeding without rate limit")

        # Call synchronous google_search method
        return self.google_search(query=query, num=num, country=country)

    def _format_ai_overview(self, data: Dict[str, Any]) -> str:
        """Format the AI overview response into a comprehensive string"""
        formatted_text = []
        
        # Process text blocks
        text_blocks = data.get('text_blocks', [])
        for block in text_blocks:
            block_type = block.get('type', '')
            
            if block_type == 'paragraph':
                snippet = block.get('snippet', '').strip()
                if snippet:
                    formatted_text.append(f"Paragraph:\n{snippet}\n")
            
            elif block_type == 'list':
                items = block.get('items', [])
                if items:
                    formatted_text.append("List:")
                    for item in items:
                        snippet = item.get('snippet', '').strip()
                        if snippet:
                            formatted_text.append(f"- {snippet}")
                    formatted_text.append("")  # Add empty line after list
        
        # Process references
        references = data.get('references', [])
        if references:
            formatted_text.append("References:")
            for ref in references:
                title = ref.get('title', '').strip()
                snippet = ref.get('snippet', '').strip()
                source = ref.get('source', '').strip()
                
                if title or snippet or source:
                    ref_parts = []
                    if title:
                        ref_parts.append(f"Title: {title}")
                    if snippet:
                        ref_parts.append(f"Snippet: {snippet}")
                    if source:
                        ref_parts.append(f"Source: {source}")
                    
                    formatted_text.append(" | ".join(ref_parts))
        
        return "\n".join(formatted_text)

    def _parse_ai_overview_html(self, html_content: str) -> str:
        """
        Parse HTML AI overview response and convert to markdown using html2text

        This method parses the raw HTML returned by ScrapingDog's AI Overview API
        when html=true parameter is used. It converts the HTML to clean markdown.

        Args:
            html_content: Raw HTML response from ScrapingDog

        Returns:
            Markdown-formatted AI overview text with sources
        """
        # Convert HTML to markdown using html2text
        h = html2text.HTML2Text()
        h.ignore_links = True
        h.body_width = 0  # Don't wrap lines
        h.ignore_images = True
        h.ignore_emphasis = False

        markdown = h.handle(html_content)

        if not markdown.strip():
            logger.warning("HTML to markdown conversion produced empty result")

        return markdown.strip()

    # Async wrapper methods for parallel processing
    async def scrape_page_async(self, url: str, js_rendering: bool = False) -> Dict[str, Any]:
        """
        Async wrapper for scrape_page method with rate limiting

        Args:
            url: URL to scrape
            js_rendering: Whether to enable JavaScript rendering (default: False)

        Returns:
            Dict with html_content, success status, and error if any
        """
        # Apply rate limiting if available
        if self.rate_limiter:
            await self.rate_limiter.acquire()
        # If no rate limiter, proceed without it

        return await asyncio.to_thread(self.scrape_page, url, js_rendering)
    
    async def get_ai_overview_async(self, query: str, country: str = "us", return_html: bool = False) -> Dict[str, Any]:
        """
        Async wrapper for get_ai_overview method with rate limiting

        Args:
            query: Search query
            country: Country code for localized results (default: "us")
            return_html: If True, request HTML format and parse with BeautifulSoup (default: False)

        Returns:
            Dict with ai_overview text, success status, and error if any
        """
        # Apply rate limiting if available
        if self.rate_limiter:
            await self.rate_limiter.acquire()
        # If no rate limiter, proceed without it

        return await asyncio.to_thread(self.get_ai_overview, query, country, return_html)

    async def cleanup(self):
        """Clean up Redis connections to prevent memory leaks"""
        if self.redis:
            try:
                await self.redis.close()
                logger.debug("ScrapingDogClient Redis connection closed")
            except Exception as e:
                logger.warning(f"Error closing Redis connection: {e}")
            finally:
                self.redis = None
                self.rate_limiter = None


class BrightDataClient:
    """Bright Data API client using web unlocker"""
    
    def __init__(self):
        # Bright Data API token from environment
        self.api_token = os.getenv('BRIGHT_DATA_API_TOKEN')
        self.zone = os.getenv('BRIGHT_DATA_ZONE', 'web_unlocker1')  # Default zone
        
        if not self.api_token:
            logger.warning("BRIGHT_DATA_API_TOKEN not found in environment variables. Bright Data will not work.")

    
    def scrape_page(self, url: str, format_type: str = "raw") -> Dict[str, Any]:
        """Scrape a page using Bright Data API"""
        if not self.api_token:
            return {'html_content': '', 'success': False, 'error': 'Bright Data API token not configured'}
        
        try:
            logger.info(f"Scraping URL via Bright Data API: {url}")
            
            headers = {
                "Authorization": f"Bearer {self.api_token}",
                "Content-Type": "application/json"
            }
            
            data = {
                "zone": self.zone,
                "url": url,
                "format": format_type
            }
            
            response = requests.post(
                "https://api.brightdata.com/request",
                json=data,
                headers=headers,
                timeout=(10, 20)
            )
            
            if response.status_code == 200:
                html_content = response.text
                logger.info(f"Successfully scraped page via Bright Data API: {url}, html length: {len(html_content)}")
                
                return {
                    'html_content': html_content,
                    'success': True,
                    'error': None
                }
            else:
                error_msg = f"HTTP {response.status_code}: {response.text}"
                logger.error(f"Bright Data API error: {error_msg}")
                return {
                    'html_content': '',
                    'success': False,
                    'error': error_msg
                }
            
        except requests.exceptions.Timeout:
            return {
                'html_content': '',
                'success': False,
                'error': "Request timeout"
            }
        except requests.exceptions.RequestException as e:
            return {
                'html_content': '',
                'success': False,
                'error': f"Request error: {str(e)}"
            }
        except Exception as e:
            return {
                'html_content': '',
                'success': False,
                'error': str(e)
            }
    
    # Async wrapper methods for parallel processing
    async def scrape_page_async(self, url: str, format_type: str = "raw") -> Dict[str, Any]:
        """Async wrapper for scrape_page method"""
        return await asyncio.to_thread(self.scrape_page, url, format_type)