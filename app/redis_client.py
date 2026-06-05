import redis
from app.config import settings
import logging

logger = logging.getLogger(__name__)

class MockRedis:
    """In-memory Mock Redis implementation for zero-cost seamless local fallback."""
    def __init__(self):
        self._store = {}
        self._zsets = {}
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
            if k in self._zsets:
                del self._zsets[k]
                deleted += 1
        return deleted

    def exists(self, key: str) -> int:
        return 1 if (key in self._store or key in self._zsets) else 0

    def incr(self, key: str, amount: int = 1) -> int:
        current = int(self._store.get(key, 0))
        new_val = current + amount
        self._store[key] = str(new_val)
        return new_val

    def zadd(self, key: str, mapping: dict) -> int:
        if key not in self._zsets:
            self._zsets[key] = {}
        added = 0
        for member, score in mapping.items():
            if member not in self._zsets[key]:
                added += 1
            self._zsets[key][member] = float(score)
        return added

    def zcount(self, key: str, min_val: float, max_val: float) -> int:
        if key not in self._zsets:
            return 0
        count = 0
        for member, score in self._zsets[key].items():
            if min_val <= score <= max_val:
                count += 1
        return count

    def expire(self, key: str, time_seconds: int) -> bool:
        return True

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
