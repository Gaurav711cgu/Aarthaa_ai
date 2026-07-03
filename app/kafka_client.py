import os
from confluent_kafka import Producer
from typing import Optional
from app.config import settings
import logging

logger = logging.getLogger(__name__)

# Mock is only enabled if explicitly set via environment variable (useful for unit tests)
MOCK_FORCED = os.getenv("ARTHA_KAFKA_MOCK", "false").lower() == "true"

class MockKafkaProducer:
    """In-memory Mock Kafka Producer for unit tests only."""
    def __init__(self):
        logger.info("MockKafkaProducer local instance initialized (test mode).")
        self._backlog = []

    def produce(self, topic: str, value: str, key: Optional[str] = None, callback=None, **kwargs):
        """Simulates message production to a topic with callback handler support."""
        event = {"topic": topic, "key": key, "value": value}
        self._backlog.append(event)
        logger.info(f"[Mock Kafka] Enqueued event to '{topic}' | Key: {key} | Payload: {value}")
        
        if callback:
            class MockMessage:
                def topic(self): return topic
                def key(self): return key
                def value(self): return value
            callback(None, MockMessage())

    def flush(self, timeout=None) -> int:
        return 0

    def list_topics(self, timeout=None):
        class MockMetadata:
            def __init__(self):
                self.topics = {"transactions.raw": None}
        return MockMetadata()

is_kafka_active = False

if MOCK_FORCED:
    logger.warning("ARTHA_KAFKA_MOCK=true — using MockKafkaProducer (test mode only)")
    is_kafka_active = False
else:
    # Real broker connection attempt at startup
    try:
        conf = {
            'bootstrap.servers': settings.KAFKA_BOOTSTRAP_SERVERS,
            'client.id': 'artha-gateway-producer',
            'socket.timeout.ms': 2000
        }
        temp_prod = Producer(conf)
        temp_prod.list_topics(timeout=2.0)
        is_kafka_active = True
        logger.info("Kafka connection established successfully.")
    except Exception as e:
        logger.error(f"Kafka broker connection failed: {e}. Mock fallback is disabled because ARTHA_KAFKA_MOCK is not true.")
        # We set active to True so it tries to use the real broker client and raises errors instead of silencing them
        is_kafka_active = True

def get_kafka_producer():
    """Factory function returning active confluent-kafka Producer or MockKafkaProducer (tests only)."""
    if MOCK_FORCED:
        return MockKafkaProducer()
    
    conf = {
        'bootstrap.servers': settings.KAFKA_BOOTSTRAP_SERVERS,
        'client.id': 'artha-gateway-producer',
        'linger.ms': 10,
        'acks': 1
    }
    return Producer(conf)

def test_kafka_connection() -> bool:
    """Returns True ONLY when a real Kafka broker is reachable. MockKafka is explicitly False."""
    if MOCK_FORCED:
        return False
    try:
        conf = {
            'bootstrap.servers': settings.KAFKA_BOOTSTRAP_SERVERS,
            'client.id': 'artha-gateway-producer',
            'socket.timeout.ms': 1000
        }
        p = Producer(conf)
        metadata = p.list_topics(timeout=1.0)
        return metadata is not None
    except Exception:
        return False
