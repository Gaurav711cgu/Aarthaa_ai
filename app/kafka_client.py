from confluent_kafka import Producer
from app.config import settings
import logging

logger = logging.getLogger(__name__)

class MockKafkaProducer:
    """In-memory Mock Kafka Producer for zero-cost local fallback without broker instances."""
    def __init__(self):
        logger.info("MockKafkaProducer local instance initialized.")
        self._backlog = []

    def produce(self, topic: str, value: str, key: str = None, callback=None, **kwargs):
        """Simulates message production to a topic with callback handler support."""
        event = {"topic": topic, "key": key, "value": value}
        self._backlog.append(event)
        logger.info(f"[Mock Kafka] Enqueued event to '{topic}' | Key: {key} | Payload: {value}")
        
        if callback:
            # Trigger successful delivery callback asynchronously
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

# Check real Kafka broker status
is_kafka_active = False

try:
    conf = {
        'bootstrap.servers': settings.KAFKA_BOOTSTRAP_SERVERS,
        'client.id': 'artha-gateway-producer',
        'socket.timeout.ms': 1000  # 1s socket timeout
    }
    # Direct reachability validation
    temp_prod = Producer(conf)
    temp_prod.list_topics(timeout=1.0)
    is_kafka_active = True
    logger.info("Kafka connection established successfully.")
except Exception as e:
    logger.warning(f"Kafka broker connection failed: {e}. Activating MockKafkaProducer fallback.")
    is_kafka_active = False

def get_kafka_producer():
    """Factory function returning active confluent-kafka Producer or MockKafkaProducer."""
    if is_kafka_active:
        conf = {
            'bootstrap.servers': settings.KAFKA_BOOTSTRAP_SERVERS,
            'client.id': 'artha-gateway-producer',
            'linger.ms': 10,
            'acks': 1
        }
        return Producer(conf)
    return MockKafkaProducer()

def test_kafka_connection() -> bool:
    """Returns True ONLY when a real Kafka broker is reachable. MockKafka is explicitly False."""
    if not is_kafka_active:
        return False  # MockKafka is not a real connection
    try:
        producer = get_kafka_producer()
        metadata = producer.list_topics(timeout=1.0)
        return metadata is not None
    except Exception:
        return False
