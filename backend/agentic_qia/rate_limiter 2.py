"""
Redis-based distributed rate limiter using sliding window algorithm.

Enforces TPM (Tokens Per Minute) limits across distributed workers.
Uses Redis sorted sets for simple, atomic sliding window counting.
"""
import redis
import time
import asyncio
import logging
import uuid
from typing import Optional

logger = logging.getLogger(__name__)


class RedisRateLimiter:
    """
    Distributed rate limiter using Redis sorted sets with sliding window.

    Much simpler than token bucket - uses sorted set where:
    - Score = timestamp
    - Member = unique request ID
    - Window = last 60 seconds

    All operations are atomic without needing transactions.
    """

    def __init__(self, redis_client: redis.Redis, bucket_key: str, tpm_limit: int):
        """
        Initialize rate limiter.

        Args:
            redis_client: Redis connection
            bucket_key: Redis key for this rate limiter
            tpm_limit: Tokens per minute limit (e.g., 1,000,000 for Gemini)
        """
        if tpm_limit <= 0:
            raise ValueError("TPM limit must be positive.")

        self.redis = redis_client
        self.bucket_key = bucket_key
        self.limit = tpm_limit
        self.window_seconds = 60  # 1 minute window

        logger.info(f"RedisRateLimiter initialized: key={bucket_key}, limit={tpm_limit:,} TPM")

    def _cleanup_expired(self):
        """Remove entries older than the sliding window."""
        now = time.time()
        window_start = now - self.window_seconds

        try:
            # Remove all entries with score < window_start
            removed = self.redis.zremrangebyscore(self.bucket_key, 0, window_start)
            if removed > 0:
                logger.debug(f"Rate limiter: Cleaned up {removed} expired entries")
        except Exception as e:
            logger.error(f"Failed to cleanup expired entries: {e}")

    def get_current_usage(self) -> int:
        """
        Get current token usage in the sliding window.

        Returns:
            Number of tokens used in last 60 seconds
        """
        try:
            self._cleanup_expired()

            now = time.time()
            window_start = now - self.window_seconds

            # Count all entries in the current window
            # Note: We store token counts in member names like "uuid:count"
            members = self.redis.zrangebyscore(self.bucket_key, window_start, now)

            total_tokens = 0
            for member in members:
                # Extract token count from member name
                try:
                    # Member format: "uuid:token_count"
                    if isinstance(member, bytes):
                        member = member.decode('utf-8')
                    _, token_count_str = member.rsplit(':', 1)
                    total_tokens += int(token_count_str)
                except (ValueError, AttributeError):
                    # Skip malformed entries
                    continue

            return total_tokens
        except Exception as e:
            logger.error(f"Failed to get current usage: {e}")
            return 0
    # TODO TEST THIS LOGIC PROPERLY
    async def reserve_tokens(self, token_count: int, max_wait: float = 60.0, request_id: Optional[str] = None) -> bool:
        """
        Reserve tokens for an upcoming LLM call (async with timeout).

        Args:
            token_count: Number of tokens to reserve
            max_wait: Maximum time to wait in seconds
            request_id: Optional unique ID for this request

        Returns:
            True if tokens reserved, False if timeout
        """
        if token_count > self.limit:
            logger.warning(f"Rate limiter: Requested tokens ({token_count:,}) exceeds limit ({self.limit:,}) - allowing anyway")
            # Allow it anyway - single request larger than limit
            return True

        if request_id is None:
            request_id = str(uuid.uuid4())

        start_time = time.time()
        retry_count = 0

        logger.info(f"Rate limiter: Starting token reservation (need: {token_count:,}, max_wait: {max_wait:.1f}s, request_id: {request_id[:8]}...)")

        while True:
            # Check timeout
            elapsed = time.time() - start_time
            if elapsed > max_wait:
                current_usage = self.get_current_usage()
                available = self.limit - current_usage
                logger.error(
                    f"Rate limiter: TIMEOUT after {elapsed:.1f}s waiting for {token_count:,} tokens "
                    f"(retries: {retry_count}, final_usage: {current_usage:,}/{self.limit:,}, "
                    f"available: {available:,}, request_id: {request_id[:8]}...)"
                )
                return False

            try:
                # Cleanup and check current usage
                current_usage = self.get_current_usage()
                available = self.limit - current_usage

                if available >= token_count:
                    # We have space - reserve the tokens
                    now = time.time()
                    member_name = f"{request_id}:{token_count}"

                    # Add to sorted set with current timestamp as score
                    self.redis.zadd(self.bucket_key, {member_name: now})

                    # Set expiration on the key to prevent memory leak
                    self.redis.expire(self.bucket_key, self.window_seconds * 2)

                    total_wait = time.time() - start_time
                    logger.info(
                        f"Rate limiter: ✅ Reserved {token_count:,} tokens after {total_wait:.2f}s "
                        f"(retries: {retry_count}, usage: {current_usage:,}/{self.limit:,}, "
                        f"available: {available:,}, request_id: {request_id[:8]}...)"
                    )
                    return True
                else:
                    # Not enough space - wait
                    retry_count += 1
                    wait_time = min(5.0, 0.5 * retry_count)  # Exponential backoff capped at 5s

                    # Log every retry with detailed stats
                    logger.info(
                        f"Rate limiter: Waiting (retry {retry_count}, elapsed: {elapsed:.1f}s, "
                        f"need: {token_count:,}, available: {available:,}, usage: {current_usage:,}/{self.limit:,}, "
                        f"sleeping: {wait_time:.1f}s, request_id: {request_id[:8]}...)"
                    )

                    await asyncio.sleep(wait_time)

                    logger.info(f"Rate limiter: Woke from {wait_time:.1f}s sleep, retrying (retry {retry_count + 1})")

            except Exception as e:
                logger.error(f"Rate limiter error during reserve (retry {retry_count}, elapsed: {elapsed:.1f}s): {e}", exc_info=True)
                # On error, allow request to proceed
                return True

    def check_available(self, token_count: int) -> tuple[bool, float]:
        """
        Check if tokens are available without reserving them.

        Args:
            token_count: Number of tokens needed

        Returns:
            Tuple of (available: bool, wait_time: float)
        """
        try:
            current_usage = self.get_current_usage()
            available = self.limit - current_usage

            if available >= token_count:
                return (True, 0.0)
            else:
                # Estimate wait time (assumes even distribution)
                tokens_needed = token_count - available
                # Tokens refill at rate of limit/60 per second
                wait_time = (tokens_needed / self.limit) * 60
                return (False, wait_time)
        except Exception as e:
            logger.error(f"Failed to check availability: {e}")
            return (True, 0.0)


def create_gemini_rate_limiter(bucket_key: str = "gemini_flash_tpm") -> Optional[RedisRateLimiter]:
    """
    Factory function to create a rate limiter for Gemini Flash.

    Uses existing Redis config from config_leadora.redis_config.

    Args:
        bucket_key: Redis key for rate limiter

    Returns:
        RedisRateLimiter instance, or None if Redis unavailable
    """
    try:
        # Import existing Redis config
        from leadora.config_leadora.redis_config import get_app_redis_conn

        redis_client = get_app_redis_conn()

        # Test connection
        redis_client.ping()
        
        # Gemini Flash: 1M tokens per minute
        # https://ai.google.dev/pricing
        TPM_LIMIT = 3_000_000

        rate_limiter = RedisRateLimiter(
            redis_client=redis_client,
            bucket_key=bucket_key,
            tpm_limit=TPM_LIMIT
        )

        logger.info(f"✅ Gemini rate limiter created: {TPM_LIMIT:,} TPM")
        return rate_limiter

    except Exception as e:
        logger.error(f"❌ Failed to create rate limiter (will run without rate limiting): {e}")
        return None
