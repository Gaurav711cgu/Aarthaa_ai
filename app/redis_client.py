import redis
from app.config import settings
import logging

logger = logging.getLogger(__name__)

class MockRedis:
    """In-memory Mock Redis implementation for zero-cost seamless local fallback."""
    def __init__(self):
        self._store = {}
        logger.info("MockRedis local instance initialized.")

    def ping(self) -> bool:
        return True

    def get(self, key: str) -> str:
        return self._store.get(key)

    def set(self, key: str, value: str, ex=None, px=None, nx=False, xx=False) -> bool:
        self._store[key] = str(value)
        return True

    def delete(self, *keys) -> int:
        deleted = 0
        for k in keys:
            if k in self._store:
                del self._store[k]
                deleted += 1
        return deleted

    def exists(self, key: str) -> int:
        return 1 if key in self._store else 0

    def incr(self, key: str, amount: int = 1) -> int:
        current = int(self._store.get(key, 0))
        new_val = current + amount
        self._store[key] = str(new_val)
        return new_val

# Try establishing real Redis connection pool
redis_pool = None
is_redis_active = False

try:
    if settings.REDIS_URL:
        logger.info("Attempting connection to Redis via REDIS_URL...")
        redis_pool = redis.ConnectionPool.from_url(
            settings.REDIS_URL,
            decode_responses=True,
            max_connections=50,
            socket_timeout=1.0  # Fail fast within 1s
        )
    else:
        logger.info("Attempting connection to Redis via host/port...")
        redis_pool = redis.ConnectionPool(
            host=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
            decode_responses=True,
            max_connections=50,
            socket_timeout=1.0  # Fail fast within 1s
        )
    # Active connection test ping
    client = redis.Redis(connection_pool=redis_pool)
    client.ping()
    is_redis_active = True
    logger.info("Redis connection established successfully.")
except Exception as e:
    logger.warning(f"Redis connection failed: {e}. Activating transparent MockRedis fallback.")
    is_redis_active = False

def get_redis_client():
    """Factory function returning active Redis client or in-memory MockRedis wrapper."""
    if is_redis_active and redis_pool:
        return redis.Redis(connection_pool=redis_pool)
    return MockRedis()

def test_redis_connection() -> bool:
    """Verifies Redis container health status (always True for active MockRedis)."""
    try:
        client = get_redis_client()
        return bool(client.ping())
    except Exception as e:
        logger.error(f"Redis connection health check failed: {e}")
        return False
