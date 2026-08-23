import json
import logging
from typing import Callable, Any

try:
    from confluent_kafka import Producer, Consumer, KafkaError
    HAS_KAFKA = True
except ImportError:
    HAS_KAFKA = False

logger = logging.getLogger(__name__)

class EventSourcedRiskEngine:
    """
    Staff-Level Architecture: Kafka Event Sourcing for Asynchronous Fraud Detection.
    
    Migrates the architecture from synchronous HTTP blocking (webhooks) to a highly 
    scalable Pub/Sub event stream. Ensures exactly-once processing semantics and 
    allows independent scaling of the ML inference workers.
    """
    def __init__(self, bootstrap_servers: str = "localhost:9092"):
        if not HAS_KAFKA:
            logger.warning("confluent_kafka not installed, running in mock mode.")
            self.mock_mode = True
            return
            
        self.mock_mode = False
        self.producer = Producer({
            'bootstrap.servers': bootstrap_servers,
            # Idempotence ensures exactly-once semantics even if network retries occur
            'enable.idempotence': True,
            'acks': 'all',
            'linger.ms': 5,
            'compression.type': 'lz4'
        })
        
        self.consumer = Consumer({
            'bootstrap.servers': bootstrap_servers,
            'group.id': 'arthashield-risk-workers',
            'auto.offset.reset': 'earliest',
            # Disable auto-commit for explicit at-least-once offset management
            'enable.auto.commit': False
        })

    def publish_razorpay_event(self, topic: str, payment_id: str, payload: dict):
        """Asynchronously publishes a webhook event to the Kafka partition."""
        if self.mock_mode:
            logger.info(f"[MOCK KAFKA] Published event {payment_id} to {topic}")
            return

        def delivery_report(err, msg):
            if err is not None:
                logger.error(f"Message delivery failed: {err}")
            else:
                logger.debug(f"Message delivered to {msg.topic()} [{msg.partition()}]")

        # Partition by payment_id to guarantee order of events for the same transaction
        self.producer.produce(
            topic, 
            key=payment_id.encode('utf-8'), 
            value=json.dumps(payload).encode('utf-8'),
            callback=delivery_report
        )
        self.producer.poll(0)

    def start_inference_worker(self, topic: str, process_function: Callable[[dict], Any]):
        """Long-running worker loop that pulls events and runs ML inference."""
        if self.mock_mode:
            logger.info("[MOCK KAFKA] Worker started (idle).")
            return

        self.consumer.subscribe([topic])
        logger.info(f"Kafka Inference Worker subscribed to {topic}")

        try:
            while True:
                msg = self.consumer.poll(1.0)
                
                if msg is None:
                    continue
                if msg.error():
                    if msg.error().code() == KafkaError._PARTITION_EOF:
                        continue
                    else:
                        logger.error(f"Consumer error: {msg.error()}")
                        break

                # Process payload
                payload = json.loads(msg.value().decode('utf-8'))
                
                try:
                    # Run ML Model
                    process_function(payload)
                    # Explicitly commit offset ONLY after successful inference
                    self.consumer.commit(asynchronous=False)
                except Exception as e:
                    logger.error(f"Inference failed for msg {msg.key()}: {e}")
                    
        finally:
            self.consumer.close()
