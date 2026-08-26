import time
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)


class StreamingFeaturePipeline:
    """
    Staff-Level ML Architecture: Lambda Architecture Speed Layer.

    The Lambda Architecture has 3 layers:
        1. Batch Layer (S3/DynamoDB): Computes historical features nightly
           (e.g., 30-day average spend by card). High accuracy, high latency.

        2. Speed Layer (THIS CLASS): Processes the Kafka event stream in
           real-time, maintaining a rolling window of features for the last
           1h/24h. Low latency (<1s), approximate accuracy.

        3. Serving Layer (OnlineFeatureStore): Merges batch + speed layer
           features and serves them to the fraud model in <5ms.

    This is architecturally identical to how Uber Michelangelo and LinkedIn
    Feathr handle real-time ML feature serving.
    """

    def __init__(self, feature_store):
        """
        Args:
            feature_store: OnlineFeatureStore instance to write computed features into
        """
        self.feature_store = feature_store
        self._transaction_buffer: Dict[str, list] = {}  # card_id -> list of recent txns
        self._running = False
        logger.info("StreamingFeaturePipeline initialized (Lambda Architecture Speed Layer).")

    def process_event(self, event: Dict[str, Any]):
        """
        Processes a single Razorpay/payment webhook event.
        Updates the rolling transaction buffer and recomputes features.

        Expected event schema:
        {
            'payment_id': str,
            'card_id': str,
            'merchant_id': str,
            'amount': float,
            'currency': str,
            'country': str,
            'timestamp': float,  # Unix timestamp
            'cross_border': bool
        }
        """
        card_id = event.get('card_id')
        if not card_id:
            logger.warning(f"Event missing card_id: {event.get('payment_id', 'unknown')}")
            return

        # Append to rolling buffer, keeping only the last 7 days
        if card_id not in self._transaction_buffer:
            self._transaction_buffer[card_id] = []

        self._transaction_buffer[card_id].append(event)

        # Prune events older than 7 days to bound memory usage
        cutoff = time.time() - 7 * 86400
        self._transaction_buffer[card_id] = [
            t for t in self._transaction_buffer[card_id]
            if t.get('timestamp', 0) > cutoff
        ]

        # Recompute features and push to the feature store
        features = self.feature_store.compute_velocity_features(
            card_id, self._transaction_buffer[card_id]
        )
        self.feature_store.put_features(card_id, features, ttl=300)
        logger.debug(f"Features updated for card {card_id[-4:]}: txn_1h={features['txn_count_1h']}")

    def start_worker(self, kafka_consumer_fn):
        """
        Long-running worker that consumes from the Kafka payment topic
        and processes each event through the speed layer.

        Args:
            kafka_consumer_fn: A generator/iterable yielding payment event dicts
        """
        self._running = True
        logger.info("StreamingFeaturePipeline worker started. Consuming from Kafka...")

        try:
            for event in kafka_consumer_fn():
                if not self._running:
                    break
                try:
                    self.process_event(event)
                except Exception as e:
                    logger.error(f"Failed to process event: {e}")
        finally:
            logger.info("StreamingFeaturePipeline worker stopped.")

    def stop(self):
        self._running = False
