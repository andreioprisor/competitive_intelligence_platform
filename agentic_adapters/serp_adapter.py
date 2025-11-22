import json
import os
from typing import List, Dict, Any, Optional, Tuple
import logging
from urllib.parse import urlparse
import time
import requests
from requests.exceptions import HTTPError

logger = logging.getLogger(__name__)

class SerpAdapter:
    """Google Serper.dev API adapter for web search. Use domain and DP name for logging context."""

    def __init__(self, api_key: Optional[str] = None, company_domain: Optional[str] = None, target_dp_name: Optional[str] = None):
        self.api_key = api_key or os.getenv('SERPER_API_KEY')
        if not self.api_key:
            raise ValueError("SERPER_API_KEY not found in environment")

        self.base_url = "https://google.serper.dev"
        self.ai_overviews = []  # Store AI Overview content
        self.company_domain = company_domain  # Store for logging context
        self.target_dp_name = target_dp_name  # Store for logging context

    def _get_log_extra(self):
        """Get logging extra context with domain and datapoint info"""
        return {
            "domain": self.company_domain,
            "datapoint_name": self.target_dp_name
        }
    
    def search(self, query: str, num: int = 10, location: str = "ro", country_code: str = "us") -> List[Dict[str, Any]]:
        """
        Execute search query and return ranked results

        Args:
            query: Search query string
            num: Number of results to return
            location: Geographic location for search
            country_code: ISO 3166-1 alpha-2 country code (e.g., "us", "ro", "de")

        Returns:
            List of search results with url, title, snippet, and score
        """
        try:
            # Prepare request payload
            payload = {
                "q": query,
                "num": 10,
                "gl": country_code
            }

            logging.info(f"Executing SERP search for query: '{query}' in country: '{country_code}'", extra=self._get_log_extra())

            headers = {
                'X-API-KEY': self.api_key,
                'Content-Type': 'application/json'
            }

            # Make API request using requests library
            start_time = time.time()
            response = requests.post(
                f"{self.base_url}/search",
                json=payload,
                headers=headers,
                timeout=30
            )
            elapsed = time.time() - start_time

            # Check response status
            response.raise_for_status()

            # Parse response
            result = response.json()

            # Log metrics
            logger.info(f"SERP query '{query}' returned {len(result.get('organic', []))} results in {elapsed:.2f}s", extra=self._get_log_extra())

            # Process results - keep original SERP order (no custom scoring)
            candidates = []
            for idx, item in enumerate(result.get('organic', [])):
                candidate = {
                    'url': item.get('link', ''),
                    'title': item.get('title', ''),
                    'snippet': item.get('snippet', ''),
                    'position': idx + 1
                }

                # Include rating data if available
                if 'rating' in item:
                    candidate['rating'] = item['rating']
                if 'ratingCount' in item:
                    candidate['ratingCount'] = item['ratingCount']

                # Include date if available
                if 'date' in item:
                    candidate['date'] = item['date']

                # Include sitelinks if available
                if 'sitelinks' in item:
                    candidate['sitelinks'] = item['sitelinks']

                candidates.append(candidate)

            print(f"🔍 Found {len(candidates)} results for '{query}'")
            return candidates[:num]

        except HTTPError as e:
            status_code = e.response.status_code if hasattr(e, 'response') else None
            # Log detailed error info for 400 errors
            if status_code == 400:
                logger.error(f"Serper.dev 400 Bad Request for query '{query}': {e}", extra=self._get_log_extra())
                if hasattr(e, 'response'):
                    logger.error(f"Response body: {e.response.text[:500]}", extra=self._get_log_extra())
            logger.error(f"SERP search HTTP error for query '{query}': status={status_code}", extra=self._get_log_extra())
            raise

        except Exception as e:
            logger.error(f"SERP search failed for query '{query}': {e}", extra=self._get_log_extra())
            raise

    async def _async_scrapingdog_fallback(self, query: str, num: int, country_code: str) -> List[Dict[str, Any]]:
        """
        Async fallback to ScrapingDog Google Search when Serper fails

        Args:
            query: Search query string
            num: Number of results to return
            country_code: ISO 3166-1 alpha-2 country code

        Returns:
            List of search results
        """
        try:
            from leadora.adapters.agentic_adapters.api_crawlers import ScrapingDogClient

            logger.info(f"Using ScrapingDog fallback for query: '{query}'", extra=self._get_log_extra())
            scraping_dog = ScrapingDogClient()
            results = await scraping_dog.async_google_search(query=query, num=num, country=country_code)

            logger.info(f"ScrapingDog fallback returned {len(results)} results", extra=self._get_log_extra())
            return results

        except Exception as e:
            logger.error(f"ScrapingDog fallback also failed for query '{query}': {e}", extra=self._get_log_extra())
            return []


    async def batch_search(self, queries: List[Dict[str, Any]], max_per_query: int = 5, max_total: int = 10) -> Tuple[Dict[str, List[Dict[str, Any]]], List[Dict[str, Any]]]:
        """
        Execute multiple queries and return results grouped by query

        Args:
            queries: List of query objects with 'query', 'ai_overview_needed', and 'reasoning' fields
            max_per_query: Max results per individual query
            max_total: Max total results to return (not used in grouped mode)

        Returns:
            Tuple of (results_by_query, ai_overview_content)
        """
        if not queries:
            return {}, []

        # Clear any existing AI overviews
        self.clear_ai_overviews()

        results_by_query = {}
        seen_exact_urls = set()  # Track exact URLs for deduplication

        for query_obj in queries:
            query_str = query_obj.get("query", "")
            ai_overview_needed = query_obj.get("ai_overview_needed", False)
            country_code = query_obj.get("country_code", "us")  # Default to US if not specified
            reasoning = query_obj.get("reasoning", "")
            if ai_overview_needed:
                country_code = "us"  # AI Overview only supported in US for now
            country_code = country_code.lower()

            if not query_str:
                continue

            # Use ai_search if AI Overview is needed, otherwise regular search
            if ai_overview_needed:
                results = await self.ai_search(query_str, reasoning)  # AI search doesn't use country code for now
            else:
                # Try Serper first, fallback to ScrapingDog on failure
                try:
                    results = self.search(query_str, num=max_per_query, country_code=country_code)
                except Exception as e:
                    logger.warning(f"SERP failed for '{query_str}', using ScrapingDog: {e}")
                    results = await self._async_scrapingdog_fallback(query_str, max_per_query, country_code)

            # Store results for this query, deduplicating only exact URLs
            query_results = []
            for result in results:
                url = result['url']
                if url not in seen_exact_urls:
                    seen_exact_urls.add(url)
                    result['source_query'] = query_str
                    query_results.append(result)

            results_by_query[query_str] = query_results[:max_per_query]

        # Return grouped results and AI overviews
        return results_by_query, self.get_ai_overviews()
    
    def _canonicalize_url(self, url: str) -> str:
        """Remove URL parameters and fragments for deduplication"""
        parsed = urlparse(url)
        # Keep scheme, netloc, and path only
        return f"{parsed.scheme}://{parsed.netloc}{parsed.path}".rstrip('/')

    def _get_deduplication_key_simple(self, url: str) -> str:
        """
        Simple approach: remove known tracking parameters to create deduplication key
        """
        import re

        # Remove common tracking parameters
        clean_url = url.lower()

        # Remove Google SERP tracking
        clean_url = re.sub(r'[?&]srsltid=[^&]*', '', clean_url)
        clean_url = re.sub(r'[?&]ved=[^&]*', '', clean_url)
        clean_url = re.sub(r'[?&]usg=[^&]*', '', clean_url)
        clean_url = re.sub(r'[?&]sa=[^&]*', '', clean_url)
        clean_url = re.sub(r'[?&]ei=[^&]*', '', clean_url)

        # Remove UTM tracking parameters
        clean_url = re.sub(r'[?&]utm_[^&]*=[^&]*', '', clean_url)

        # Remove other common tracking parameters
        clean_url = re.sub(r'[?&]gclid=[^&]*', '', clean_url)
        clean_url = re.sub(r'[?&]fbclid=[^&]*', '', clean_url)

        # Clean up malformed query strings (remove dangling ? or &)
        clean_url = re.sub(r'[?&]$', '', clean_url)
        clean_url = re.sub(r'\?&', '?', clean_url)

        # Normalize domain (remove www)
        clean_url = clean_url.replace('://www.', '://')

        # Remove trailing slash
        clean_url = clean_url.rstrip('/')

        return clean_url

    def _remove_duplicates(self, all_candidates: List[Dict]) -> Tuple[List[Dict], int]:
        """
        Remove duplicates by identifying tracking parameters and grouping
        Returns (deduplicated_candidates, removed_count)
        """
        groups = {}

        for candidate in all_candidates:
            original_url = candidate.get('url', '')
            # Generate key by removing tracking params
            dedup_key = self._get_deduplication_key_simple(original_url)

            if dedup_key not in groups:
                groups[dedup_key] = []
            groups[dedup_key].append(candidate)

        # Keep best candidate from each group
        deduplicated = []
        removed_count = 0
        duplicate_groups = []

        for dedup_key, candidates in groups.items():
            if len(candidates) > 1:
                # Multiple candidates - keep the first one (highest SERP ranking)
                best = candidates[0]
                removed = candidates[1:]
                removed_count += len(removed)

                # Log detailed deduplication info
                kept_url = best.get('url', '')
                removed_urls = [c.get('url', '') for c in removed]

                logger.info(f"DEDUPLICATION GROUP: {len(candidates)} URLs with same content", extra=self._get_log_extra())
                logger.info(f"  ✓ KEPT (highest rank): {kept_url}", extra=self._get_log_extra())
                for i, removed_url in enumerate(removed_urls, 1):
                    logger.info(f"  ✗ REMOVED #{i}: {removed_url}", extra=self._get_log_extra())
                logger.info(f"  → Normalized key: {dedup_key}", extra=self._get_log_extra())

                duplicate_groups.append({
                    'key': dedup_key,
                    'total': len(candidates),
                    'kept': kept_url,
                    'removed': removed_urls
                })
            else:
                best = candidates[0]

            deduplicated.append(best)

        if duplicate_groups:
            logger.info(f"DEDUPLICATION SUMMARY: Found {len(duplicate_groups)} duplicate groups, removed {removed_count} total URLs", extra=self._get_log_extra())
            for i, group in enumerate(duplicate_groups, 1):
                logger.info(f"  Group {i}: {group['total']} URLs → kept 1, removed {len(group['removed'])}", extra=self._get_log_extra())
        else:
            logger.info(f"DEDUPLICATION: No duplicates found in {len(all_candidates)} candidates", extra=self._get_log_extra())

        logger.info(f"Final result: {len(all_candidates)} → {len(deduplicated)} candidates", extra=self._get_log_extra())
        return deduplicated, removed_count
    
    def rerank_candidates(
        self,
        results_by_query: Dict[str, List[Dict[str, Any]]],
        company_context: Dict[str, Any],
        subtask: Dict[str, Any],
        datapoint_definition: Optional[Dict[str, Any]] = None,
        max_candidates: int = 8,
        reranker_prompt_path: Optional[str] = None
    ) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        """
        Intelligently rerank SERP candidates based on company and datapoint relevance

        Args:
            results_by_query: Dict mapping queries to their results
            company_context: Company information for matching
            subtask: Research goal and context
            datapoint_definition: Optional datapoint requirements
            max_candidates: Maximum candidates to return
            reranker_prompt_path: Optional path to custom reranker prompt (uses simplified approach if None)

        Returns:
            Tuple of (ranked_candidates, rerank_metadata)
        """
        if not results_by_query:
            return [], {"total_input": 0, "filtered_count": 0, "discarded_count": 0}

        try:
            from .llm_adapter import LLMAdapter
            import re
            import random
            import time

            llm_adapter = LLMAdapter()

            # Prepare candidates text
            candidates_text = ""
            all_candidates = []

            for query, results in results_by_query.items():
                if not results:
                    continue

                candidates_text += f"\nQuery: \"{query}\"\n"

                for result in results:
                    url = result.get("url", "")
                    if url.lower().endswith('.pdf'):
                        logger.info(f"Skipping PDF URL: {url}", extra=self._get_log_extra())
                        continue

                    title = result.get("title", "")
                    snippet = result.get("snippet", "")
                    combined_text = f"{title} {snippet}".strip()

                    candidates_text += f"- {url}: {combined_text}\n"
                    all_candidates.append(result)

            # Remove duplicates before reranking
            original_candidate_count = len(all_candidates)
            all_candidates, duplicates_removed = self._remove_duplicates(all_candidates)

            # Create prompt based on whether custom path is provided
            if reranker_prompt_path:
                # Use custom prompt template
                serp_queries = list(results_by_query.keys())
                formatted_prompt = llm_adapter.format_prompt_with_template(
                    reranker_prompt_path,
                    company_context_json=company_context,
                    datapoint_definition_json=datapoint_definition or {},
                    serp_queries=serp_queries,
                    candidates_text=candidates_text
                )
                logging.info(f"Using custom reranker prompt from: {reranker_prompt_path}", extra=self._get_log_extra())
                with open("reranker_formatted_prompt.md", "w") as f:
                    f.write(formatted_prompt)
                method = "custom_prompt_reranking"
            else:
                # Use simplified built-in prompt
                company_name = company_context.get('name', '')
                domain = company_context.get('domain', '')
                company_desc = company_context.get('description', '')[:200] + "..." if len(company_context.get('description', '')) > 200 else company_context.get('description', '')

                datapoint_name = datapoint_definition.get('dp_name', '') if datapoint_definition else ''
                datapoint_desc = datapoint_definition.get('description', '') if datapoint_definition else ''

                serp_queries = list(results_by_query.keys())

                formatted_prompt = f"""You are a URL relevance ranker. Given a company and datapoint, rank URLs by how likely they contain information relevant to the datapoint for that company.

COMPANY: {company_name} ({domain}) - {company_desc}
DATAPOINT: {datapoint_name} - {datapoint_desc}

RANKING CRITERIA:
1. URL is about the target company (not competitors/other companies)
2. Content relates to the specific datapoint we're extracting
3. Contains actionable information that could answer our datapoint question

SEARCH QUERIES: {serp_queries}

URLS TO RANK:
{candidates_text}

OUTPUT FORMAT:
Return only the top {max_candidates} URLs in ranked order (most relevant first), one per line. Skip irrelevant URLs. Don't include anything else in your response."""
                method = "simplified_llm_reranking"

            # Retry logic: attempt up to 2 times if no URLs returned
            retry_attempted = False
            retry_successful = False
            final_candidates = []

            for attempt in range(2):
                temperature = 0.2 if attempt == 0 else 0.5

                # Get LLM response
                response = llm_adapter.get_completion(formatted_prompt, temperature=temperature)

                # Parse URLs from response
                lines = [line.strip() for line in response.strip().split('\n') if line.strip()]
                ranked_urls = []

                for line in lines:
                    if line.startswith('http'):
                        ranked_urls.append(line)
                    else:
                        url_match = re.search(r'(https?://[^\s]+)', line)
                        if url_match:
                            ranked_urls.append(url_match.group(1))

                # Match URLs back to original candidates
                candidate_lookup = {c["url"]: c for c in all_candidates}
                ranked_candidates = []
                for url in ranked_urls:
                    original = candidate_lookup.get(url)
                    if original:
                        ranked_candidates.append(original)

                # Limit to max_candidates with mixed sampling
                if len(ranked_candidates) > max_candidates:
                    first_half_count = max_candidates // 2
                    first_half = ranked_candidates[:first_half_count]

                    remaining_needed = max_candidates - first_half_count
                    remaining_candidates = ranked_candidates[first_half_count:]

                    if remaining_needed > 0 and remaining_candidates:
                        random_sample = random.sample(remaining_candidates, min(remaining_needed, len(remaining_candidates)))
                        final_candidates = first_half + random_sample
                    else:
                        final_candidates = first_half
                else:
                    final_candidates = ranked_candidates

                # Check if we got results
                if len(final_candidates) > 0:
                    if attempt == 1:
                        retry_successful = True
                        logger.info(f"RETRY SUCCESSFUL: Got {len(final_candidates)} URLs on retry attempt with temperature={temperature}", extra=self._get_log_extra())
                    break
                else:
                    if attempt == 0:
                        retry_attempted = True
                        logger.warning(f"RETRY TRIGGERED: 0 URLs returned on first attempt, retrying with higher temperature...", extra=self._get_log_extra())
                        time.sleep(2)
                    else:
                        logger.error(f"RETRY FAILED: 0 URLs returned after retry attempt", extra=self._get_log_extra())

            # Create metadata
            rerank_metadata = {
                "total_input": original_candidate_count,
                "deduplicated_input": len(all_candidates),
                "duplicates_removed": duplicates_removed,
                "filtered_count": len(final_candidates),
                "discarded_count": len(all_candidates) - len(final_candidates),
                "method": method,
                "llm_ranked_count": len(ranked_urls),
                "retry_attempted": retry_attempted,
                "retry_successful": retry_successful
            }

            logger.info(f"Reranked {len(all_candidates)} candidates → {len(final_candidates)} filtered candidates using {method}", extra=self._get_log_extra())
            logger.info(f"Final Candidates URLs: {[c['url'] for c in final_candidates]} for queries: {list(results_by_query.keys())}", extra=self._get_log_extra())
            return final_candidates, rerank_metadata

        except Exception as e:
            logger.error(f"Reranking failed: {e}", extra=self._get_log_extra())
            # Fallback: flatten all results and return top candidates
            all_candidates = []
            for results in results_by_query.values():
                for result in results:
                    if not result.get("url", "").lower().endswith('.pdf'):
                        all_candidates.append(result)

            # Apply deduplication even in fallback
            original_fallback_count = len(all_candidates)
            all_candidates, fallback_duplicates_removed = self._remove_duplicates(all_candidates)

            fallback_candidates = all_candidates[:max_candidates]
            fallback_metadata = {
                "total_input": original_fallback_count,
                "deduplicated_input": len(all_candidates),
                "duplicates_removed": fallback_duplicates_removed,
                "filtered_count": len(fallback_candidates),
                "discarded_count": len(all_candidates) - len(fallback_candidates),
                "fallback": True,
                "error": str(e)
            }
            return fallback_candidates, fallback_metadata
    
    async def ai_search(self, query: str, reasoning: str = "") -> List[Dict[str, Any]]:
        """
        Execute AI Overview search via Scraping Dog and store result
        No URL crawling - AI overview is treated as synthesized text content only

        Args:
            query: Search query string
            reasoning: Why AI Overview is needed for this query

        Returns:
            Empty list (no URLs to crawl - AI overview is used directly as text)
        """
        try:
            # Import here to avoid circular imports
            from .api_crawlers import ScrapingDogClient

            # Get AI Overview via Scraping Dog with HTML format (async with rate limiting)
            scraping_dog = ScrapingDogClient()
            overview_result = await scraping_dog.get_ai_overview_async(query, return_html=True)

            if overview_result.get("success", False) and overview_result.get("ai_overview"):
                ai_content = {
                    "query": query,
                    "reasoning": reasoning,
                    "ai_overview": overview_result["ai_overview"],
                    "source": "scraping_dog_ai_overview"
                }
                self.ai_overviews.append(ai_content)
                logger.info(f"AI Overview collected for: '{query[:50]}...'", extra=self._get_log_extra())
                logger.info(f"AI Overview content: {overview_result['ai_overview'][:200]}...", extra=self._get_log_extra())
            else:
                logger.warning(f"AI Overview failed for '{query}': {overview_result.get('error', 'Unknown error')}", extra=self._get_log_extra())

            # Return empty list - AI overview is treated as text content, not URLs to crawl
            return []

        except Exception as e:
            logger.error(f"AI search failed for '{query}': {e}", extra=self._get_log_extra())
            # Return empty list on error
            return []
    
    def get_ai_overviews(self) -> List[Dict[str, Any]]:
        """Return collected AI Overview content"""
        return self.ai_overviews.copy()
    
    def clear_ai_overviews(self):
        """Clear stored AI Overview content"""
        self.ai_overviews.clear()

    def format_serp_results_as_text(self, results_by_query: Dict[str, List[Dict[str, Any]]]) -> str:
        """
        Format SERP results as Google-style text with markdown links

        Args:
            results_by_query: Dict mapping query strings to lists of results.
                             Each result should have 'url', 'title', and 'snippet' keys.

        Returns:
            Formatted string with query groups and markdown-linked results

        Example output:
            ### Query: site:example.com locations

            - [Page Title](https://example.com/page)
              Snippet text describing the page content...

            - [Another Page](https://example.com/another)
              Another snippet with context...
        """
        if not results_by_query:
            return ""

        output_lines = []

        for query, results in results_by_query.items():
            # Add query header
            output_lines.append(f"### Query: {query}\n")

            if not results:
                output_lines.append("No results found.\n")
                continue

            # Format each result
            for result in results:
                url = result.get('url', '')
                title = result.get('title', 'Untitled')
                snippet = result.get('snippet', '')
                rating = result.get('rating')
                rating_count = result.get('ratingCount')
                date = result.get('date')

                # Format as markdown link with snippet
                output_lines.append(f"- [{title}]({url})")
                if snippet:
                    output_lines.append(f"  {snippet}")

                # Add rating information if available
                if rating is not None:
                    rating_info = f"  ⭐ Rating: {rating}"
                    if rating_count:
                        rating_info += f" ({rating_count} reviews)"
                    output_lines.append(rating_info)

                # Add date if available
                if date:
                    output_lines.append(f"  📅 {date}")

                output_lines.append("")

            # Add spacing between query groups
            output_lines.append("")

        return "\n".join(output_lines)

    def close(self):
        """Close the connection - no-op for requests-based implementation"""
        pass

    def cleanup(self):
        """Clean up state to prevent memory leaks"""
        # Clear accumulated AI overviews
        self.clear_ai_overviews()