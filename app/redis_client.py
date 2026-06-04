import hashlib
import time
from typing import Optional
import redis
from app.config import settings
from app.logger import logger

# Initialize Redis Client
redis_client = redis.Redis(
    host=settings.REDIS_HOST,
    port=settings.REDIS_PORT,
    password=settings.REDIS_PASSWORD,
    decode_responses=True, # Automatically decode bytes to strings
    socket_timeout=5.0,
    socket_keepalive=True,
)

def get_redis_client() -> redis.Redis:
    return redis_client

def is_rate_limited(ip_address: str, limit: int = 15, window_sec: int = 60) -> bool:
    """
    Sliding window rate limiter using Redis sorted sets (zset).
    Limits requests per IP address over a sliding window.
    """
    now = time.time()
    key = f"rate_limit:{ip_address}"
    try:
        # Use Redis pipeline for atomic execution
        pipeline = redis_client.pipeline()
        
        # Remove timestamps older than the window
        pipeline.zremrangebyscore(key, 0, now - window_sec)
        # Add current timestamp to the zset (value and score are both now)
        pipeline.zadd(key, {str(now): now})
        # Get count of requests in the current window
        pipeline.zcard(key)
        # Set expiry to clean up inactive keys
        pipeline.expire(key, window_sec)
        
        # Execute pipeline
        _, _, count, _ = pipeline.execute()
        
        # If requests exceed limit, block access
        return count > limit
    except Exception as e:
        # Fail-open in case Redis is unavailable to prevent API outages
        logger.error("Redis rate-limiting error occurred", extra={"ip": ip_address, "error": str(e)})
        return False

def get_cache_key(text: str) -> str:
    """Generate MD5 hash of text to act as a unique cache key."""
    hasher = hashlib.md5(text.strip().encode("utf-8"))
    return f"cache:summary:{hasher.hexdigest()}"

def get_cached_summary(text: str) -> Optional[str]:
    """Retrieve summary from Redis cache if exists."""
    key = get_cache_key(text)
    try:
        return redis_client.get(key)
    except Exception as e:
        logger.error("Redis cache read error occurred", extra={"error": str(e)})
        return None

def set_cached_summary(text: str, summary: str, ttl_seconds: int = 3600) -> None:
    """Cache summary in Redis with a specified Time-to-Live."""
    key = get_cache_key(text)
    try:
        redis_client.setex(key, ttl_seconds, summary)
    except Exception as e:
        logger.error("Redis cache write error occurred", extra={"error": str(e)})
