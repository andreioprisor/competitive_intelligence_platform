"""
Content utilities for deduplication and spam removal in web crawling.

This module provides comprehensive tools for cleaning and deduplicating web content
while preserving valuable business information.
"""

import re
import logging
from typing import List, Dict, Any, Tuple, Optional

try:
    from simhash import Simhash
except ImportError:
    # Fallback if simhash is not available
    class Simhash:
        def __init__(self, text):
            self.value = hash(text) % (2**64)
        
        def distance(self, other):
            return bin(self.value ^ other.value).count('1')

logger = logging.getLogger(__name__)

class ContentUtils:
    """Utility class for content deduplication and spam removal"""
    
    def __init__(self):
        # Enhanced spam keywords - aggressive but business-aware
        self.spam_keywords = [
            # Cookie/Privacy/Legal
            'cookie', 'cookies', 'privacy policy', 'terms of service', 'terms and conditions',
            'gdpr', 'data protection', 'consent', 'storage duration', 'cloudflare', 'by continuing to use',
            'accept cookies', 'cookie preferences', 'cookie settings', 'manage cookies', 'consent selection',
            'necessary cookies', 'performance cookies', 'functional cookies', 'targeting cookies',
            'analytics cookies', 'third-party cookies', 'cookie consent', 'cookie notice', 'maximum storage duration',
            'we use cookies', 'this site uses cookies', 'this website uses cookies', 'html local storage',
            'data processing', 'legal basis', 'legitimate interest', 'opt-out', 'http cookie',
            'do not sell my personal information', 'california privacy rights', 'pixel tracker',
            'privacy notice', 'privacy statement', 'data collection', 'tracking', 'ccpa',
            'personal data', 'cookies policy', 'cookie banner', 'cookie popup',
            
            # Tracking/Analytics providers (from result_5.md analysis)
            'airtable session', 'calendly', 'hubspot', 'typeform', 'hotjar', 'rudderstack',
            'google analytics', 'facebook pixel', 'linkedin insight', 'tiktok pixel',
            'youtube tracking', 'visitor info', 'session id', 'tracking pixel',
            'advertisement efficiency', 'marketing platform', 'user behaviour',
            'statistical purposes', 'targeted ads', 'advertisement products',
            
            # Navigation/UI elements
            'breadcrumb', 'main menu', 'footer', 'sidebar', 'navigation', 'skip to content',
            'search form', 'login form', 'sign up', 'newsletter', 'subscribe',
            'back to top', 'print page', 'share this', 'social media',
            
            # Generic spam patterns
            'lorem ipsum', 'placeholder text', 'test content', 'dummy text',
            'example text', 'sample content', 'copyright notice', '© 2024', '© 2023',
            'all rights reserved', 'powered by', 'developed by', 'designed by',
            
            # Form/Survey elements  
            'required field', 'optional field', 'form validation', 'captcha',
            'please fill', 'enter your', 'submit form', 'form error',
            
            # Empty/Low value content
            'no content', 'content not available', 'coming soon', 'under construction',
            'page not found', '404 error', 'access denied', 'permission denied'
        ]
        
        # Business value keywords to preserve - critical content indicators
        self.preserve_keywords = [
            # Business metrics
            'revenue', 'profit', 'sales', 'growth', 'market share', 'customers',
            'employees', 'staff', 'headcount', 'workforce', 'team size',
            'funding', 'investment', 'valuation', 'ipo', 'acquisition',
            'merger', 'partnership', 'collaboration', 'contract',
            
            # Financial data
            'quarterly', 'annual', 'earnings', 'financial', 'budget',
            'cost', 'expense', 'margin', 'ebitda', 'operating income',
            'net income', 'cash flow', 'balance sheet', 'assets',
            
            # Company info
            'headquarters', 'office', 'location', 'address', 'founded',
            'ceo', 'founder', 'executive', 'leadership', 'management',
            'board', 'director', 'president', 'cto', 'cfo',
            
            # Business operations
            'product', 'service', 'offering', 'solution', 'technology',
            'platform', 'software', 'application', 'system', 'tool',
            'feature', 'capability', 'benefit', 'advantage', 'innovation',
            
            # Industry/Market
            'industry', 'market', 'sector', 'vertical', 'niche',
            'competition', 'competitor', 'client', 'customer', 'user',
            'target market', 'audience', 'demographic', 'segment'
        ]
        
        # DOM selectors for crawl-time spam removal
        self.spam_selectors = [
            # Cookie/Privacy banners
            '[id*="cookie"]', '[class*="cookie"]', '[data-testid*="cookie"]',
            '[id*="consent"]', '[class*="consent"]', '[data-testid*="consent"]',
            '[id*="privacy"]', '[class*="privacy"]', '[data-testid*="privacy"]',
            '[id*="gdpr"]', '[class*="gdpr"]', '[data-testid*="gdpr"]',
            
            # Navigation elements
            'nav', 'header', 'footer', 'aside', '.sidebar', '#sidebar',
            '.navigation', '#navigation', '.menu', '#menu', '.nav',
            '.breadcrumb', '.breadcrumbs', '.pagination',
            
            # Ads and tracking
            '[id*="ad"]', '[class*="ad"]', '[id*="ads"]', '[class*="ads"]',
            '[id*="tracking"]', '[class*="tracking"]', '[id*="analytics"]',
            '[class*="analytics"]', '.advertisement', '.sponsored',
            
            # Social/Share widgets
            '.social', '.share', '.follow', '.like', '.tweet', '.facebook',
            '.linkedin', '.youtube', '.instagram', '.twitter',
            
            # Forms (if not business-critical)
            '.newsletter', '.subscribe', '.signup', '.login-form',
            '.contact-form', '.search-form', '.filter-form'
        ]

    def deduplicate_paragraphs(
        self, 
        content: str, 
        similarity_threshold: float = 0.85,
        min_paragraph_length: int = 50
    ) -> str:
        """
        Remove duplicate paragraphs within a single page using SimHash.
        
        Args:
            content: The markdown content to deduplicate
            similarity_threshold: Similarity threshold (0.85 = 85% similar)
            min_paragraph_length: Minimum paragraph length to consider
            
        Returns:
            Deduplicated content with near-duplicates removed
        """
        if not content or not content.strip():
            return ""
        
        # Split content into paragraphs
        paragraphs = [p.strip() for p in content.split('\n\n') if p.strip()]
        
        if len(paragraphs) <= 1:
            return content
        
        # Track seen hashes and deduplicated paragraphs
        seen_hashes = []  # List of (hash, paragraph) tuples
        deduplicated = []
        duplicates_removed = 0
        
        for paragraph in paragraphs:
            # Skip very short paragraphs
            if len(paragraph) < min_paragraph_length:
                deduplicated.append(paragraph)
                continue
            
            # Normalize paragraph for hashing
            normalized = self._normalize_text(paragraph)
            
            # Generate SimHash
            paragraph_hash = Simhash(normalized)
            
            # Check for duplicates
            is_duplicate = False
            for existing_hash, existing_para in seen_hashes:
                hamming_distance = paragraph_hash.distance(existing_hash)
                # Calculate similarity (lower hamming distance = higher similarity)
                similarity = 1 - (hamming_distance / 64.0)  # 64-bit hash
                
                if similarity >= similarity_threshold:
                    is_duplicate = True
                    # Keep the longer version
                    if len(paragraph) > len(existing_para):
                        # Replace with longer version
                        for i, dedup_para in enumerate(deduplicated):
                            if dedup_para == existing_para:
                                deduplicated[i] = paragraph
                                # Update in seen_hashes
                                for j, (h, p) in enumerate(seen_hashes):
                                    if p == existing_para:
                                        seen_hashes[j] = (existing_hash, paragraph)
                                        break
                                break
                    duplicates_removed += 1
                    break
            
            if not is_duplicate:
                seen_hashes.append((paragraph_hash, paragraph))
                deduplicated.append(paragraph)
        
        result = '\n\n'.join(deduplicated)
        
        if duplicates_removed > 0:
            logger.info(f"Deduplicated content: removed {duplicates_removed} similar paragraphs")
        
        return result

    def aggregate_and_dedup(
        self, 
        pages: List[Dict[str, Any]], 
        similarity_threshold: float = 0.85,
        content_key: str = 'fit_markdown'
    ) -> List[Dict[str, Any]]:
        """
        Remove duplicate paragraphs across multiple pages.
        Each paragraph appears only once across all pages.
        
        Args:
            pages: List of page dictionaries with content
            similarity_threshold: Threshold for paragraph similarity
            content_key: Key containing the content to deduplicate
            
        Returns:
            List of pages with cross-page duplicate paragraphs removed
        """
        if not pages or len(pages) <= 1:
            return pages
        
        # Track all unique paragraphs across all pages
        global_paragraph_hashes = []  # List of (hash, paragraph, source_url) tuples
        
        # Process each page and update with deduplicated content
        updated_pages = []
        total_paragraphs_removed = 0
        
        for page in pages:
            content = page.get(content_key, "")
            if not content or not content.strip():
                updated_pages.append(page)
                continue
            
            # Split into paragraphs
            paragraphs = [p.strip() for p in content.split('\n\n') if p.strip()]
            deduplicated_paragraphs = []
            local_removed = 0
            
            for paragraph in paragraphs:
                # Skip very short paragraphs
                # if len(paragraph) < 50:
                #     deduplicated_paragraphs.append(paragraph)
                #     continue
                
                # Normalize and hash
                normalized = self._normalize_text(paragraph)
                paragraph_hash = Simhash(normalized)
                
                # Check against all previously seen paragraphs
                is_duplicate = False
                for existing_hash, existing_para, source_url in global_paragraph_hashes:
                    hamming_distance = paragraph_hash.distance(existing_hash)
                    similarity = 1 - (hamming_distance / 64.0)
                    
                    if similarity >= similarity_threshold:
                        is_duplicate = True
                        local_removed += 1
                        logger.debug(f"Removed duplicate paragraph from {page.get('url')} (originally from {source_url})")
                        break
                
                if not is_duplicate:
                    # Add to global tracking and keep in page
                    global_paragraph_hashes.append((paragraph_hash, paragraph, page.get('url', 'unknown')))
                    deduplicated_paragraphs.append(paragraph)
            
            # Update page with deduplicated content
            updated_page = page.copy()
            updated_page[content_key] = '\n\n'.join(deduplicated_paragraphs)
            updated_pages.append(updated_page)
            
            if local_removed > 0:
                total_paragraphs_removed += local_removed
                logger.info(f"Removed {local_removed} duplicate paragraphs from {page.get('url')}")
        
        if total_paragraphs_removed > 0:
            logger.info(f"Cross-page deduplication: removed {total_paragraphs_removed} duplicate paragraphs total")
        
        return updated_pages

    def spam_removal(
        self, 
        content: str, 
        aggressive: bool = True
    ) -> str:
        """
        Remove spam content using advanced pattern detection.
        
        Args:
            content: Content to clean
            aggressive: Enable aggressive spam removal
            
        Returns:
            Cleaned content with spam removed
        """
        if not content or not content.strip():
            return ""
        
        cleaned = content
        
        # Step 1: Remove markdown links but preserve text
        cleaned = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', cleaned)
        
        # Step 2: Remove bare URLs
        cleaned = re.sub(r'https?://[^\s]+', '', cleaned)
        
        # Step 3: Remove image references
        cleaned = re.sub(r'!\[([^\]]*)\]\([^\)]+\)', '', cleaned)
        
        # Step 4: Line-by-line spam filtering
        lines = cleaned.split('\n')
        filtered_lines = []
        
        spam_lines_removed = 0
        for line in lines:
            line = line.strip()
            
            if not line:
                continue
            
            # Check for spam patterns
            if self._is_spam_line(line, aggressive):
                continue
            
            # Check for repetitive patterns
            if self._is_repetitive_content(line):
                continue
            
            filtered_lines.append(line)
        
        # Step 5: Remove consecutive duplicate lines
        deduplicated_lines = []
        prev_line = None
        
        for line in filtered_lines:
            if line != prev_line:
                deduplicated_lines.append(line)
            prev_line = line
        
        # Step 6: Reconstruct paragraphs
        if not deduplicated_lines:
            return ""
        
        paragraphs = self._reconstruct_paragraphs(deduplicated_lines)
        result = '\n\n'.join(paragraphs)
        
        # Step 7: Final cleanup
        result = re.sub(r'\n{3,}', '\n\n', result)
        result = re.sub(r' {2,}', ' ', result)
        
        # Log cleaning statistics
        original_length = len(content)
        cleaned_length = len(result)
        if original_length > 0:
            reduction_pct = (1 - cleaned_length/original_length) * 100
            logger.info(f"Spam removal: {original_length} -> {cleaned_length} chars ({reduction_pct:.1f}% reduction)")
        
        return result.strip()

    def _normalize_text(self, text: str) -> str:
        """Normalize text for comparison"""
        # Convert to lowercase
        text = text.lower()
        
        # Remove extra whitespace
        text = re.sub(r'\s+', ' ', text)
        
        # Remove punctuation (keep alphanumeric and spaces)
        text = re.sub(r'[^\w\s]', '', text)
        
        return text.strip()


    def _should_preserve_line(self, line: str) -> bool:
        """Check if a line contains valuable business content"""
        line_lower = line.lower()
        
        # Preserve lines with business value keywords
        if any(keyword in line_lower for keyword in self.preserve_keywords):
            return True
        
        # Preserve lines with financial data patterns
        if re.search(r'\$[\d,]+|\d+%|\d+\s*(million|billion|thousand)', line_lower):
            return True
        
        # Preserve substantial content (likely to be valuable)
        if len(line) > 100 and line.count(' ') > 10:
            return True
        
        return False

    def _is_spam_line(self, line: str, aggressive: bool = True) -> bool:
        """Check if a line is spam content"""
        line_lower = line.lower()
        
        # Check spam keywords
        spam_matches = sum(1 for keyword in self.spam_keywords if keyword in line_lower)
        
        if aggressive:
            # Aggressive: any spam keyword triggers removal
            if spam_matches > 0:
                return True
        else:
            # Conservative: multiple spam keywords needed
            if spam_matches > 1:
                return True
        
        # Pattern-based spam detection
        spam_patterns = [
            r'click here', r'learn more', r'read more', r'see more',
            r'accept all', r'allow all', r'deny all', r'customize',
            r'©\s*\d{4}', r'all rights reserved', r'powered by',
            r'continue to.*site', r'this website uses',
            r'\[\s*x\s*\]', r'\[\s*\d+\s*\]',  # Close buttons, counters
        ]
        
        if any(re.search(pattern, line_lower) for pattern in spam_patterns):
            return True
        
        # Check for provider lists (like in result_5.md)
        if re.search(r'learn more about this provider|pending|\d+learn more', line_lower):
            return True
        
        return False

    def _is_repetitive_content(self, line: str) -> bool:
        """Check if content is repetitive/low value"""
        # Very short lines
        if len(line) < 10:
            return True
        
        # Lines with mostly punctuation
        if len(re.sub(r'[^\w\s]', '', line)) < len(line) * 0.5:
            return True
        
        # Repetitive characters
        if re.search(r'(.)\1{5,}', line):  # Same char repeated 6+ times
            return True
        
        return False

    def _reconstruct_paragraphs(self, lines: List[str]) -> List[str]:
        """Reconstruct meaningful paragraphs from filtered lines"""
        if not lines:
            return []
        
        paragraphs = []
        current_paragraph = []
        
        for line in lines:
            # Check if line should start new paragraph
            if (line.endswith('.') or line.endswith('!') or line.endswith('?') or 
                line.startswith('#') or len(line) > 150):
                # Complete current paragraph
                if current_paragraph:
                    paragraphs.append(' '.join(current_paragraph))
                    current_paragraph = []
                # Add as standalone paragraph
                paragraphs.append(line)
            else:
                current_paragraph.append(line)
        
        # Add remaining content
        if current_paragraph:
            paragraphs.append(' '.join(current_paragraph))
        
        return [p for p in paragraphs if p.strip()]


# Global instance for easy access
content_utils = ContentUtils()

# Convenience functions
def deduplicate_paragraphs(content: str, **kwargs) -> str:
    """Convenience function for paragraph deduplication"""
    return content_utils.deduplicate_paragraphs(content, **kwargs)

def aggregate_and_dedup(pages: List[Dict[str, Any]], **kwargs) -> List[Dict[str, Any]]:
    """Convenience function for cross-page deduplication"""
    return content_utils.aggregate_and_dedup(pages, **kwargs)

def spam_removal(content: str, **kwargs) -> str:
    """Convenience function for spam removal"""
    return content_utils.spam_removal(content, **kwargs)