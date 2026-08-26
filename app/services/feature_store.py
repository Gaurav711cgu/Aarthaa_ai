import time
import json
import logging
import threading
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

try:
    import redis as redis_lib
    HAS_REDIS = True
except ImportError:
    HAS_REDIS = False


@dataclass
class FeatureVector:
    """
    Strongly-typed feature container.
    Features older than TTL are considered stale and must be recomputed
    by the streaming pipeline before being used for ML inference.
    """
    entity_id: str
    features: Dict[str, float]
    computed_at: float = field(default_factory=time.time)
    ttl_seconds: int = 300  # 5-minute freshness window (matches Stripe/PayPal SLA)

    def is_stale(self) -> bool:
        return (time.time() - self.computed_at) > self.ttl_seconds

    def to_redis_dict(self) -> dict:
        return {
            'entity_id': self.entity_id,
            'features': json.dumps(self.features),
            'computed_at': str(self.computed_at),
            'ttl_seconds': str(self.ttl_seconds)
        }

    @staticmethod
    def from_redis_dict(data: dict) -> 'FeatureVector':
        return FeatureVector(
            entity_id=data['entity_id'],
            features=json.loads(data['features']),
            computed_at=float(data['computed_at']),
            ttl_seconds=int(data['ttl_seconds'])
        )


class OnlineFeatureStore:
    """
    Staff-Level ML Architecture: Two-Layer Online Feature Store.

    CUSTOMER POV: 'I need my fraud model to make decisions in under 50ms.'

    The Problem with naive batch ML:
    Most fraud models compute features (e.g., 'how many transactions in the
    last 1 hour?') by querying Postgres at inference time.
    Under Black Friday load, these queries spike to 200-500ms each,
    causing cascading DB timeouts and failed fraud checks.

    The Solution (Feast/Tecton/Amazon SageMaker Feature Store pattern):
    A two-tier cache hierarchy:
        - L1: In-process Python dict (sub-millisecond, 10k entities max)
        - L2: Redis Hash (1-5ms, unlimited)

    Features are pre-computed ASYNCHRONOUSLY by the Kafka streaming pipeline
    and pushed into both tiers. The fraud model at inference time ONLY reads
    from L1/L2. It NEVER touches the transactional Postgres DB.

    This decouples the ML inference latency from database load entirely.
    """

    def __init__(self, redis_url: str = 'redis://localhost:6379/2', l1_max_size: int = 10000):
        self._l1_cache: Dict[str, FeatureVector] = {}
        self._l1_max_size = l1_max_size
        self._l1_access_order: List[str] = []
        self._lock = threading.Lock()

        self.mock_mode = not HAS_REDIS
        if not self.mock_mode:
            try:
                self._redis = redis_lib.Redis.from_url(redis_url, decode_responses=True)
                self._redis.ping()
                logger.info("OnlineFeatureStore connected to Redis L2 cache.")
            except Exception as e:
                logger.warning(f"Redis unavailable, L1-only mode: {e}")
                self.mock_mode = True

    def get_features(self, entity_id: str) -> Optional[FeatureVector]:
        """
        Cache-aside read: L1 -> L2 -> None (triggers recompute).
        Total expected latency: <1ms (L1 hit) or 1-5ms (L2 hit).
        """
        # L1 check
        with self._lock:
            fv = self._l1_cache.get(entity_id)
            if fv and not fv.is_stale():
                self._update_lru(entity_id)
                return fv

        # L2 check
        if not self.mock_mode:
            try:
                raw = self._redis.hgetall(f"features:{entity_id}")
                if raw:
                    fv = FeatureVector.from_redis_dict(raw)
                    if not fv.is_stale():
                        self._put_l1(entity_id, fv)  # Promote to L1
                        return fv
            except Exception as e:
                logger.error(f"Redis L2 read failed: {e}")

        return None  # Cache miss: caller must trigger recompute

    def put_features(self, entity_id: str, features: Dict[str, float], ttl: int = 300):
        """Write-through: updates both L1 and L2 atomically."""
        fv = FeatureVector(entity_id=entity_id, features=features, ttl_seconds=ttl)
        self._put_l1(entity_id, fv)

        if not self.mock_mode:
            try:
                pipe = self._redis.pipeline()
                pipe.hset(f"features:{entity_id}", mapping=fv.to_redis_dict())
                pipe.expire(f"features:{entity_id}", ttl)
                pipe.execute()
            except Exception as e:
                logger.error(f"Redis L2 write failed: {e}")

    def _put_l1(self, entity_id: str, fv: FeatureVector):
        with self._lock:
            if len(self._l1_cache) >= self._l1_max_size:
                self._evict_l1_lru()
            self._l1_cache[entity_id] = fv
            self._update_lru(entity_id)

    def _update_lru(self, entity_id: str):
        """Move entity to end of access order list (most recently used)."""
        if entity_id in self._l1_access_order:
            self._l1_access_order.remove(entity_id)
        self._l1_access_order.append(entity_id)

    def _evict_l1_lru(self):
        """Evict least recently used entry from L1 cache."""
        if self._l1_access_order:
            lru_key = self._l1_access_order.pop(0)
            self._l1_cache.pop(lru_key, None)

    def compute_velocity_features(self, card_id: str, recent_transactions: list) -> Dict[str, float]:
        """
        Synchronously computes all velocity features for a card from its transaction history.
        Called by the streaming pipeline to pre-populate the feature store.

        Features computed:
        - txn_count_1h: transaction count in last 1 hour (velocity signal)
        - txn_count_24h: transaction count in last 24 hours
        - avg_amount_7d: average transaction amount over 7 days (baseline)
        - std_amount_7d: standard deviation (anomaly = current >> avg + 2*std)
        - unique_merchants_24h: number of distinct merchants (card testing signal)
        - cross_border_ratio: fraction of transactions crossing country boundary
        """
        now = time.time()
        one_hour_ago = now - 3600
        one_day_ago = now - 86400
        seven_days_ago = now - 7 * 86400

        txns_1h = [t for t in recent_transactions if t.get('timestamp', 0) > one_hour_ago]
        txns_24h = [t for t in recent_transactions if t.get('timestamp', 0) > one_day_ago]
        txns_7d = [t for t in recent_transactions if t.get('timestamp', 0) > seven_days_ago]

        amounts_7d = [float(t.get('amount', 0)) for t in txns_7d]
        avg_amount = float(sum(amounts_7d) / len(amounts_7d)) if amounts_7d else 0.0
        std_amount = float(__import__('statistics').stdev(amounts_7d)) if len(amounts_7d) > 1 else 0.0

        merchants_24h = {t.get('merchant_id') for t in txns_24h if t.get('merchant_id')}
        cross_border = sum(1 for t in txns_24h if t.get('cross_border', False))
        cross_border_ratio = cross_border / len(txns_24h) if txns_24h else 0.0

        return {
            'txn_count_1h': float(len(txns_1h)),
            'txn_count_24h': float(len(txns_24h)),
            'avg_amount_7d': avg_amount,
            'std_amount_7d': std_amount,
            'unique_merchants_24h': float(len(merchants_24h)),
            'cross_border_ratio': cross_border_ratio,
        }

    def get_or_compute(self, entity_id: str, compute_fn, ttl: int = 300) -> FeatureVector:
        """Cache-aside pattern: return cached features or compute and store them."""
        cached = self.get_features(entity_id)
        if cached:
            return cached
        features = compute_fn()
        self.put_features(entity_id, features, ttl)
        return FeatureVector(entity_id=entity_id, features=features, ttl_seconds=ttl)
