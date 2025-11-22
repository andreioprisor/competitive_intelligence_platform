import asyncio
from typing import List, Dict, Any, Optional
import logging
from datetime import datetime, timedelta
import time
from urllib.parse import urlparse
import os
import httpx
from types import SimpleNamespace

from crawl4ai import (
    AsyncWebCrawler,
    BrowserConfig, 
    CrawlerRunConfig,
    UndetectedAdapter,
    DefaultMarkdownGenerator,
    PruningContentFilter,
)
from crawl4ai.async_crawler_strategy import AsyncPlaywrightCrawlerStrategy

from .utils.content_utils import content_utils
from .api_crawlers import ScrapingDogClient, BrightDataClient
from html2text import html2text

logger = logging.getLogger(__name__)

class CrawlAdapter:
    """Crawl4AI adapter for web page fetching and markdown conversion. Use domain and DP name for logging context."""
    
    def __init__(self, use_browser: bool = False, company_domain: Optional[str] = None, target_dp_name: Optional[str] = None):
        self.crawler = None
        self.failed_urls = set()
        self.use_browser = use_browser

        # Simple 2-option system
        if self.use_browser:
            self.crawl_levels = ["requests", "crawl4ai", "apis"]
            # Initialize browser components
            self.browser_config = BrowserConfig(headless=True, verbose=False)
            self.undetected_adapter = UndetectedAdapter()
            self.crawler_strategy = AsyncPlaywrightCrawlerStrategy(
                browser_config=self.browser_config,
                browser_adapter=self.undetected_adapter
            )
        else:
            self.crawl_levels = ["requests", "apis"]
            # No browser components
            self.browser_config = None
            self.undetected_adapter = None
            self.crawler_strategy = None

        # API clients
        self.scraping_dog = ScrapingDogClient()
        self.bright_data = BrightDataClient()

        # Requests layer defaults
        self.requests_timeout = int(os.getenv("REQUESTS_TIMEOUT", "8"))
        self.requests_retries = int(os.getenv("REQUESTS_RETRIES", "0"))
        self.requests_concurrency = int(os.getenv("REQUESTS_CONCURRENCY", "10"))  # 3–15 sweet spot
        self.default_headers = {
            "User-Agent": os.getenv("REQUESTS_UA", "Mozilla/5.0 (compatible; CrawlAdapter/1.0)"),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.8",
            "Cache-Control": "no-cache",
            "Pragma": "no-cache",
        }
        self.http_proxy = os.getenv("HTTP_PROXY")  # optional
        self.https_proxy = os.getenv("HTTPS_PROXY")  # optional

        logger.info(f"CrawlAdapter initialized with use_browser: {self.use_browser}, levels: {self.crawl_levels}")
        
        # Markdown generator with content filtering
        self.markdown_generator = DefaultMarkdownGenerator(
            content_filter=PruningContentFilter(
                threshold=0.1,  # Adjust threshold as needed
            ),
            options={
                'ignore_links': True,  # Ignore links in markdown output
                'ignore_images': True,  # Ignore images in markdown output
                'skip_internal_links': True  # Skip internal links in markdown
            },
            content_source="fit_html"  # Focus on main body content
        )
        
    
    def _is_security_challenge(self, markdown_content: str, result) -> bool:
        """
        Detect security challenges, bot detection, cookie walls, etc. in markdown content
        Returns True if page contains security/bot detection elements
        """
        if not markdown_content or len(markdown_content.strip()) < 1000:
            return True  # Suspiciously short content
        
        # Comprehensive security indicators
        security_indicators = [
            # Cloudflare & DDoS Protection
            'cloudflare', 'cf-ray', 'ddos protection', 'ddos-guard',
            
            # CAPTCHA Systems
            'captcha', 'recaptcha', 'hcaptcha', 'im not a robot',
            'solve the captcha', 'complete the captcha',
            
            # Access Blocks
            'access denied', 'forbidden', 'bot detection',
            'blocked', 'access blocked', 'ip blocked',
            
            # Human Verification
            'security check', 'verify you are human', 'human verification',
            'confirm you are human', 'prove you are human',
            'are you a robot', 'verify that you are not a robot',
            
            # Rate Limiting
            'rate limit', 'too many requests', 'suspicious activity',
            'request limit exceeded', 'temporarily blocked',
            
            # Security Services
            'firewall', 'incapsula', 'imperva', 'sucuri', 'akamai',
            'turnstile', 'perimeterx', 'radware', 'barracuda',
            'datadome', 'distil', 'kasada',
            
            # Browser/JavaScript Checks
            'javascript required', 'enable javascript', 'browser check',
            'javascript is required', 'please enable javascript',
            'your browser does not support javascript',
            
            # Loading & Redirect States
            'loading...', 'please wait', 'redirecting', 
            'checking your browser', 'just a moment',
            'one moment please', 'verifying your browser',
            
            # Cookie Requirements
            'enable cookies', 'accept cookies', 'cookie consent',
            'cookies required', 'please accept cookies',
            'this site uses cookies',
            'manage cookies', 'cookie settings',
            
            # Security Challenges
            'security challenge', 'complete security check',
            'verification required', 'additional verification',
            
            # Geographic/Location Blocks
            'not available in your region', 'geo-blocked',
            'service unavailable in your location',
            
            # Generic Challenge Pages
            'unusual traffic', 'automated requests detected',
            'suspected automated behavior', 'unusual activity'
        ]
        
        # Convert to lowercase for case-insensitive matching
        content_lower = markdown_content.lower()
        
        # Check for security indicators
        for indicator in security_indicators:
            if indicator in content_lower:
                logger.info(f"Security indicator found: '{indicator}' in {getattr(result, 'url', 'unknown URL')}")
                return True
            
        
        # Additional checks for specific HTML patterns
        security_patterns = [
            '<title>just a moment', '<title>please wait', 
            '<title>access denied', '<title>blocked',
            'data-cf-beacon', 'cf-browser-verification',
            'cookie-banner', 'cookie-notice', 'gdpr-banner'
        ]
        
        for pattern in security_patterns:
            if pattern in content_lower:
                logger.info(f"Security pattern found: '{pattern}' in {getattr(result, 'url', 'unknown URL')}")
                return True
        
        return False

    def _looks_blocked_or_empty(self, url: str, status: int, html: str, markdown: str) -> bool:
        """Check if content looks blocked or empty"""
        # Clearly empty / too short
        if not markdown or len(markdown.strip()) < 150:
            return True

        # Reuse your security checker (wrap url)
        try:
            pseudo = SimpleNamespace(url=url)
            if self._is_security_challenge(markdown, pseudo):
                return True
        except Exception:
            pass

        # Obvious patterns: mostly scripts, no real text
        visible_ratio = len(markdown) / max(len(html), 1)
        if visible_ratio < 0.02:  # 2% of HTML turns into text -> suspicious (heavily JS app shell)
            return True

        return False

    async def detect_javascript_need(self, html: str, markdown: str = None) -> bool:
        """
        Detect if page requires JavaScript rendering

        Analyzes HTML (and optionally markdown) to determine if content is loaded dynamically via JavaScript.

        Args:
            html: Raw HTML content from HTTP request
            markdown: Optional markdown conversion of HTML for additional checks

        Returns:
            True if page likely needs JavaScript rendering, False otherwise

        Detection heuristics:
        - Markdown is very short (<300 chars) indicating minimal rendered content
        - Very little visible content (<200 chars after stripping tags)
        - Contains JS framework markers (React, Vue, Angular, Next.js)
        - Has <noscript> warning messages about JavaScript
        - Body is mostly <script> tags with minimal static content
        - Contains common SPA loading indicators
        """
        if not html or len(html) < 100:
            return False

        # 0. Check markdown length if provided
        if markdown and len(markdown.strip()) < 300:
            logger.info(f"Short markdown content ({len(markdown)} chars) - likely needs JS")
            return True

        html_lower = html.lower()

        # 1. Check for JS framework markers
        js_frameworks = [
            'data-reactroot',
            'data-react',
            '__next',  # Next.js
            'ng-app',  # Angular
            'ng-version',
            'v-cloak',  # Vue
            'data-vue',
            'id="app"',
            'id="root"',
            '__nuxt',  # Nuxt.js
        ]

        if any(marker in html_lower for marker in js_frameworks):
            marker = next(m for m in js_frameworks if m in html_lower)
            logger.info(f"Detected JS framework markers in HTML: {marker}")
            return True

        # 2. Check for noscript warnings
        if '<noscript>' in html_lower:
            noscript_warnings = [
                'enable javascript',
                'javascript is disabled',
                'requires javascript',
                'turn on javascript',
                'javascript must be enabled'
            ]
            if any(warning in html_lower for warning in noscript_warnings):
                logger.info("Detected noscript JavaScript warning")
                return True

        # 3. Check if body is mostly empty except for scripts
        try:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(html, 'html.parser')

            # Remove script and style tags
            for tag in soup(['script', 'style', 'noscript']):
                tag.decompose()

            # Get visible text
            visible_text = soup.get_text(strip=True)

            # If very little visible content, likely needs JS
            if len(visible_text) < 200:
                logger.info(f"Very little visible content ({len(visible_text)} chars) - likely needs JS")
                return True

        except Exception as e:
            logger.warning(f"Error parsing HTML for JS detection: {e}")

        # 4. Check for common SPA loading indicators
        loading_indicators = [
            'loading...',
            'please wait',
            'data-server-rendered="false"'
        ]

        if any(indicator in html_lower for indicator in loading_indicators):
            logger.info("Detected SPA loading indicator")
            return True

        return False

    async def _fetch_urls_via_requests(
        self,
        urls: List[str],
        *,
        max_concurrency: int,
        timeout: int
    ) -> List[Dict[str, Any]]:
        """
        Fetch pages via raw HTTP (no JS). Converts HTML -> markdown with your generator.
        Uses simple backoff for 429/5xx (and sometimes 403).
        """
        if not urls:
            return []

        limits = httpx.Limits(
            max_connections=max_concurrency,
            max_keepalive_connections=max_concurrency,
            keepalive_expiry=30.0,
        )
        
        # Configure single proxy for httpx (prefers HTTPS proxy)
        proxy = None
        if self.https_proxy:
            proxy = self.https_proxy
        elif self.http_proxy:
            proxy = self.http_proxy

        sem = asyncio.Semaphore(max_concurrency)
        headers = dict(self.default_headers)

        async with httpx.AsyncClient(
            headers=headers,
            limits=limits,
            http2=True,
            proxy=proxy,
            follow_redirects=True,
            timeout=httpx.Timeout(timeout)
        ) as client:
            async def fetch_one(url: str) -> Dict[str, Any]:
                async with sem:
                    try:
                        logging.info(f"Requests fetching: {url} with timeout {timeout}s")
                        start_time = time.time()
                        r = await asyncio.wait_for(
                            client.get(url),
                            timeout=timeout
                        )
                        logging.info(f"Requests fetched {url} with status {r.status_code} after {time.time() - start_time:.2f}s")
                        status = r.status_code
                        text = r.text if r.text is not None else ""

                        if 200 <= status < 300 and text:
                            md = await self._convert_html_to_markdown(text)
                            blocked = self._looks_blocked_or_empty(url, status, text, md)

                            # Detect if page needs JavaScript rendering
                            # needs_js = await self.detect_javascript_need(text, md)

                            if not blocked:
                                return {
                                    "url": str(r.url),
                                    "deduplicated_markdown": md,
                                    "html": text,
                                    "meta": {
                                        "source_type": "requests",
                                        "status_code": status,
                                        "response_headers": dict(r.headers),
                                        "final_url": str(r.url),
                                        "content_length": len(text),
                                        "needs_js": False,
                                    },
                                    "success": True,
                                    "error": None,
                                }
                            else:
                                # treat as failed so next layer can try with JS rendering if needed
                                return {
                                    "url": str(r.url),
                                    "deduplicated_markdown": "",
                                    "meta": {
                                        "source_type": "requests",
                                        "status_code": status,
                                        "final_url": str(r.url),
                                        "blocked_like": blocked,
                                    },
                                    "success": False,
                                    "error": "JS rendering required",
                                }

                        # Non-2xx or empty body
                        err = f"HTTP {status}"
                        return {"url": url, "deduplicated_markdown": "", "meta": {"source_type": "requests"}, "success": False, "error": err}
                    except Exception as e:
                        return {"url": url, "deduplicated_markdown": "", "meta": {"source_type": "requests"}, "success": False, "error": str(e)}

            results = await asyncio.gather(*(fetch_one(u) for u in urls))
            return results

    async def _ensure_crawler(self):
        """Initialize crawler if not already initialized"""
        if not self.crawler:
            # Create the crawler with our custom strategy and config
            self.crawler = AsyncWebCrawler(
                crawler_strategy=self.crawler_strategy,
                config=self.browser_config
            )
            await self.crawler.start()
    
    async def crawl_pages(
        self,
        urls: List[str],
        requests_timeout: int = 10,
        api_timeout: int = 30,
        browser_timeout: int = 30,
        wait_until: str = "domcontentloaded"
    ) -> List[Dict[str, Any]]:
        """
        Multi-level crawling with configurable levels
        Each level tries to fetch failed URLs from the previous level

        Args:
            urls: List of URLs to crawl
            requests_timeout: Timeout for direct HTTP requests in seconds (default: 10)
            api_timeout: Timeout for API-based crawling in seconds (default: 30)
            browser_timeout: Timeout for browser-based crawling in seconds (default: 30)
            wait_until: Wait condition for page load

        Returns:
            List of crawled pages with markdown and metadata
        """
        if not urls:
            return []
        
        start_time = time.time()
        logger.info(f"Starting multi-level crawl for {len(urls)} URLs using levels: {self.crawl_levels}")
        logging.info("Urls to crawl: " + ", ".join(urls))
        # Initialize results with failed state for all URLs
        results = []
        for url in urls:
            results.append({
                'url': url,
                'deduplicated_markdown': '',
                'meta': {},
                'success': False,
                'error': 'Not yet attempted'
            })
        
        # Keep track of URLs to try at each level
        urls_to_try = urls.copy()

        # Loop through each configured level
        for level_idx, level in enumerate(self.crawl_levels):
            if not urls_to_try:
                break

            logger.info(f"Level {level_idx + 1} ({level}): Trying {len(urls_to_try)} URLs")

            # Execute the appropriate crawling method for this level
            if level == "requests":
                level_results = await self._fetch_urls_via_requests(
                    urls_to_try,
                    max_concurrency=self.requests_concurrency,
                    timeout=self.requests_timeout
                )
            elif level == "crawl4ai":
                if not self.use_browser:
                    logger.warning("crawl4ai level requested but use_browser=False, skipping")
                    continue
                level_results = await self._crawl_with_crawl4ai(urls_to_try, browser_timeout, wait_until)
            elif level == "apis":
                level_results = await self.crawl_via_apis(
                    urls_to_try,
                    max_concurrent_requests=self.requests_concurrency,
                    timeout_per_url=api_timeout
                )
            else:
                logger.error(f"Unknown level: {level}")
                continue

            # Update results with successful ones from this level and track latest errors
            successful_urls = set()
            url_to_level_result = {r["url"]: r for r in level_results}

            for i, result in enumerate(results):
                if result["url"] in url_to_level_result:
                    level_result = url_to_level_result[result["url"]]
                    if level_result["success"]:
                        # Success: update full result
                        results[i] = level_result
                        successful_urls.add(result["url"])
                    else:
                        # Failed: update error message
                        results[i]["error"] = level_result.get("error", f"Failed at level {level}")

            # Prepare URLs for next level (only failed ones)
            urls_to_try = [url for url in urls_to_try if url not in successful_urls]

            successful_count = len(successful_urls)
            logger.info(f"Level {level_idx + 1} ({level}): {successful_count} successful, {len(urls_to_try)} remaining")
        
        return await self._finalize_results(results)

    async def _crawl_with_crawl4ai(
        self, 
        urls: List[str], 
        timeout: int, 
        wait_until: str
    ) -> List[Dict[str, Any]]:
        """Original crawl4ai implementation"""
        await self._ensure_crawler()
        
        # Create crawler configs for each URL with aggressive spam filtering
        configs = []
        for url in urls:
            config = CrawlerRunConfig(
                markdown_generator=self.markdown_generator,
                wait_until=wait_until,
                capture_console_messages=True,
                excluded_tags=[
                    'nav', 'footer', 'aside', 'header', 'script', 'style', 'noscript',
                    'iframe', 'embed', 'object', 'form', 'input', 'button', 'select',
                    'textarea', 'fieldset', 'legend', 'label'
                ]
            )
            configs.append(config)
        
        results = []
        
        try:
            # Run crawls in parallel
            crawl_results = await self.crawler.arun_many(urls, configs)
            
            # Process results
            for i, result in enumerate(crawl_results):
                if result.success and hasattr(result, 'status_code') and result.status_code == 200:
                    # Extract markdown content
                    fit_markdown_content = ""
                    
                    if hasattr(result, 'markdown') and result.markdown:
                        if hasattr(result.markdown, 'fit_markdown'):
                            fit_markdown_content = result.markdown.fit_markdown
                        elif hasattr(result.markdown, 'raw_markdown'):
                            fit_markdown_content = result.markdown.raw_markdown
                        else:
                            fit_markdown_content = str(result.markdown)
                    
                    # Apply spam removal and deduplication
                    fit_markdown_content = content_utils.spam_removal(fit_markdown_content, aggressive=True)
                    fit_markdown_content = content_utils.deduplicate_paragraphs(fit_markdown_content)
                    
                    # Check for security challenges
                    if self._is_security_challenge(fit_markdown_content, result):
                        logger.warning(f"Security challenge detected for {result.url}")
                        page_data = {
                            'url': result.url,
                            'deduplicated_markdown': '',
                            'meta': {"source_type": "crawl4ai"},
                            'success': False,
                            'error': 'Security challenge/bot detection page detected'
                        }
                    else:
                        page_data = {
                            'url': result.url,
                            'deduplicated_markdown': fit_markdown_content,
                            'html': result.html if hasattr(result, 'html') else '',
                            'meta': self._extract_metadata(result),
                            'success': True,
                            'error': None
                        }
                else:
                    # HTTP failure or other crawl error
                    error_msg = 'Crawl failed'
                    if hasattr(result, 'status_code') and result.status_code != 200:
                        error_msg = f'HTTP {result.status_code}'
                    elif hasattr(result, 'error'):
                        error_msg = str(result.error)
                    
                    page_data = {
                        'url': urls[i],
                        'deduplicated_markdown': '',
                        'meta': {"source_type": "crawl4ai"},
                        'success': False,
                        'error': error_msg
                    }
                
                results.append(page_data)
                
        except Exception as e:
            logger.error(f"Crawl4AI batch crawl failed: {e}")
            # Return failed results for all URLs
            for url in urls[len(results):]:
                results.append({
                    'url': url,
                    'deduplicated_markdown': '',
                    'meta': {"source_type": "crawl4ai"},
                    'success': False,
                    'error': str(e)
                })
        
        return results

    async def _finalize_results(self, results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Apply final processing to results"""
        # Apply cross-page paragraph deduplication
        if len(results) > 1:
            results = content_utils.aggregate_and_dedup(results, similarity_threshold=0.85, content_key='deduplicated_markdown')
            logger.info(f"Applied cross-page paragraph deduplication to {len(results)} pages")

        # Track failed URLs and log summary
        failed_count = sum(1 for r in results if not r['success'])
        successful_count = len(results) - failed_count

        # MEMORY LEAK FIX: Only track failed URLs for this session, clear old ones
        session_failed_urls = set()
        for result in results:
            if not result['success']:
                session_failed_urls.add(result['url'])

        # Clear old failed URLs to prevent memory leak, keep only recent ones
        self.failed_urls.clear()
        self.failed_urls.update(session_failed_urls)

        logger.info(f"Final crawl results: {successful_count}/{len(results)} successful, {failed_count} failed")
        return results
    
    async def crawl_via_apis(self, urls: List[str], max_concurrent_requests: int = 10, timeout_per_url: int = 30) -> List[Dict[str, Any]]:
        """
        Crawl URLs using API services for failed domains only with parallel processing
        Priority: Scraping Dog → Bright Data → Failure
        Returns same format as crawl_pages()

        Args:
            urls: List of URLs to crawl
            max_concurrent_requests: Maximum number of concurrent API requests (default: 3)
            timeout_per_url: Timeout per URL in seconds (default: 60)
        """
        if not urls:
            return []

        logger.info(f"Starting parallel API-based crawling for {len(urls)} URLs with {max_concurrent_requests} concurrent workers and {timeout_per_url}s per URL timeout")

        # Create semaphore to limit concurrent requests
        semaphore = asyncio.Semaphore(max_concurrent_requests)

        # Create tasks for all URLs with timeout wrapper
        tasks = [
            asyncio.wait_for(
                self._crawl_single_url_via_apis(url, semaphore),
                timeout=timeout_per_url
            )
            for url in urls
        ]

        # Execute all tasks in parallel using gather
        gather_results = await asyncio.gather(*tasks, return_exceptions=True)

        # Process results and handle exceptions
        results = []
        for i, result in enumerate(gather_results):
            if isinstance(result, asyncio.TimeoutError):
                logger.warning(f"API crawl timeout after {timeout_per_url}s for {urls[i]}")
                results.append({
                    'url': urls[i],
                    'deduplicated_markdown': '',
                    'meta': {'source_type': 'api_timeout'},
                    'success': False,
                    'error': f'Timeout after {timeout_per_url}s'
                })
            elif isinstance(result, Exception):
                logger.error(f"API crawl exception for {urls[i]}: {result}")
                results.append({
                    'url': urls[i],
                    'deduplicated_markdown': '',
                    'meta': {'source_type': 'api_error'},
                    'success': False,
                    'error': str(result)
                })
            else:
                results.append(result)

        successful_count = sum(1 for r in results if r['success'])
        logger.info(f"Parallel API crawling completed: {successful_count}/{len(results)} successful")
        return results
    
    def crawl_via_apis_sync(self, urls: List[str], max_concurrent_requests: int = 10) -> List[Dict[str, Any]]:
        """
        Synchronous wrapper for crawl_via_apis for backward compatibility
        """
        return asyncio.run(self.crawl_via_apis(urls, max_concurrent_requests))
    
    async def _crawl_single_url_via_apis(self, url: str, semaphore: asyncio.Semaphore, api_timeout: int = 30, needs_js: bool = False) -> Dict[str, Any]:
        """
        Crawl a single URL using API services with semaphore for concurrency control
        Priority: Scraping Dog → Bright Data → Failure
        Returns same format as crawl_via_apis()

        Args:
            url: URL to crawl
            semaphore: Concurrency control semaphore
            api_timeout: Timeout for individual API calls in seconds (default: 30)
            needs_js: Whether to enable JavaScript rendering in ScrapingDog (default: False)
        """
        async with semaphore:
            logger.info(f"Attempting API crawl for: {url} (needs_js={needs_js})")

            # Try Scraping Dog first with timeout and JS rendering if needed
            try:
                logger.info(f"Trying Scraping Dog for {url} with {api_timeout}s timeout and js_rendering={needs_js}")
                dog_result = await asyncio.wait_for(
                    self.scraping_dog.scrape_page_async(url, js_rendering=needs_js),
                    timeout=api_timeout
                )

                if dog_result['success'] and dog_result['html_content']:
                    logger.info(f"Scraping Dog success for {url}")
                    markdown_content = await self._convert_html_to_markdown(dog_result['html_content'])
                    # Check if page needs JS rendering (only if we didn't already try with JS)
                    if self._is_security_challenge(markdown_content, SimpleNamespace(url=url)) and not needs_js:
                        logger.info(f"Detected security challenge need for {url}, retrying with js_rendering=True")
                        try:
                            dog_result_js = await asyncio.wait_for(
                                self.scraping_dog.scrape_page_async(url, js_rendering=True),
                                timeout=api_timeout
                            )
                            if dog_result_js['success'] and dog_result_js['html_content']:
                                logger.info(f"Scraping Dog with JS success for {url}")
                                markdown_content = await self._convert_html_to_markdown(dog_result_js['html_content'])
                                return self._format_api_result(url, markdown_content, dog_result_js['html_content'], 'scraping_dog_js', dog_result_js)
                        except Exception as e:
                            logger.warning(f"Scraping Dog JS retry failed for {url}: {e}")
                            # Continue with non-JS result
                    return self._format_api_result(url, markdown_content, dog_result['html_content'], 'scraping_dog', dog_result)
                else:
                    logger.warning(f"Scraping Dog failed for {url}: {dog_result.get('error', 'Unknown error')}")

            except asyncio.TimeoutError:
                logger.warning(f"Scraping Dog timeout after {api_timeout}s for {url}")
            except Exception as e:
                logger.error(f"Scraping Dog exception for {url}: {e}")

            # Fallback to Bright Data with timeout
            try:
                logger.info(f"Trying Bright Data for {url} with {api_timeout}s timeout")
                bright_data_result = await asyncio.wait_for(
                    self.bright_data.scrape_page_async(url),
                    timeout=api_timeout
                )

                if bright_data_result['success'] and bright_data_result['html_content']:
                    logger.info(f"Bright Data success for {url}")
                    markdown_content = await self._convert_html_to_markdown(bright_data_result['html_content'])
                    return self._format_api_result(url, markdown_content, bright_data_result['html_content'], 'bright_data', bright_data_result)
                else:
                    logger.warning(f"Bright Data failed for {url}: {bright_data_result.get('error', 'Unknown error')}")

            except asyncio.TimeoutError:
                logger.warning(f"Bright Data timeout after {api_timeout}s for {url}")
            except Exception as e:
                logger.error(f"Bright Data exception for {url}: {e}")

            # Both APIs failed
            logger.error(f"All API services failed for {url}")
            return {
                'url': url,
                'html': '',
                'deduplicated_markdown': '',  # Empty markdown for failed pages
                'meta': {
                    'api_used': 'none',
                    'all_apis_failed': True,
                    'source_type': 'api_failed'
                },
                'success': False,
                'error': 'All API services failed'
            }
    
    async def crawl_single(self, url: str, **kwargs) -> Dict[str, Any]:
        """Convenience method to crawl a single URL"""
        results = await self.crawl_pages([url], **kwargs)
        return results[0] if results else None
    
    async def _convert_html_to_markdown(self, html_content: str) -> str:
        """
        Convert HTML content to markdown using Crawl4AI's markdown generator
        Used for API responses from Scraping Dog and Bright Data
        """
        try:
            # Generate markdown using the same generator as crawl_pages with 3s timeout
            logging.info(f"Converting HTML to markdown using Crawl4AI markdown generator for {len(html_content)} characters")

            # Wrap markdown generation in timeout to prevent large content from hanging
            markdown_result = await asyncio.wait_for(
                asyncio.to_thread(
                    self.markdown_generator.generate_markdown,
                    input_html=html_content,
                    base_url="",
                    content_filter=self.markdown_generator.content_filter,
                    citations=False
                ),
                timeout=3.0
            )

            # Extract markdown content - prefer fit_markdown if available
            if hasattr(markdown_result, 'fit_markdown') and markdown_result.fit_markdown:
                markdown_content = markdown_result.fit_markdown
            elif hasattr(markdown_result, 'raw_markdown') and markdown_result.raw_markdown:
                markdown_content = markdown_result.raw_markdown
            else:
                markdown_content = str(markdown_result)

            # Apply spam removal and deduplication like crawl_pages
            markdown_content = content_utils.spam_removal(markdown_content, aggressive=True)
            markdown_content = content_utils.deduplicate_paragraphs(markdown_content)

            # html2text_content = html2text(html_content)
            # if len(html2text_content) > len(markdown_content) * 1.5:
            #     logger.info("html2text produced significantly more content, using it instead")
            #     markdown_content = html2text_content

            return markdown_content

        except asyncio.TimeoutError:
            logger.warning(f"Markdown conversion timed out after 3s for {len(html_content)} character content - returning empty")
            return ""
        except Exception as e:
            logger.error(f"Failed to convert HTML to markdown: {e}")
            return ""
    
    def _format_api_result(self, url: str, markdown_content: str, html_content: str, api_used: str, api_response: Dict[str, Any]) -> Dict[str, Any]:
        """
        Format API crawling result to match crawl_pages output format
        """
        return {
            'url': url,
            'deduplicated_markdown': markdown_content,  # Already deduplicated in conversion
            'html': html_content,
            'meta': {
                'api_used': api_used,
                'source_type': 'api',
                'api_response_size': len(api_response.get('html_content', ''))
            },
            'success': True,
            'error': None
        }
    
    def _extract_metadata(self, result) -> Dict[str, Any]:
        """Extract metadata from crawl result"""
        meta = {'source_type': 'crawl4ai'}
        
        if hasattr(result, 'status_code'):
            meta['status_code'] = result.status_code
        if hasattr(result, 'response_headers'):
            meta['response_headers'] = dict(result.response_headers) if result.response_headers else {}
        if hasattr(result, 'links'):
            meta['links_found'] = len(result.links) if result.links else 0
        if hasattr(result, 'media'):
            meta['media_found'] = len(result.media) if result.media else 0
            
        return meta
    
    async def close(self):
        """Clean up crawler resources"""
        if self.crawler:
            await self.crawler.close()
            self.crawler = None

    async def cleanup(self):
        """Clean up all resources including API client connections"""
        # Clean up crawler if exists
        if self.crawler:
            try:
                await self.crawler.close()
            except Exception as e:
                logger.warning(f"Error closing crawler: {e}")
            finally:
                self.crawler = None

        # Clean up ScrapingDog Redis connections
        if hasattr(self, 'scraping_dog') and self.scraping_dog:
            try:
                await self.scraping_dog.cleanup()
            except Exception as e:
                logger.warning(f"Error cleaning up ScrapingDog client: {e}")

        # Note: BrightDataClient doesn't have persistent connections to clean up
        logger.debug("CrawlAdapter cleanup completed")